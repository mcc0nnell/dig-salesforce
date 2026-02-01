#!/usr/bin/env python3
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


DEFAULT_WORKER_URL = "https://geary-mermaid-runner-v1.stokoe.workers.dev"
MAX_MERMAID_BYTES = 200 * 1024


def parse_args():
    parser = argparse.ArgumentParser(description="Geary slice CLI (apt-get style).")
    subparsers = parser.add_subparsers(dest="command", required=True)

    update = subparsers.add_parser("update", help="Rebuild slice registry")
    update.add_argument("--root", default=".", help="Repo root")

    listing = subparsers.add_parser("list", help="List slices and aliases")
    listing.add_argument("--root", default=".", help="Repo root")

    graph = subparsers.add_parser("graph", help="Show dependency graph")
    graph.add_argument("--root", default=".", help="Repo root")

    doctor = subparsers.add_parser("doctor", help="Health check or repo checks")
    doctor.add_argument("--root", default=".", help="Repo root")
    doctor.add_argument("--repo", action="store_true", help="Run repository slice checks")
    doctor.add_argument("--no-network", action="store_true", help="Skip network round-trip")
    doctor.add_argument("--env-file", help="Load env vars from this dotenv file before running")

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

    mermaid = subparsers.add_parser("mermaid", help="Render Mermaid via the worker")
    mermaid.add_argument("--root", default=".", help="Repo root")
    mermaid.add_argument("--in", dest="input_path", help="Mermaid source file")
    mermaid.add_argument("--format", choices=["json", "svg"], default="json", help="Worker output format")
    mermaid.add_argument("--out", help="Write output to PATH instead of stdout")
    mermaid.add_argument("--id", help="Optional request id")
    mermaid.add_argument(
        "--worker-url",
        default=os.environ.get("WORKER_URL", DEFAULT_WORKER_URL),
        help="Mermaid worker render URL",
    )
    mermaid.add_argument("--key", help="Mermaid runner auth key")
    mermaid.add_argument("--env-file", help="Path to dotenv file (default: .env.local if present)")
    mermaid.add_argument("--timeout", type=int, default=20, help="Request timeout in seconds")
    mermaid.add_argument("--quiet", action="store_true", help="Suppress informational output")

    run = subparsers.add_parser("run", help="Render Mermaid with receipts/emissions")
    run.add_argument("--root", default=".", help="Repo root")
    run.add_argument("--in", dest="input_path", help="Mermaid source file")
    run.add_argument("--stdin", action="store_true", help="Read Mermaid source from stdin")
    run.add_argument("--format", choices=["json", "svg"], default="svg", help="Worker output format")
    run.add_argument("--out", help="Write output to PATH instead of stdout")
    run.add_argument("--env-file", help="Load env vars from this dotenv file before running")
    run.add_argument("--offline", action="store_true", help="Skip contacting the worker and run structural checks only")

    replay = subparsers.add_parser("replay", help="Verify a prior run by hash")
    replay.add_argument("run_id", help="Run id to replay")
    replay.add_argument("--root", default=".", help="Repo root")
    replay.add_argument("--runs-dir", help="Override runs directory")

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


def normalize_mermaid_text(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip(" \t") for line in normalized.split("\n")]
    cleaned = "\n".join(lines).rstrip()
    if cleaned.startswith("\ufeff"):
        cleaned = cleaned[1:]
    return cleaned


def normalize_input_for_hash(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip(" \t") for line in normalized.split("\n")]
    if lines and lines[0].startswith("\ufeff"):
        lines[0] = lines[0].lstrip("\ufeff")
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def sha256_digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def isoformat_utc(dt: datetime.datetime) -> str:
    return dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_runs_dir(root: Path, override: str | None = None) -> Path:
    value = override or os.environ.get("GEARY_RUNS_DIR") or "./runs"
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path


def generate_run_id() -> str:
    stamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    rand = os.urandom(4).hex()
    return f"{stamp}_{rand}"


