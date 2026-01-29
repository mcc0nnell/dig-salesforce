#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path
import importlib.util
import xml.etree.ElementTree as ET


def parse_args():
    parser = argparse.ArgumentParser(description="Geary slice CLI (apt-get style).")
    subparsers = parser.add_subparsers(dest="command", required=True)

    update = subparsers.add_parser("update", help="Rebuild slice registry")
    update.add_argument("--root", default=".", help="Repo root")

    listing = subparsers.add_parser("list", help="List slices and aliases")
    listing.add_argument("--root", default=".", help="Repo root")

    graph = subparsers.add_parser("graph", help="Show dependency graph")
    graph.add_argument("--root", default=".", help="Repo root")

    doctor = subparsers.add_parser("doctor", help="Check for issues")
    doctor.add_argument("--root", default=".", help="Repo root")

    install = subparsers.add_parser("install", help="Deploy slices")
    install.add_argument("name", nargs="?", help="Slice name or alias")
    install.add_argument("--all", action="store_true", help="Install all slices")
    install.add_argument("--root", default=".", help="Repo root")
    install.add_argument("--target-org", required=True, help="Salesforce target org alias")
    install.add_argument("--with-deps", action="store_true", help="Install dependencies")
    install.add_argument("--allow-empty", action="store_true", help="Allow installing empty slices")
    install.add_argument("--test-level", choices=["NoTestRun", "RunLocalTests", "RunAllTestsInOrg", "RunSpecifiedTests"], help="Test level for deploy")
    install.add_argument("--tests", help="Comma-separated test class names (RunSpecifiedTests only)")
    install.add_argument("--debug", action="store_true", help="Show full traceback on errors")

    recipe = subparsers.add_parser("recipe", help="Recipe operations")
    recipe_sub = recipe.add_subparsers(dest="recipe_command", required=True)
    recipe_compile = recipe_sub.add_parser("compile", help="Compile recipes")
    recipe_compile.add_argument("--root", default=".", help="Repo root")

    recipe_doctor = recipe_sub.add_parser("doctor", help="Validate recipes")
    recipe_doctor.add_argument("--root", default=".", help="Repo root")

    recipe_install = recipe_sub.add_parser("install", help="Compile recipes and deploy")
    recipe_install.add_argument("name", help="Recipe alias or slice name")
    recipe_install.add_argument("--root", default=".", help="Repo root")
    recipe_install.add_argument("--target-org", help="Salesforce target org alias")
    recipe_install.add_argument("--with-deps", action="store_true", help="Install dependencies")

    return parser.parse_args()


