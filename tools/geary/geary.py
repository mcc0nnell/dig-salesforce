#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path
import importlib.util


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
            f"flows={counts.get('flows', 0)}",
            f"apexClasses={counts.get('apexClasses', 0)}",
            f"apexTriggers={counts.get('apexTriggers', 0)}",
            f"apexTestSuites={counts.get('apexTestSuites', 0)}",
            f"lwc={counts.get('lwc', 0)}",
            f"aura={counts.get('aura', 0)}",
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
        if not lwc_note_added and counts.get("lwc"):
            notes.append("LWC present: ensure CSP Trusted Sites / CORS endpoints exist for external calls (if used).")
            lwc_note_added = True

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

    if args.tests and args.test_level != "RunSpecifiedTests":
        raise ValueError("--tests requires --test-level RunSpecifiedTests")
    if args.test_level == "RunSpecifiedTests" and not args.tests:
        raise ValueError("--test-level RunSpecifiedTests requires --tests")

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

    for name in order:
        entry = slices.get(name)
        if not entry:
            raise ValueError(f"Missing slice {name}")
        counts = entry.get("counts", {})
        if sum(counts.values()) == 0 and not args.allow_empty:
            raise ValueError(f"Refusing to install empty slice {name}. Use --allow-empty to override.")
        manifest_path = (root / entry["manifest"]).resolve()
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
        if args.test_level:
            cmd.extend(["--test-level", args.test_level])
        if args.tests:
            cmd.extend(["--tests", args.tests])
        print("Running: " + " ".join(cmd))
        subprocess.run(cmd, check=True)


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