def append_emission(emissions_path: Path, run_id: str, event_type: str, data: dict):
    event = {
        "ts": isoformat_utc(utc_now()),
        "run_id": run_id,
        "type": event_type,
        "data": data,
    }
    emissions_path.parent.mkdir(parents=True, exist_ok=True)
    with emissions_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def write_receipt(path: Path, receipt: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(receipt, indent=2, ensure_ascii=False)
    path.write_text(payload + "\n", encoding="utf-8")


def load_dotenv_file(path: Path):
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        if key not in os.environ:
            os.environ[key] = value


def load_env_files(root: Path, args):
    paths = []
    if args.env_file:
        path = Path(args.env_file)
        if not path.is_absolute():
            path = root / path
        paths.append(path)
    else:
        local = root / ".env.local"
        default = root / ".env"
        if local.exists():
            paths.append(local)
        if default.exists():
            paths.append(default)
    for path in paths:
        load_dotenv_file(path)


def read_mermaid_input(root: Path, args) -> str:
    if args.input_path:
        source = Path(args.input_path)
        if not source.is_absolute():
            source = root / source
        if not source.exists():
            print(f"Mermaid input file not found: {source}", file=sys.stderr)
            raise SystemExit(2)
        return source.read_text(encoding="utf-8")
    if getattr(args, "stdin", False):
        return sys.stdin.read()
    if sys.stdin.isatty():
        print("Provide Mermaid source via --in <file> or pipe data to stdin.", file=sys.stderr)
        raise SystemExit(2)
    return sys.stdin.read()


def build_render_url(base_url: str) -> str:
    if base_url.endswith("/render"):
        return base_url
    return base_url.rstrip("/") + "/render"


def perform_worker_request(
    mermaid_text: str,
    fmt: str,
    worker_url: str,
    key: str,
    request_id: str | None,
    timeout: int,
):
    url = build_render_url(worker_url)
    payload = {"mermaid": mermaid_text, "format": fmt}
    if request_id:
        payload["id"] = request_id
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Geary-Key": key,
        },
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            body = response.read()
    except urllib.error.HTTPError as err:
        status = err.code
        body = err.read() if err.fp else b""
    except urllib.error.URLError as err:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return None, None, latency_ms, f"request_failed: {err.reason}"
    latency_ms = int((time.perf_counter() - started) * 1000)
    return status, body, latency_ms, None


def parse_worker_payload(fmt: str, status: int, body: bytes):
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as err:
        raise RuntimeError("invalid_json_response") from err
    if status != 200:
        detail = ""
        if isinstance(payload, dict):
            detail = payload.get("error") or payload.get("detail") or ""
        if not detail:
            detail = "worker_error"
        raise RuntimeError(detail)
    if not payload.get("ok"):
        error_msg = payload.get("error", "missing ok:true")
        raise RuntimeError(error_msg)
    if fmt == "svg":
        svg = payload.get("svg", "")
        if "<svg" not in svg:
            raise RuntimeError("missing svg payload")
    return payload


def map_error_code(http_status: int | None, error_message: str, parse_error: bool = False):
    if http_status is None:
        return "UPSTREAM_DOWN"
    if http_status in {401, 403}:
        return "AUTH_FAIL"
    if http_status == 429:
        return "RATE_LIMIT"
    if 400 <= http_status < 500:
        return "BAD_INPUT"
    if 500 <= http_status < 600:
        return "UPSTREAM_DOWN"
    if parse_error:
        return "RENDER_FAIL"
    if "render" in error_message.lower():
        return "RENDER_FAIL"
    return "UNKNOWN"