def trim_quotes(value: str) -> str:
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def resolve_package_dirs(root: Path):
    project_file = root / "sfdx-project.json"
    if project_file.exists():
        try:
            data = json.loads(project_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        paths = []
        for entry in data.get("packageDirectories", []):
            path = entry.get("path")
            if path:
                paths.append(root / path)
        if paths:
            return paths
    return [root / "force-app"]


def local_name(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def parse_xml(path: Path):
    try:
        return ET.parse(path).getroot()
    except ET.ParseError:
        return None


def extract_text(root, tag):
    if root is None:
        return None
    for child in list(root):
        if local_name(child.tag) == tag:
            return (child.text or "").strip()
    return None


def scan_objects(root: Path):
    package_dirs = resolve_package_dirs(root)
    missing_object_meta = []
    lookup_errors = []
    custom_objects = set()
    custom_fields = set()
    fields_by_object = {}

    for package_dir in package_dirs:
        base = package_dir / "main" / "default"
        objects_dir = base / "objects"
        if not objects_dir.exists():
            continue
        for obj_path in sorted(objects_dir.iterdir()):
            if not obj_path.is_dir():
                continue
            obj_api_name = obj_path.name
            fields_dir = obj_path / "fields"
            if fields_dir.exists():
                field_files = sorted(fields_dir.glob("*.field-meta.xml"))
            else:
                field_files = []
            obj_meta = obj_path / f"{obj_api_name}.object-meta.xml"
            if obj_api_name.endswith("__c") and field_files and not obj_meta.exists():
                missing_object_meta.append(obj_meta)
            if obj_meta.exists() and obj_api_name.endswith("__c"):
                custom_objects.add(obj_api_name)
            for field_path in field_files:
                field_name = field_path.name.replace(".field-meta.xml", "")
                custom_fields.add(f"{obj_api_name}.{field_name}")
                fields_by_object.setdefault(obj_api_name, []).append(field_name)
                root_xml = parse_xml(field_path)
                field_type = extract_text(root_xml, "type")
                required = extract_text(root_xml, "required")
                if field_type == "Lookup" and required == "true":
                    delete_constraint = extract_text(root_xml, "deleteConstraint")
                    if delete_constraint not in {"Restrict", "Cascade", "RestrictDelete", "CascadeDelete"}:
                        lookup_errors.append((field_path, delete_constraint))

    return {
        "missing_object_meta": missing_object_meta,
        "lookup_errors": lookup_errors,
        "custom_objects": custom_objects,
        "custom_fields": custom_fields,
        "fields_by_object": fields_by_object,
    }


def scan_apex_classes(root: Path):
    package_dirs = resolve_package_dirs(root)
    classes = set()
    for package_dir in package_dirs:
        classes_dir = package_dir / "main" / "default" / "classes"
        if not classes_dir.exists():
            continue
        for path in classes_dir.glob("*.cls"):
            classes.add(path.stem)
        for path in classes_dir.glob("*.cls-meta.xml"):
            classes.add(path.name.replace(".cls-meta.xml", ""))
    return classes


def scan_permsets(root: Path):
    package_dirs = resolve_package_dirs(root)
    permsets = []
    for package_dir in package_dirs:
        permsets_dir = package_dir / "main" / "default" / "permissionsets"
        if not permsets_dir.exists():
            continue
        for path in sorted(permsets_dir.glob("*.permissionset-meta.xml")):
            permsets.append(path)
    return permsets


def manifest_members(path: Path):
    members_by_type = {}
    root_xml = parse_xml(path)
    if root_xml is None:
        return members_by_type
    for types in root_xml.findall(".//{*}types"):
        name_elem = types.find("{*}name")
        if name_elem is None or not name_elem.text:
            continue
        type_name = name_elem.text.strip()
        members = []
        for member in types.findall("{*}members"):
            if member.text:
                members.append(member.text.strip())
        if members:
            members_by_type[type_name] = members
    return members_by_type


def local_file_exists(package_dirs, rel_path: str):
    for base in package_dirs:
        candidate = base / "main" / "default" / rel_path
        if candidate.exists():
            return True
    return False


def validate_manifest_apex_members(root: Path, manifest_path: Path):
    package_dirs = resolve_package_dirs(root)
    members = manifest_members(manifest_path)
    missing = []
    for name in members.get("ApexClass", []):
        cls_path = f"classes/{name}.cls"
        meta_path = f"classes/{name}.cls-meta.xml"
        if not local_file_exists(package_dirs, cls_path) or not local_file_exists(package_dirs, meta_path):
            missing.append(("ApexClass", name))
    for name in members.get("ApexTrigger", []):
        trg_path = f"triggers/{name}.trigger"
        meta_path = f"triggers/{name}.trigger-meta.xml"
        if not local_file_exists(package_dirs, trg_path) or not local_file_exists(package_dirs, meta_path):
            missing.append(("ApexTrigger", name))
    if missing:
        for kind, name in missing:
            if kind == "ApexTrigger":
                location = "dig-src/main/default/triggers/"
            else:
                location = "dig-src/main/default/classes/"
            print(
                f"Missing {kind} in local project: {name}. This class is referenced in {manifest_path} "
                f"but is not present under {location}. Deploy would fail with "
                "'named in package.xml but not found'."
            )
        sys.exit(1)


def extract_permset_refs(path: Path):
    root_xml = parse_xml(path)
    classes = set()
    objects = set()
    if root_xml is None:
        return classes, objects
    for elem in root_xml.iter():
        name = local_name(elem.tag)
        if name == "apexClass" and elem.text:
            classes.add(elem.text.strip())
        if name == "object" and elem.text:
            objects.add(elem.text.strip())
    return classes, objects


def validate_permsets(root: Path, local_classes, local_custom_objects):
    errors = []
    warnings = []
    permsets = scan_permsets(root)
    for permset_path in permsets:
        classes, objects = extract_permset_refs(permset_path)
        missing_classes = sorted([c for c in classes if c and c not in local_classes])
        if missing_classes:
            errors.append((permset_path, missing_classes))
        missing_objects = sorted([o for o in objects if o.endswith("__c") and o not in local_custom_objects])
        if missing_objects:
            warnings.append((permset_path, missing_objects))
    return errors, warnings


def is_production_org(target_org: str):
    cmd = ["sf", "org", "display", "--target-org", target_org, "--json"]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError:
        return None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    org = payload.get("result", {})
    is_sandbox = org.get("isSandbox")
    is_scratch = org.get("isScratchOrg")
    if is_sandbox is None and is_scratch is None:
        return None
    return (is_sandbox is False) and (is_scratch is False)


def apply_test_level_policy(target_org: str, requested_level: str, requested_tests: str):
    prod = is_production_org(target_org)
    if prod is None:
        return requested_level, requested_tests
    if prod:
        if requested_level == "NoTestRun":
            print("NoTestRun is not allowed on production orgs; switching to RunLocalTests")
            return "RunLocalTests", None
        if requested_level is None:
            print("Production org detected; defaulting to RunLocalTests")
            return "RunLocalTests", None
    return requested_level, requested_tests


def load_recipes_module(root: Path):
    module_path = root / "tools" / "geary" / "recipes.py"
    if not module_path.exists():
        raise FileNotFoundError("Missing tools/geary/recipes.py")
    spec = importlib.util.spec_from_file_location("geary_recipes", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("Unable to load recipes module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_aliases(path: Path):
    aliases = {}
    if not path.exists():
        return aliases

    current = None
    in_aliases = False
    includes_mode = False

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not in_aliases:
            if line.strip() == "aliases:":
                in_aliases = True
            continue

        if line and not line.startswith(" "):
            current = None
            includes_mode = False
            continue

        if line.startswith("  ") and line.strip().endswith(":") and not line.strip().startswith("-"):
            alias = line.strip()[:-1]
            aliases[alias] = {"includes": [], "withDeps": None}
            current = alias
            includes_mode = False
            continue

        if current is None:
            continue

        stripped = line.strip()
        if stripped.startswith("includes:"):
            value = stripped[len("includes:"):].strip()
            if value.startswith("["):
                inner = value.strip("[] ")
                items = []
                if inner:
                    for item in inner.split(","):
                        if item.strip():
                            items.append(trim_quotes(item))
                aliases[current]["includes"] = items
                includes_mode = False
            else:
                aliases[current]["includes"] = []
                includes_mode = True
            continue

        if stripped.startswith("withDeps:"):
            value = stripped[len("withDeps:"):].strip().lower()
            aliases[current]["withDeps"] = value == "true"
            includes_mode = False
            continue

        if includes_mode and stripped.startswith("- "):
            item = stripped[2:].strip()
            if item:
                aliases[current]["includes"].append(trim_quotes(item))
            continue

    for alias, data in aliases.items():
        if data["withDeps"] is None:
            data["withDeps"] = False
    return aliases


def load_registry(root: Path):
    registry_path = root / "geary" / "out" / "slices.json"
    if not registry_path.exists():
        raise FileNotFoundError("Missing geary/out/slices.json. Run geary update first.")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    slices = {slice_entry["name"]: slice_entry for slice_entry in registry.get("slices", [])}
    return registry, slices


def canonical_aliases(aliases):
    mapping = {}
    for alias, data in aliases.items():
        for name in data.get("includes", []):
            mapping.setdefault(name, []).append(alias)
    for name in mapping:
        mapping[name].sort()
    return mapping


def resolve_targets(name, aliases, slices):
    if name in aliases:
        return aliases[name]["includes"], name, aliases[name].get("withDeps", False)
    if name in slices:
        return [name], None, False
    raise ValueError(f"Unknown slice or alias: {name}")


def topo_sort(nodes, dep_map):
    ordered = []
    temp = set()
    perm = set()

    def visit(node):
        if node in perm:
            return
        if node in temp:
            raise ValueError(f"Cycle detected at {node}")
        temp.add(node)
        for dep in sorted(dep_map.get(node, [])):
            if dep in nodes:
                visit(dep)
        temp.remove(node)
        perm.add(node)
        ordered.append(node)

    for node in sorted(nodes):
        visit(node)
    return ordered


def expand_with_deps(targets, dep_map, slices):
    expanded = set()

    def add_node(node):
        if node not in slices:
            raise ValueError(f"Missing dependency slice: {node}")
        if node in expanded:
            return
        expanded.add(node)
        for dep in dep_map.get(node, []):
            add_node(dep)

    for target in targets:
        add_node(target)

    return expanded


def format_alias(name, alias_map):
    aliases = alias_map.get(name)
    if not aliases:
        return ""
    return f" (alias: {', '.join(aliases)})"


def run_update(root: Path):
    script = root / "tools" / "geary" / "slices.py"
    if not script.exists():
        raise FileNotFoundError("Missing tools/geary/slices.py")
    cmd = [sys.executable, str(script), "--root", str(root), "--out", "geary/out", "--manifest-dir", "manifest"]
    print("Running: " + " ".join(cmd))
    subprocess.run(cmd, check=True)


def run_recipe_compile(root: Path):
    recipes = load_recipes_module(root)

    results, lock = recipes.compile_all(root)
    lock_path = root / "geary" / "out" / "recipes.lock.json"
    recipes.write_lockfile(lock_path, lock)

    compiled = sum(1 for r in results if r.changed and not r.errors)
    unchanged = sum(1 for r in results if not r.changed and not r.errors)
    failed = sum(1 for r in results if r.errors)

    for result in results:
        for error in result.errors:
            print(f"{result.recipe.path}: {error}")

    alias_directives = recipes.load_alias_directives(root)
    registry_path = root / "geary" / "out" / "slices.json"
    alias_msg = ""
    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        slice_names = [entry["name"] for entry in registry.get("slices", [])]
        alias_msg = recipes.merge_aliases(root / "geary" / "slices.yml", slice_names, alias_directives)
        if alias_msg:
            print(alias_msg)

    print(f"recipes: compiled {compiled}, unchanged {unchanged}, failed {failed}")

    if failed:
        raise SystemExit(1)


def run_recipe_doctor(root: Path):
    recipes = load_recipes_module(root)

    issues = recipes.doctor(root)
    if issues:
        print("RECIPE ISSUES:")
        for issue in issues:
            print(f"- {issue}")
        raise SystemExit(1)


def run_recipe_install(root: Path, args):
    recipes = load_recipes_module(root)

    run_recipe_compile(root)
    run_update(root)

    alias_directives = recipes.load_alias_directives(root)
    alias_map = {item["alias"]: item for item in alias_directives if item.get("alias")}
    recipe_items = recipes.recipe_index(root)
    recipe_map = {item.get("name"): item for item in recipe_items if item.get("name")}

    target_org = args.target_org
    if not target_org:
        fm_target = alias_map.get(args.name, {}).get("targetOrg")
        if not fm_target and args.name in recipe_map:
            fm_target = recipe_map[args.name].get("targetOrg")
        target_org = fm_target or "deafingov"

    install_name = args.name
    if args.name in recipe_map and recipe_map[args.name].get("alias"):
        install_name = recipe_map[args.name]["alias"]
    elif args.name in recipe_map:
        install_name = "flows"

    install_args = argparse.Namespace(
        name=install_name,
        all=False,
        root=str(root),
        target_org=target_org,
        with_deps=args.with_deps,
        allow_empty=False,
        test_level=None,
        tests=None,
    )
    run_install(root, install_args)


def run_list(root: Path):
    registry, slices = load_registry(root)
    aliases = parse_aliases(root / "geary" / "slices.yml")
    alias_map = canonical_aliases(aliases)

    print("Aliases:")
    for alias in sorted(aliases):
        data = aliases[alias]
        includes = ", ".join(data.get("includes", []))
        missing = [item for item in data.get("includes", []) if item not in slices]
        with_deps = data.get("withDeps", False)
        suffix = " withDeps" if with_deps else ""
        if missing:
            print(f"- {alias} -> {includes}{suffix} (missing: {', '.join(missing)})")
        else:
            print(f"- {alias} -> {includes}{suffix}")

    print("\nSlices:")
    for name in sorted(slices):
        entry = slices[name]
        counts = entry["counts"]
        deps = ", ".join(entry.get("dependsOn", [])) or "-"
        print(f"- {name}{format_alias(name, alias_map)}")
        print(f"  manifest: {entry['manifest']}")
        counts_line = [
            f"customObjects={counts.get('customObjects', 0)}",
            f"customFields={counts.get('customFields', 0)}",
            f"flows={counts.get('flows', 0)}",
            f"apexClasses={counts.get('apexClasses', 0)}",
            f"apexTriggers={counts.get('apexTriggers', 0)}",
            f"apexTestSuites={counts.get('apexTestSuites', 0)}",
            f"lwc={counts.get('lwc', 0)}",
            f"aura={counts.get('aura', 0)}",
            f"csp={counts.get('csp', 0)}",
            f"permissionSets={counts.get('permissionSets', 0)}",
            f"profiles={counts.get('profiles', 0)}",
            f"reports={counts.get('reports', 0)}",
            f"dashboards={counts.get('dashboards', 0)}",
            f"folders={counts.get('folders', 0)}",
        ]
        print("  counts: " + " ".join(counts_line))
        print(f"  dependsOn: {deps}")
        if entry.get("notes"):
            print(f"  notes: {', '.join(entry['notes'])}")


def run_graph(root: Path):
    _, slices = load_registry(root)
    aliases = parse_aliases(root / "geary" / "slices.yml")
    alias_map = canonical_aliases(aliases)

    for name in sorted(slices):
        deps = slices[name].get("dependsOn", [])
        dep_display = []
        for dep in deps:
            dep_display.append(dep + format_alias(dep, alias_map))
        dep_str = ", ".join(dep_display) if dep_display else "-"
        print(f"{name}{format_alias(name, alias_map)} -> {dep_str}")


def run_doctor(root: Path):
    _, slices = load_registry(root)
    aliases = parse_aliases(root / "geary" / "slices.yml")
    errors = []
    warnings = []
    notes = []
    lwc_note_added = False
    lwc_present = False
    csp_present = False

    slice_names = set(slices.keys())
    for alias, data in sorted(aliases.items()):
        for item in data.get("includes", []):
            if item not in slice_names:
                errors.append(f"alias {alias} references missing slice {item}")

    for name, entry in sorted(slices.items()):
        counts = entry.get("counts", {})
        if sum(counts.values()) == 0:
            warnings.append(f"empty slice {name}")
        for note in entry.get("notes", []):
            if note.startswith("missing_report:"):
                warnings.append(f"{name} {note}")
            if note.startswith("missing_report_folder:"):
                warnings.append(f"{name} {note}")
            if note.startswith("missing_dashboard_folder:"):
                warnings.append(f"{name} {note}")
        if name == "apex" and (counts.get("apexClasses") or counts.get("apexTriggers")):
            notes.append("Apex present: deploy may require tests; use --test-level RunLocalTests (or RunSpecifiedTests).")
        if counts.get("lwc"):
            lwc_present = True
        if name == "csp" and counts.get("csp"):
            csp_present = True
        if not lwc_note_added and counts.get("lwc"):
            notes.append("LWC present: ensure CSP Trusted Sites / CORS endpoints exist for external calls (if used).")
            lwc_note_added = True

    object_scan = scan_objects(root)
    for missing_meta in object_scan["missing_object_meta"]:
        errors.append(f"missing object-meta.xml for custom object with fields: {missing_meta}")
    for field_path, delete_constraint in object_scan["lookup_errors"]:
        if delete_constraint:
            errors.append(
                f"required lookup missing delete behavior ({delete_constraint}) in {field_path}"
            )
        else:
            errors.append(
                f"required lookup missing delete behavior in {field_path}"
            )

    local_classes = scan_apex_classes(root)
    perm_errors, perm_warnings = validate_permsets(root, local_classes, object_scan["custom_objects"])
    for permset_path, missing in perm_errors:
        errors.append(
            f"permset {permset_path.name} references missing Apex classes: {', '.join(missing)}"
        )
    for permset_path, missing in perm_warnings:
        warnings.append(
            f"permset {permset_path.name} references custom objects not in local source: {', '.join(missing)}"
        )

    warnings.append("Production orgs do not allow NoTestRun; use RunLocalTests for Apex deploys.")

    if lwc_present and not csp_present:
        notes.append("LWC present: if components call external endpoints, add CSPTrustedSite metadata and deploy `csp` slice.")

    manifest_dir = root / "manifest"
    if manifest_dir.exists():
        for manifest_path in sorted(manifest_dir.glob("slice-*.xml")):
            members = manifest_members(manifest_path)
            missing = []
            package_dirs = resolve_package_dirs(root)
            for name in members.get("ApexClass", []):
                cls_path = f"classes/{name}.cls"
                meta_path = f"classes/{name}.cls-meta.xml"
                if not local_file_exists(package_dirs, cls_path) or not local_file_exists(package_dirs, meta_path):
                    missing.append(f"ApexClass:{name}")
            for name in members.get("ApexTrigger", []):
                trg_path = f"triggers/{name}.trigger"
                meta_path = f"triggers/{name}.trigger-meta.xml"
                if not local_file_exists(package_dirs, trg_path) or not local_file_exists(package_dirs, meta_path):
                    missing.append(f"ApexTrigger:{name}")
            if missing:
                warnings.append(
                    f"manifest {manifest_path} references missing Apex members: {', '.join(missing)}"
                )

    if errors:
        print("ERRORS:")
        for item in errors:
            print(f"- {item}")
    if warnings:
        print("WARNINGS:")
        for item in warnings:
            print(f"- {item}")
    if notes:
        print("NOTES:")
        for item in notes:
            print(f"- {item}")

    if errors:
        sys.exit(1)


def run_install(root: Path, args):
    registry, slices = load_registry(root)
    aliases = parse_aliases(root / "geary" / "slices.yml")
    dep_map = {name: entry.get("dependsOn", []) for name, entry in slices.items()}
    warned_coverage = False

    if args.tests and args.test_level != "RunSpecifiedTests":
        raise ValueError("--tests requires --test-level RunSpecifiedTests")
    if args.test_level == "RunSpecifiedTests" and not args.tests:
        raise ValueError("--test-level RunSpecifiedTests requires --tests")

    def schema_lint_or_exit():
        scan = scan_objects(root)
        lint_errors = []
        for missing_meta in scan["missing_object_meta"]:
            lint_errors.append(f"missing object-meta.xml for custom object with fields: {missing_meta}")
        for field_path, delete_constraint in scan["lookup_errors"]:
            if delete_constraint:
                lint_errors.append(
                    f"required lookup missing delete behavior ({delete_constraint}) in {field_path}"
                )
            else:
                lint_errors.append(
                    f"required lookup missing delete behavior in {field_path}"
                )
        if lint_errors:
            print("SCHEMA LINT FAILED:")
            for item in lint_errors:
                print(f"- {item}")
            sys.exit(1)
        return scan

    def permset_check_or_exit(local_objects):
        local_classes = scan_apex_classes(root)
        perm_errors, perm_warnings = validate_permsets(root, local_classes, local_objects)
        if perm_warnings:
            print("PERMSET WARNINGS:")
            for permset_path, missing in perm_warnings:
                print(f"- {permset_path.name}: missing custom objects in local source: {', '.join(missing)}")
        if perm_errors:
            print("PERMSET ERRORS:")
            for permset_path, missing in perm_errors:
                print(f"- {permset_path.name}: missing Apex classes: {', '.join(missing)}")
            print("Guidance: deploy apex-comms-core first or check manifest/slice contents.")
            sys.exit(1)

    def reorder_for_perm_deps(order):
        perms = [name for name in order if slices.get(name, {}).get("kind") == "permissionsets"]
        if not perms:
            return order
        return [name for name in order if name not in perms] + perms

    def deploy_order(order, effective_level, effective_tests):
        nonlocal warned_coverage
        for name in order:
            entry = slices.get(name)
            if not entry:
                raise ValueError(f"Missing slice {name}")
            counts = entry.get("counts", {})
            if sum(counts.values()) == 0 and not args.allow_empty:
                raise ValueError(f"Refusing to install empty slice {name}. Use --allow-empty to override.")
            manifest_path = (root / entry["manifest"]).resolve()
            if counts.get("apexClasses") or counts.get("apexTriggers"):
                validate_manifest_apex_members(root, manifest_path)
            cmd = [
                "sf",
                "project",
                "deploy",
                "start",
                "--target-org",
                args.target_org,
                "--manifest",
                str(manifest_path),
            ]
            use_test_level = None
            use_tests = None
            if effective_level and (
                counts.get("apexClasses") or counts.get("apexTriggers") or counts.get("apexTestSuites")
            ):
                use_test_level = effective_level
                if effective_tests and use_test_level == "RunSpecifiedTests":
                    use_tests = effective_tests
            if use_test_level:
                cmd.extend(["--test-level", use_test_level])
            if use_tests:
                cmd.extend(["--tests", use_tests])
            if use_test_level == "RunLocalTests" and not warned_coverage:
                print("WARNING: Salesforce requires org-wide coverage >= 75% when tests run. "
                      "If you see 'Average test coverage ... 74%' then you must add tests or "
                      "raise coverage before deploy will succeed.")
                print(
                    f"Suggested: sf apex test run --target-org {args.target_org} "
                    "--test-level RunLocalTests --code-coverage --result-format human --wait 60"
                )
                warned_coverage = True
            print("Running: " + " ".join(cmd))
            try:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                if result.stdout:
                    print(result.stdout.rstrip())
                if result.stderr:
                    print(result.stderr.rstrip(), file=sys.stderr)
            except subprocess.CalledProcessError as e:
                if e.stdout:
                    print(e.stdout.rstrip())
                if e.stderr:
                    print(e.stderr.rstrip(), file=sys.stderr)
                print(f"\nDeploy FAILED for slice '{name}': exit code {e.returncode}")
                print(f"Command: {' '.join(cmd)}")
                combined = (e.stdout or "") + "\n" + (e.stderr or "")
                if "test coverage" in combined.lower() or "coverage" in combined.lower():
                    print(
                        "Coverage gate failed. Hint: run "
                        "`sf apex test run --target-org deafingov --tests CoverageBumpTests "
                        "--code-coverage --result-format human --wait 60` and ensure "
                        "org-wide coverage >= 75%."
                    )
                if getattr(args, 'debug', False):
                    raise
                sys.exit(e.returncode)

    def install_by_name(name, override_level=None, override_tests=None):
        targets, _, alias_with_deps = resolve_targets(name, aliases, slices)
        with_deps = args.with_deps or alias_with_deps
        if with_deps:
            nodes = expand_with_deps(targets, dep_map, slices)
            order = topo_sort(nodes, dep_map)
        else:
            order = sorted(set(targets))
        order = reorder_for_perm_deps(order)
        effective_level = override_level
        effective_tests = override_tests
        deploy_order(order, effective_level, effective_tests)

    # Special-case deterministic installer:
    # `comms-web` enforces a safe deploy sequence with schema/permset linting and prod test-level policy.
    # `comms-web-full` is a normal alias expansion (no special behavior).
    if args.name in {"comms-web", "comms-web-full"}:
        schema_scan = schema_lint_or_exit()
        steps = [
            ("objects-case", None, None),
            ("objects-comms", None, None),
            ("apex-comms-core", None, None),
            ("comms-perms", None, None),
            ("lwc-web", None, None),
        ]
        apex_level, apex_tests = apply_test_level_policy(args.target_org, args.test_level, args.tests)
        steps[2] = ("apex-comms-core", apex_level, apex_tests)
        for idx, (step_name, level, tests) in enumerate(steps, start=1):
            print(f"==> Step {idx}/{len(steps)}: {step_name}")
            if step_name == "comms-perms":
                permset_check_or_exit(schema_scan["custom_objects"])
            install_by_name(step_name, level, tests)
        return

    if args.all:
        targets = sorted(slices.keys())
        with_deps = args.with_deps
    else:
        if not args.name:
            raise ValueError("Provide a slice/alias name or use --all")
        targets, alias_name, alias_with_deps = resolve_targets(args.name, aliases, slices)
        with_deps = args.with_deps or alias_with_deps

    if with_deps:
        nodes = expand_with_deps(targets, dep_map, slices)
        order = topo_sort(nodes, dep_map)
    else:
        order = sorted(set(targets))
    order = reorder_for_perm_deps(order)
    schema_scan = None
    if any(slices.get(name, {}).get("kind") == "objects" for name in order):
        schema_scan = schema_lint_or_exit()
    if any(slices.get(name, {}).get("kind") == "permissionsets" for name in order):
        if schema_scan is None:
            schema_scan = scan_objects(root)
        permset_check_or_exit(schema_scan["custom_objects"])
    effective_level, effective_tests = apply_test_level_policy(args.target_org, args.test_level, args.tests)
    deploy_order(order, effective_level, effective_tests)


def main():
    args = parse_args()
    root = Path(args.root).resolve()

    if args.command == "update":
        run_update(root)
        return 0
    if args.command == "list":
        run_list(root)
        return 0
    if args.command == "graph":
        run_graph(root)
        return 0
    if args.command == "doctor":
        run_doctor(root)
        return 0
    if args.command == "install":
        run_install(root, args)
        return 0
    if args.command == "recipe":
        if args.recipe_command == "compile":
            run_recipe_compile(root)
            return 0
        if args.recipe_command == "doctor":
            run_recipe_doctor(root)
            return 0
        if args.recipe_command == "install":
            run_recipe_install(root, args)
            return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