def call_mermaid_worker(
    mermaid_text: str,
    fmt: str,
    worker_url: str,
    key: str,
    request_id: str | None,
    timeout: int,
) -> dict:
    url = build_render_url(worker_url)
    payload = {"mermaid": mermaid_text, "format": fmt}
    if request_id:
        payload["id"] = request_id
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Geary-Key": key,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        status = err.code
        body = err.read().decode("utf-8") if err.fp else ""
    except urllib.error.URLError as err:
        raise RuntimeError(f"request_failed: {err.reason}") from err

    if status != 200:
        detail = body.strip().replace("\n", " ")
        if detail:
            try:
                parsed = json.loads(body)
                if isinstance(parsed, dict):
                    detail = parsed.get("error") or parsed.get("detail") or detail
            except json.JSONDecodeError:
                pass
        else:
            detail = "no response body"
        if status == 401:
            raise RuntimeError("unauthorized: check GEARY_KEY")
        if status == 413:
            raise RuntimeError("payload_too_large: <=200KB")
        raise RuntimeError(f"worker_error: {status} {detail}")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as err:
        raise RuntimeError("invalid_json_response") from err

    if not payload.get("ok"):
        error_msg = payload.get("error", "missing ok:true")
        raise RuntimeError(f"worker_error: {error_msg}")

    if fmt == "svg":
        svg = payload.get("svg", "")
        if "<svg" not in svg:
            raise RuntimeError("missing svg payload")

    return payload


def write_mermaid_output(root: Path, args, payload: dict):
    output_format = args.format
    if args.out:
        target = Path(args.out)
        if not target.is_absolute():
            target = root / target
        target.parent.mkdir(parents=True, exist_ok=True)
        content = payload.get("svg") if output_format == "svg" else json.dumps(payload, indent=2, ensure_ascii=False)
        target.write_text(content, encoding="utf-8")
        if not args.quiet:
            print(f"Wrote {target}")
    else:
        if output_format == "svg":
            print(payload.get("svg", ""), end="" if payload.get("svg", "").endswith("\n") else "\n")
        else:
            print(json.dumps(payload, indent=2, ensure_ascii=False))


def run_mermaid(root: Path, args):
    load_env_files(root, args)
    key = args.key or os.environ.get("GEARY_KEY")
    if not key:
        print("Missing GEARY_KEY (set env or --key).", file=sys.stderr)
        raise SystemExit(2)

    raw = read_mermaid_input(root, args)
    if not raw.strip():
        print("Mermaid input is empty.", file=sys.stderr)
        raise SystemExit(2)
    normalized = normalize_mermaid_text(raw)
    if not normalized:
        print("Mermaid input is empty after normalization.", file=sys.stderr)
        raise SystemExit(2)
    size = len(normalized.encode("utf-8"))
    if size > MAX_MERMAID_BYTES:
        print(f"Mermaid source too large ({size} bytes > {MAX_MERMAID_BYTES}).", file=sys.stderr)
        raise SystemExit(2)

    try:
        response = call_mermaid_worker(
            normalized,
            args.format,
            args.worker_url,
            key,
            args.id,
            args.timeout,
        )
    except RuntimeError as err:
        print(f"Mermaid render failed: {err}", file=sys.stderr)
        raise SystemExit(1)

    write_mermaid_output(root, args, response)


def offline_artifact_payload(fmt: str) -> tuple[str, bytes]:
    if fmt == "svg":
        content = "<!-- geary offline placeholder -->\n"
        return "output.svg", content.encode("utf-8")
    payload = {"ok": True, "offline": True}
    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
    return "output.json", (rendered + "\n").encode("utf-8")


def compute_input_output_hashes(input_path: Path, output_path: Path) -> tuple[str, str]:
    normalized = normalize_input_for_hash(input_path.read_text(encoding="utf-8"))
    input_hash = sha256_digest(normalized.encode("utf-8"))
    output_hash = sha256_digest(output_path.read_bytes())
    return input_hash, output_hash


def verify_run_hashes(run_dir: Path) -> tuple[bool, str]:
    receipt_path = run_dir / "receipt.json"
    if not receipt_path.exists():
        return False, "missing receipt.json"
    receipt_data = json.loads(receipt_path.read_text(encoding="utf-8"))
    fmt = receipt_data.get("format") or "svg"
    artifacts_dir = run_dir / "artifacts"
    input_path = artifacts_dir / "input.mmd"
    output_path = artifacts_dir / ("output.svg" if fmt == "svg" else "output.json")
    if not input_path.exists() or not output_path.exists():
        return False, "missing artifacts"
    input_hash, output_hash = compute_input_output_hashes(input_path, output_path)
    errors = []
    if (receipt_data.get("input_hash") or "") != input_hash:
        errors.append("input hash mismatch")
    if (receipt_data.get("output_hash") or "") != output_hash:
        errors.append("output hash mismatch")
    if errors:
        return False, "; ".join(errors)
    return True, ""


def perform_offline_invariants(
    root: Path,
    run_id: str | None = None,
    runs_dir_override: str | None = None,
    sample_input: str = "flowchart TD\n  A-->B\n",
) -> tuple[bool, str]:
    final_run_id = run_id or generate_run_id()
    _, run_dir, artifacts_dir = ensure_run_dirs(root, final_run_id, runs_dir_override)
    run_id = run_dir.name
    emissions_path = run_dir / "emissions.ndjson"
    receipt_path = run_dir / "receipt.json"
    started_at = utc_now()

    append_emission(emissions_path, run_id, "run.started", {"command": "doctor-offline"})

    geary_key = os.environ.get("GEARY_KEY")
    worker_url = os.environ.get("WORKER_URL")
    append_emission(
        emissions_path,
        run_id,
        "env.checked",
        {"geary_key_present": bool(geary_key), "worker_url_present": bool(worker_url)},
    )
    append_emission(emissions_path, run_id, "auth.present", {"present": bool(geary_key)})

    normalized = normalize_input_for_hash(sample_input)
    input_bytes = normalized.encode("utf-8")
    input_hash = sha256_digest(input_bytes)
    input_path = artifacts_dir / "input.mmd"
    write_artifact(input_path, input_bytes)
    append_emission(
        emissions_path,
        run_id,
        "artifact.written",
        {"path": str(input_path), "bytes": len(input_bytes), "hash": input_hash},
    )

    output_name, output_bytes = offline_artifact_payload("svg")
    output_hash = sha256_digest(output_bytes)
    output_path = artifacts_dir / output_name
    write_artifact(output_path, output_bytes)
    append_emission(
        emissions_path,
        run_id,
        "artifact.written",
        {"path": str(output_path), "bytes": len(output_bytes), "hash": output_hash, "offline": True},
    )

    receipt = {
        "run_id": run_id,
        "command": "doctor-offline",
        "worker_url": worker_url or "",
        "input_hash": input_hash,
        "output_hash": output_hash,
        "format": "svg",
        "started_at": isoformat_utc(started_at),
        "finished_at": isoformat_utc(utc_now()),
        "status": "ok",
        "http_status": None,
        "latency_ms": None,
        "error_code": "",
        "error_message": "",
    }
    write_receipt(receipt_path, receipt)
    append_emission(emissions_path, run_id, "receipt.written", {"path": str(receipt_path)})
    append_emission(emissions_path, run_id, "run.completed", {"status": "ok"})

    if not emissions_path.exists() or emissions_path.stat().st_size == 0:
        return False, "missing emissions log"

    verified, reason = verify_run_hashes(run_dir)
    if not verified:
        return False, reason

    return True, ""


def ensure_run_dirs(root: Path, run_id: str, runs_dir_override: str | None = None):
    runs_dir = get_runs_dir(root, runs_dir_override)
    run_dir = runs_dir / run_id
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return runs_dir, run_dir, artifacts_dir


def write_artifact(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def format_json_output(payload: dict) -> bytes:
    rendered = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    return (rendered + "\n").encode("utf-8")


def run_health_doctor(root: Path, args):
    load_env_files(root, argparse.Namespace(env_file=getattr(args, "env_file", None)))
    worker_url = os.environ.get("WORKER_URL")
    geary_key = os.environ.get("GEARY_KEY")
    key_present = bool(geary_key)
    worker_present = bool(worker_url)
    http_status = None
    latency_ms = None
    error_code = ""
    error_message = ""
    status = "ok"
    mode_label = "OFFLINE" if args.no_network else "LIVE"

    worker_host = "-"
    if worker_url:
        worker_host = urllib.parse.urlparse(worker_url).netloc or worker_url

    if args.no_network:
        success, reason = perform_offline_invariants(root)
        if not success:
            status = "fail"
            error_code = "OFFLINE_FAIL"
            error_message = reason or "offline validation failed"
    else:
        run_id = generate_run_id()
        _, run_dir, artifacts_dir = ensure_run_dirs(root, run_id)
        emissions_path = run_dir / "emissions.ndjson"
        receipt_path = run_dir / "receipt.json"
        started_at = utc_now()

        append_emission(emissions_path, run_id, "run.started", {"command": "doctor"})
        append_emission(
            emissions_path,
            run_id,
            "env.checked",
            {"geary_key_present": key_present, "worker_url_present": worker_present},
        )
        append_emission(emissions_path, run_id, "auth.present", {"present": key_present})

        input_hash = ""
        output_hash = ""
        status = "ok"

        if not key_present or not worker_present:
            status = "fail"
            if not key_present:
                error_code = "AUTH_FAIL"
                error_message = "GEARY_KEY is missing"
            else:
                error_code = "UPSTREAM_DOWN"
                error_message = "WORKER_URL is missing"
        else:
            sample = "flowchart TD\n  A-->B\n"
            normalized = normalize_input_for_hash(sample)
            input_bytes = normalized.encode("utf-8")
            input_hash = sha256_digest(input_bytes)
            input_path = artifacts_dir / "input.mmd"
            write_artifact(input_path, input_bytes)
            append_emission(
                emissions_path,
                run_id,
                "artifact.written",
                {"path": str(input_path), "bytes": len(input_bytes), "hash": input_hash},
            )

            http_status, body, latency_ms, request_error = perform_worker_request(
                normalized,
                "svg",
                worker_url,
                geary_key,
                None,
                20,
            )
            request_payload = {"mermaid": normalized, "format": "svg"}
            append_emission(
                emissions_path,
                run_id,
                "request.sent",
                {
                    "method": "POST",
                    "path": urllib.parse.urlparse(build_render_url(worker_url)).path,
                    "body_bytes": len(json.dumps(request_payload, ensure_ascii=False).encode("utf-8")),
                },
            )
            if request_error:
                status = "fail"
                error_code = "UPSTREAM_DOWN"
                error_message = request_error
            else:
                response_bytes = len(body or b"")
                append_emission(
                    emissions_path,
                    run_id,
                    "response.received",
                    {"status": http_status, "bytes": response_bytes},
                )
                try:
                    payload = parse_worker_payload("svg", http_status, body or b"")
                    svg_bytes = (payload.get("svg") or "").encode("utf-8")
                    output_hash = sha256_digest(svg_bytes)
                    output_path = artifacts_dir / "output.svg"
                    write_artifact(output_path, svg_bytes)
                    append_emission(
                        emissions_path,
                        run_id,
                        "artifact.written",
                        {"path": str(output_path), "bytes": len(svg_bytes), "hash": output_hash},
                    )
                except RuntimeError as err:
                    status = "fail"
                    error_message = str(err)
                    error_code = map_error_code(http_status, error_message, parse_error=True)

        finished_at = utc_now()
        receipt = {
            "run_id": run_id,
            "command": "doctor",
            "worker_url": worker_url or "",
            "input_hash": input_hash,
            "output_hash": output_hash,
            "format": "svg",
            "started_at": isoformat_utc(started_at),
            "finished_at": isoformat_utc(finished_at),
            "status": status,
            "http_status": http_status,
            "latency_ms": latency_ms,
            "error_code": error_code,
            "error_message": error_message,
        }
        write_receipt(receipt_path, receipt)
        append_emission(emissions_path, run_id, "receipt.written", {"path": str(receipt_path)})
        if status == "ok":
            append_emission(emissions_path, run_id, "run.completed", {"status": status})
        else:
            append_emission(emissions_path, run_id, "run.failed", {"error_code": error_code})
            append_emission(emissions_path, run_id, "run.completed", {"status": status})

    print(f"worker host: {worker_host}")
    print(f"key present: {'yes' if key_present else 'no'}")
    print(f"mode: {mode_label}")
    if http_status is not None:
        print(f"http status: {http_status}")
    else:
        print("http status: -")
    if latency_ms is not None:
        print(f"latency ms: {latency_ms}")
    else:
        print("latency ms: -")

    if status == "ok":
        print(f"PASS: geary doctor healthy ({mode_label} mode)")
        return 0
    print(f"FAIL: {error_message or 'doctor failed'}")
    if error_code in {"AUTH_FAIL", "UPSTREAM_DOWN"}:
        print("Next step: set GEARY_KEY and WORKER_URL for live checks.")
    elif error_code == "RATE_LIMIT":
        print("Next step: wait and retry (rate limit).")
    elif error_code == "BAD_INPUT":
        print("Next step: check Mermaid payload formatting.")
    elif error_code == "OFFLINE_FAIL":
        print("Next step: inspect runs directory for receipts/emissions.")
    else:
        print("Next step: retry or inspect worker status.")
    return 1


def run_mermaid_render(root: Path, args, command_name: str, run_id: str, runs_dir_override: str | None = None):
    load_env_files(root, args)
    _runs_dir, run_dir, artifacts_dir = ensure_run_dirs(root, run_id, runs_dir_override)
    emissions_path = run_dir / "emissions.ndjson"
    receipt_path = run_dir / "receipt.json"
    started_at = utc_now()

    append_emission(emissions_path, run_id, "run.started", {"command": command_name})

    geary_key = os.environ.get("GEARY_KEY")
    worker_url = os.environ.get("WORKER_URL")
    key_present = bool(geary_key)
    worker_present = bool(worker_url)
    append_emission(
        emissions_path,
        run_id,
        "env.checked",
        {"geary_key_present": key_present, "worker_url_present": worker_present},
    )
    append_emission(emissions_path, run_id, "auth.present", {"present": key_present})

    input_hash = ""
    output_hash = ""
    http_status = None
    latency_ms = None
    error_code = ""
    error_message = ""
    status = "ok"
    offline = getattr(args, "offline", False)

    if not offline and (not key_present or not worker_present):
        status = "fail"
        if not key_present:
            error_code = "AUTH_FAIL"
            error_message = "GEARY_KEY is missing"
        else:
            error_code = "UPSTREAM_DOWN"
            error_message = "WORKER_URL is missing"
    else:
        try:
            raw = read_mermaid_input(root, args)
        except SystemExit:
            status = "fail"
            error_code = "BAD_INPUT"
            error_message = "Mermaid input is missing."
        else:
            normalized = normalize_input_for_hash(raw)
            if not normalized.strip():
                status = "fail"
                error_code = "BAD_INPUT"
                error_message = "Mermaid input is empty."
            else:
                size = len(normalized.encode("utf-8"))
                if size > MAX_MERMAID_BYTES:
                    status = "fail"
                    error_code = "BAD_INPUT"
                    error_message = f"Mermaid source too large ({size} bytes > {MAX_MERMAID_BYTES})."
                else:
                    input_bytes = normalized.encode("utf-8")
                    input_hash = sha256_digest(input_bytes)
                    input_path = artifacts_dir / "input.mmd"
                    write_artifact(input_path, input_bytes)
                    append_emission(
                        emissions_path,
                        run_id,
                        "artifact.written",
                        {"path": str(input_path), "bytes": len(input_bytes), "hash": input_hash},
                    )

                    output_bytes = b""
                    output_name = ""
                    if offline:
                        http_status = None
                        latency_ms = None
                        output_name, output_bytes = offline_artifact_payload(args.format)
                        output_hash = sha256_digest(output_bytes)
                        output_path = artifacts_dir / output_name
                        write_artifact(output_path, output_bytes)
                        append_emission(
                            emissions_path,
                            run_id,
                            "artifact.written",
                            {"path": str(output_path), "bytes": len(output_bytes), "hash": output_hash, "offline": True},
                        )
                    else:
                        http_status, body, latency_ms, request_error = perform_worker_request(
                            normalized,
                            args.format,
                            worker_url,
                            geary_key,
                            None,
                            20,
                        )
                        request_payload = {"mermaid": normalized, "format": args.format}
                        append_emission(
                            emissions_path,
                            run_id,
                            "request.sent",
                            {
                                "method": "POST",
                                "path": urllib.parse.urlparse(build_render_url(worker_url)).path,
                                "body_bytes": len(json.dumps(request_payload, ensure_ascii=False).encode("utf-8")),
                            },
                        )
                        if request_error:
                            status = "fail"
                            error_code = "UPSTREAM_DOWN"
                            error_message = request_error
                        else:
                            append_emission(
                                emissions_path,
                                run_id,
                                "response.received",
                                {"status": http_status, "bytes": len(body or b"")},
                            )
                            try:
                                payload = parse_worker_payload(args.format, http_status, body or b"")
                                if args.format == "svg":
                                    output_bytes = (payload.get("svg") or "").encode("utf-8")
                                    output_name = "output.svg"
                                else:
                                    output_bytes = format_json_output(payload)
                                    output_name = "output.json"
                                output_hash = sha256_digest(output_bytes)
                                output_path = artifacts_dir / output_name
                                write_artifact(output_path, output_bytes)
                                append_emission(
                                    emissions_path,
                                    run_id,
                                    "artifact.written",
                                    {"path": str(output_path), "bytes": len(output_bytes), "hash": output_hash},
                                )
                            except RuntimeError as err:
                                status = "fail"
                                error_message = str(err)
                                error_code = map_error_code(http_status, error_message, parse_error=True)

                    if args.out and status == "ok":
                        target = Path(args.out)
                        if not target.is_absolute():
                            target = root / target
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(output_bytes)
                    elif status == "ok":
                        sys.stdout.buffer.write(output_bytes)
                        if not output_bytes.endswith(b"\n"):
                            sys.stdout.buffer.write(b"\n")

    finished_at = utc_now()
    receipt = {
        "run_id": run_id,
        "command": command_name,
        "worker_url": worker_url or "",
        "input_hash": input_hash,
        "output_hash": output_hash,
        "format": args.format,
        "started_at": isoformat_utc(started_at),
        "finished_at": isoformat_utc(finished_at),
        "status": status,
        "http_status": http_status,
        "latency_ms": latency_ms,
        "error_code": error_code,
        "error_message": error_message,
    }
    write_receipt(receipt_path, receipt)
    append_emission(emissions_path, run_id, "receipt.written", {"path": str(receipt_path)})
    if status == "ok":
        append_emission(emissions_path, run_id, "run.completed", {"status": status})
    else:
        append_emission(emissions_path, run_id, "run.failed", {"error_code": error_code})
        append_emission(emissions_path, run_id, "run.completed", {"status": status})

    print(f"run id: {run_id}", file=sys.stderr)
    if status != "ok" and error_message:
        print(f"{command_name} failed: {error_message}", file=sys.stderr)
    return 0 if status == "ok" else 1


def run_run(root: Path, args):
    if args.input_path and args.stdin:
        print("Choose either --in <file> or --stdin.", file=sys.stderr)
        return 2
    run_id = generate_run_id()
    return run_mermaid_render(root, args, "run", run_id)


def run_replay(root: Path, args):
    runs_dir = get_runs_dir(root, args.runs_dir)
    target_dir = runs_dir / args.run_id
    receipt_path = target_dir / "receipt.json"
    artifacts_dir = target_dir / "artifacts"

    if not receipt_path.exists():
        print(f"Missing receipt.json for run {args.run_id}", file=sys.stderr)
        return 2

    receipt_data = json.loads(receipt_path.read_text(encoding="utf-8"))
    fmt = receipt_data.get("format") or "svg"
    worker_url = receipt_data.get("worker_url") or ""

    input_path = artifacts_dir / "input.mmd"
    if fmt == "svg":
        output_path = artifacts_dir / "output.svg"
    else:
        output_path = artifacts_dir / "output.json"

    if not input_path.exists() or not output_path.exists():
        print("Missing input/output artifacts for replay.", file=sys.stderr)
        return 2

    replay_run_id = generate_run_id()
    _, run_dir, artifacts_dir_new = ensure_run_dirs(root, replay_run_id, args.runs_dir)
    emissions_path = run_dir / "emissions.ndjson"
    receipt_out_path = run_dir / "receipt.json"
    started_at = utc_now()
    append_emission(emissions_path, replay_run_id, "run.started", {"command": "replay", "target_run_id": args.run_id})
    append_emission(
        emissions_path,
        replay_run_id,
        "env.checked",
        {"geary_key_present": bool(os.environ.get("GEARY_KEY")), "worker_url_present": bool(os.environ.get("WORKER_URL"))},
    )
    append_emission(
        emissions_path,
        replay_run_id,
        "auth.present",
        {"present": bool(os.environ.get("GEARY_KEY"))},
    )

    input_text = input_path.read_text(encoding="utf-8")
    normalized = normalize_input_for_hash(input_text)
    input_bytes = normalized.encode("utf-8")
    input_hash = sha256_digest(input_bytes)
    output_bytes = output_path.read_bytes()
    output_hash = sha256_digest(output_bytes)

    input_written_path = artifacts_dir_new / "input.mmd"
    output_written_path = artifacts_dir_new / output_path.name
    write_artifact(input_written_path, input_bytes)
    write_artifact(output_written_path, output_bytes)
    append_emission(
        emissions_path,
        replay_run_id,
        "artifact.written",
        {"path": str(input_written_path), "bytes": len(input_bytes), "hash": input_hash},
    )
    append_emission(
        emissions_path,
        replay_run_id,
        "artifact.written",
        {"path": str(output_written_path), "bytes": len(output_bytes), "hash": output_hash},
    )

    receipt_input_hash = receipt_data.get("input_hash") or ""
    receipt_output_hash = receipt_data.get("output_hash") or ""

    verified_input = input_hash == receipt_input_hash
    verified_output = output_hash == receipt_output_hash
    status = "ok" if (verified_input and verified_output) else "fail"

    finished_at = utc_now()
    receipt = {
        "run_id": replay_run_id,
        "command": "replay",
        "worker_url": worker_url,
        "input_hash": input_hash,
        "output_hash": output_hash,
        "format": fmt,
        "started_at": isoformat_utc(started_at),
        "finished_at": isoformat_utc(finished_at),
        "status": status,
        "http_status": None,
        "latency_ms": None,
        "error_code": "" if status == "ok" else "UNKNOWN",
        "error_message": "" if status == "ok" else "hash verification failed",
    }
    write_receipt(receipt_out_path, receipt)
    append_emission(emissions_path, replay_run_id, "receipt.written", {"path": str(receipt_out_path)})
    if status == "ok":
        append_emission(emissions_path, replay_run_id, "run.completed", {"status": status})
    else:
        append_emission(emissions_path, replay_run_id, "run.failed", {"error_code": "UNKNOWN"})
        append_emission(emissions_path, replay_run_id, "run.completed", {"status": status})

    print(f"input hash verified: {'yes' if verified_input else 'no'}")
    print(f"output hash verified: {'yes' if verified_output else 'no'}")
    print(f"status: {status}")

    return 0 if status == "ok" else 1


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


def run_repo_doctor(root: Path):
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
        use_repo = args.repo or ("--root" in sys.argv)
        if use_repo:
            run_repo_doctor(root)
            return 0
        return run_health_doctor(root, args)
    if args.command == "install":
        run_install(root, args)
        return 0
    if args.command == "mermaid":
        run_mermaid(root, args)
        return 0
    if args.command == "run":
        return run_run(root, args)
    if args.command == "replay":
        return run_replay(root, args)
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
