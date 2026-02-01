#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
SCHEMA_PATH = REPO_ROOT / "docs" / "schema" / "slice.schema.json"
EXAMPLES_GLOB = "docs/examples/slice-digops-*.yml"
CATALOG_PATH = REPO_ROOT / "build" / "catalog.yml"
REPORT_PATH = REPO_ROOT / "build" / "catalog_report.md"
SLICES_PATH = REPO_ROOT / "geary" / "slices.yml"

X_GEARY_KEY_ALLOWLIST = {
    "tools/geary/geary.py",
    "tools/geary/mermaid_client.py",
    "dig-src/main/default/classes/MermaidHttpClient.cls",
    "dig-src/main/default/classes/MermaidSecrets.cls",
}
X_GEARY_HEADER = "X" + "-Geary-Key"
X_GEARY_HEADER_COLON = X_GEARY_HEADER + ":"
GEARY_KEY_EQ = "GEARY" + "_KEY="

MANIFEST_KEYS = {"manifests", "manifest", "sf_manifests"}
DOCS_KEYS = {"docs", "documentation"}


@dataclass
class EntryResult:
    path: Path
    data: Dict[str, Any]
    normalized: Dict[str, Any]
    validation_errors: List[str]
    missing_files: List[str]
    warnings: List[str]


@dataclass
class AliasCheck:
    ok: bool
    comms_web_expanded: List[str]
    comms_web_full_expanded: List[str]
    failures: List[str]


@dataclass
class AllowlistCheck:
    ok: bool
    offenders: List[str]


@dataclass
class SecretCheck:
    ok: bool
    offenders: List[str]


class YamlParser:
    def __init__(self, text: str):
        self.lines: List[Tuple[int, str]] = []
        for idx, raw in enumerate(text.splitlines(), 1):
            stripped = self._strip_comment(raw)
            if stripped.strip() == "":
                continue
            self.lines.append((idx, stripped.rstrip("\n")))
        self.line_map: Dict[Tuple[Any, ...], int] = {}

    def parse(self) -> Any:
        value, idx = self._parse_block(0, 0, ())
        if idx != len(self.lines):
            raise ValueError("Invalid YAML structure")
        return value

    def _parse_block(self, idx: int, indent: int, path: Tuple[Any, ...]):
        if idx >= len(self.lines):
            return {}, idx
        line_no, line = self.lines[idx]
        if self._leading_spaces(line) < indent:
            return None, idx
        if line.strip().startswith("- "):
            return self._parse_list(idx, indent, path)
        return self._parse_map(idx, indent, path)

    def _parse_list(self, idx: int, indent: int, path: Tuple[Any, ...]):
        items: List[Any] = []
        while idx < len(self.lines):
            line_no, line = self.lines[idx]
            if self._leading_spaces(line) != indent or not line.strip().startswith("- "):
                break
            content = line.strip()[2:].strip()
            item_path = path + (len(items),)
            if content == "":
                idx += 1
                child, idx = self._parse_block(idx, indent + 2, item_path)
                items.append(child)
                continue
            if ":" in content:
                key, value = self._split_kv(content)
                item_map: Dict[str, Any] = {}
                self.line_map[item_path + (key,)] = line_no
                if value == "":
                    idx += 1
                    child, idx = self._parse_block(idx, indent + 2, item_path + (key,))
                    item_map[key] = child
                else:
                    value_obj, idx = self._parse_scalar_with_continuation(
                        value, idx + 1, indent, line_no
                    )
                    item_map[key] = value_obj
                if idx < len(self.lines) and self._leading_spaces(self.lines[idx][1]) > indent:
                    child, idx = self._parse_block(idx, indent + 2, item_path)
                    if isinstance(child, dict):
                        item_map.update(child)
                    else:
                        item_map[key] = child
                items.append(item_map)
                continue
            value_obj, idx = self._parse_scalar_with_continuation(content, idx + 1, indent, line_no)
            items.append(value_obj)
        return items, idx

    def _parse_map(self, idx: int, indent: int, path: Tuple[Any, ...]):
        mapping: Dict[str, Any] = {}
        while idx < len(self.lines):
            line_no, line = self.lines[idx]
            if self._leading_spaces(line) != indent or line.strip().startswith("- "):
                break
            key, value = self._split_kv(line.strip())
            self.line_map[path + (key,)] = line_no
            if value == "":
                idx += 1
                child_indent = indent + 2
                if idx < len(self.lines):
                    next_line = self.lines[idx][1]
                    if self._leading_spaces(next_line) == indent and next_line.strip().startswith("- "):
                        child_indent = indent
                child, idx = self._parse_block(idx, child_indent, path + (key,))
                mapping[key] = child
            else:
                value_obj, idx = self._parse_scalar_with_continuation(value, idx + 1, indent, line_no)
                mapping[key] = value_obj
        return mapping, idx

    def _parse_scalar_with_continuation(
        self, value: str, idx: int, indent: int, line_no: int
    ) -> Tuple[Any, int]:
        value_obj = self._parse_scalar(value)
        if isinstance(value_obj, str):
            while idx < len(self.lines):
                next_no, next_line = self.lines[idx]
                if self._leading_spaces(next_line) <= indent:
                    break
                stripped = next_line.strip()
                if stripped.startswith("- ") or ":" in stripped:
                    break
                value_obj = f"{value_obj} {stripped}".strip()
                idx += 1
        return value_obj, idx

    @staticmethod
    def _split_kv(text: str) -> Tuple[str, str]:
        if ":" not in text:
            raise ValueError(f"Invalid YAML line: {text}")
        key, value = text.split(":", 1)
        return key.strip(), value.strip()

    @staticmethod
    def _leading_spaces(line: str) -> int:
        return len(line) - len(line.lstrip(" "))

    @staticmethod
    def _parse_scalar(value: str) -> Any:
        lowered = value.lower()
        if lowered in ("true", "false"):
            return lowered == "true"
        if lowered in ("null", "~"):
            return None
        if re.fullmatch(r"\d+", value):
            return int(value)
        if re.fullmatch(r"\d+\.\d+", value):
            return float(value)
        if value.startswith("[") and value.endswith("]"):
            inner = value.strip("[] ")
            if not inner:
                return []
            return [v.strip().strip("\"'") for v in inner.split(",") if v.strip()]
        return value.strip("\"'")

    @staticmethod
    def _strip_comment(line: str) -> str:
        in_single = False
        in_double = False
        for i, ch in enumerate(line):
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif ch == "#" and not in_single and not in_double:
                return line[:i]
        return line


def load_yaml(path: Path) -> Tuple[Any, Dict[Tuple[Any, ...], int]]:
    text = path.read_text(encoding="utf-8")
    parser = YamlParser(text)
    data = parser.parse()
    return data, parser.line_map


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def list_tracked_files() -> List[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return [format_path(p) for p in REPO_ROOT.rglob("*") if p.is_file()]
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def format_path(path: Path) -> str:
    return path.as_posix().replace(str(REPO_ROOT) + "/", "")


def find_line(line_map: Dict[Tuple[Any, ...], int], path: Tuple[Any, ...]) -> str:
    if path in line_map:
        return f"line {line_map[path]}"
    return "line ?"


def validate_against_schema(
    data: Any,
    schema: Dict[str, Any],
    line_map: Dict[Tuple[Any, ...], int],
    path: Tuple[Any, ...] = (),
) -> List[str]:
    errors: List[str] = []
    if "type" in schema:
        if not type_matches(data, schema["type"]):
            errors.append(
                f"{format_json_path(path)}: expected {schema['type']}, got {type_name(data)} ({find_line(line_map, path)})"
            )
            return errors
    if "enum" in schema and data not in schema["enum"]:
        errors.append(
            f"{format_json_path(path)}: value {data!r} not in enum {schema['enum']} ({find_line(line_map, path)})"
        )
    if isinstance(data, str):
        if "minLength" in schema and len(data) < schema["minLength"]:
            errors.append(
                f"{format_json_path(path)}: length {len(data)} < {schema['minLength']} ({find_line(line_map, path)})"
            )
        if "pattern" in schema:
            if not re.fullmatch(schema["pattern"], data):
                errors.append(
                    f"{format_json_path(path)}: value {data!r} does not match pattern ({find_line(line_map, path)})"
                )
    if isinstance(data, int) and "minimum" in schema:
        if data < schema["minimum"]:
            errors.append(
                f"{format_json_path(path)}: value {data} < minimum {schema['minimum']} ({find_line(line_map, path)})"
            )
    if isinstance(data, int) and "maximum" in schema:
        if data > schema["maximum"]:
            errors.append(
                f"{format_json_path(path)}: value {data} > maximum {schema['maximum']} ({find_line(line_map, path)})"
            )
    if isinstance(data, dict):
        props = schema.get("properties", {})
        required = schema.get("required", [])
        for key in required:
            if key not in data:
                errors.append(f"{format_json_path(path + (key,))}: missing required key")
        additional = schema.get("additionalProperties", True)
        if additional is False:
            for key in data.keys():
                if key not in props:
                    errors.append(
                        f"{format_json_path(path + (key,))}: unknown key not allowed ({find_line(line_map, path + (key,))})"
                    )
        for key, value in data.items():
            if key in props:
                errors.extend(
                    validate_against_schema(value, props[key], line_map, path + (key,))
                )
    if isinstance(data, list):
        item_schema = schema.get("items")
        if item_schema:
            for idx, item in enumerate(data):
                errors.extend(
                    validate_against_schema(item, item_schema, line_map, path + (idx,))
                )
    return errors


def type_matches(value: Any, schema_type: Any) -> bool:
    if isinstance(schema_type, list):
        return any(type_matches(value, t) for t in schema_type)
    if schema_type == "object":
        return isinstance(value, dict)
    if schema_type == "array":
        return isinstance(value, list)
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "null":
        return value is None
    return True


def type_name(value: Any) -> str:
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if value is None:
        return "null"
    return type(value).__name__


def format_json_path(path: Tuple[Any, ...]) -> str:
    if not path:
        return "$"
    parts = ["$"]
    for part in path:
        if isinstance(part, int):
            parts.append(f"[{part}]")
        else:
            parts.append(f".{part}")
    return "".join(parts)


def normalize_against_schema(data: Any, schema: Dict[str, Any]) -> Any:
    if isinstance(data, dict):
        props = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        if additional is True:
            return {k: normalize_against_schema(v, props.get(k, {})) for k, v in data.items()}
        normalized: Dict[str, Any] = {}
        for key in props:
            if key in data:
                normalized[key] = normalize_against_schema(data[key], props[key])
        return normalized
    if isinstance(data, list):
        item_schema = schema.get("items", {})
        return [normalize_against_schema(item, item_schema) for item in data]
    return data


def normalize_paths(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: normalize_paths_with_key(k, v) for k, v in data.items()}
    if isinstance(data, list):
        return [normalize_paths(item) for item in data]
    return data


def normalize_paths_with_key(key: str, value: Any) -> Any:
    if isinstance(value, list):
        return [normalize_path_value(key, v) for v in value]
    return normalize_path_value(key, value)


def normalize_path_value(key: str, value: Any) -> Any:
    if not isinstance(value, str):
        return normalize_paths(value)
    cleaned = value.replace("\\", "/").lstrip("./")
    if key in MANIFEST_KEYS or "manifest" in key:
        if not cleaned.startswith("manifest/"):
            cleaned = f"manifest/{cleaned}"
        return cleaned
    if key in DOCS_KEYS or key.endswith("docs"):
        if not cleaned.startswith("docs/"):
            cleaned = f"docs/{cleaned}"
        return cleaned
    if "schema" in key or "rules" in key:
        return cleaned
    return cleaned


def collect_file_refs(data: Any) -> List[Tuple[str, str]]:
    refs: List[Tuple[str, str]] = []

    def walk(node: Any, key: str = ""):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, k)
            return
        if isinstance(node, list):
            for item in node:
                walk(item, key)
            return
        if isinstance(node, str):
            cleaned = node.replace("\\", "/").lstrip("./")
            if key in MANIFEST_KEYS or "manifest" in key or cleaned.startswith("manifest/"):
                path = cleaned if cleaned.startswith("manifest/") else f"manifest/{cleaned}"
                refs.append((path, "manifest"))
                return
            if key in DOCS_KEYS or key.endswith("docs") or cleaned.startswith("docs/"):
                path = cleaned if cleaned.startswith("docs/") else f"docs/{cleaned}"
                refs.append((path, "docs"))
                return
            if "schema" in key or "rules" in key:
                refs.append((cleaned, "other"))

    walk(data)
    return refs


def check_files_exist(refs: List[Tuple[str, str]]) -> List[str]:
    missing: List[str] = []
    for path, _kind in refs:
        if not (REPO_ROOT / path).exists():
            missing.append(path)
    return sorted(set(missing))


def load_aliases() -> Dict[str, Any]:
    data, _ = load_yaml(SLICES_PATH)
    aliases = data.get("aliases", {}) if isinstance(data, dict) else {}
    return aliases


def expand_alias(aliases: Dict[str, Any], alias: str, seen: List[str]) -> List[str]:
    if alias in seen:
        return []
    seen = seen + [alias]
    config = aliases.get(alias, {})
    includes = config.get("includes", []) if isinstance(config, dict) else []
    expanded: List[str] = []
    for item in includes:
        if item in aliases:
            expanded.extend(expand_alias(aliases, item, seen))
        else:
            expanded.append(item)
    return expanded


def includes_alias(aliases: Dict[str, Any], alias: str, target: str, seen: List[str]) -> bool:
    if alias in seen:
        return False
    seen = seen + [alias]
    config = aliases.get(alias, {})
    includes = config.get("includes", []) if isinstance(config, dict) else []
    for item in includes:
        if item == target:
            return True
        if item in aliases and includes_alias(aliases, item, target, seen):
            return True
    return False


def check_alias_boundedness() -> AliasCheck:
    aliases = load_aliases()
    comms_web_expanded = expand_alias(aliases, "comms-web", [])
    comms_web_full_expanded = expand_alias(aliases, "comms-web-full", [])
    failures: List[str] = []
    if includes_alias(aliases, "comms-web", "mermaid-intake", []):
        failures.append("comms-web includes mermaid-intake")
    if includes_alias(aliases, "comms-web-full", "mermaid-intake", []):
        failures.append("comms-web-full includes mermaid-intake")
    ok = len(failures) == 0
    return AliasCheck(ok=ok, comms_web_expanded=comms_web_expanded, comms_web_full_expanded=comms_web_full_expanded, failures=failures)


def check_x_geary_key_allowlist() -> AllowlistCheck:
    offenders: List[str] = []
    scan_targets: List[Path] = []
    geary_root = REPO_ROOT / "tools" / "geary"
    classes_root = REPO_ROOT / "dig-src" / "main" / "default" / "classes"
    if geary_root.exists():
        scan_targets.extend(sorted(geary_root.rglob("*.py")))
    if classes_root.exists():
        scan_targets.extend(sorted(classes_root.rglob("*.cls")))
    for path in scan_targets:
        rel = format_path(path)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if X_GEARY_HEADER in text and rel not in X_GEARY_KEY_ALLOWLIST:
            offenders.append(rel)
    return AllowlistCheck(ok=len(offenders) == 0, offenders=sorted(offenders))


def check_secret_hygiene() -> SecretCheck:
    offenders: List[str] = []
    placeholder_values = {
        "REDACTED",
        "<REDACTED>",
        "CHANGEME",
        "YOUR_KEY_HERE",
        "EXAMPLE",
        "DUMMY",
    }

    def is_placeholder(value: str) -> bool:
        cleaned = value.strip().strip("\"'").strip()
        if cleaned == "":
            return True
        upper = cleaned.upper()
        if upper in placeholder_values:
            return True
        if cleaned.startswith("$") or cleaned.startswith("${"):
            return True
        return False

    for rel in list_tracked_files():
        if rel.startswith("docs/"):
            continue
        name = Path(rel).name
        if name.startswith(".env") or ".env" in name:
            continue
        path = REPO_ROOT / rel
        if path.suffix in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".zip", ".pdf"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for idx, line in enumerate(text.splitlines(), 1):
            if GEARY_KEY_EQ in line:
                parts = line.split(GEARY_KEY_EQ, 1)
                value = parts[1] if len(parts) > 1 else ""
                if is_placeholder(value):
                    continue
                offenders.append(f"{rel}:{idx} ({GEARY_KEY_EQ})")
            if X_GEARY_HEADER_COLON in line:
                parts = line.split(X_GEARY_HEADER_COLON, 1)
                value = parts[1] if len(parts) > 1 else ""
                if is_placeholder(value):
                    continue
                offenders.append(f"{rel}:{idx} ({X_GEARY_HEADER})")
    return SecretCheck(ok=len(offenders) == 0, offenders=sorted(offenders))


def generate_report(
    results: List[EntryResult],
    alias_check: AliasCheck,
    allowlist_check: AllowlistCheck,
    secret_check: SecretCheck,
) -> str:
    lines: List[str] = []
    lines.append("# DIG Ops Catalog Report")
    lines.append("")
    lines.append(f"Catalog entry count: {len(results)}")
    lines.append("")
    lines.append("## Per-entry status")
    lines.append("")
    lines.append("| id | name | status | missing files |")
    lines.append("| --- | --- | --- | --- |")
    for result in results:
        slice_data = result.data.get("slice", {}) if isinstance(result.data, dict) else {}
        slice_id = slice_data.get("id", "-")
        slice_title = slice_data.get("title", "-")
        status = "ok" if not result.validation_errors and not result.missing_files else "fail"
        missing = ", ".join(result.missing_files) if result.missing_files else "-"
        lines.append(f"| {slice_id} | {slice_title} | {status} | {missing} |")
    lines.append("")
    lines.append("## Alias boundedness")
    lines.append("")
    lines.append(f"Result: {'PASS' if alias_check.ok else 'FAIL'}")
    lines.append("")
    lines.append("comms-web expands to:")
    lines.append("")
    lines.append("```text")
    lines.append(", ".join(alias_check.comms_web_expanded) if alias_check.comms_web_expanded else "(empty)")
    lines.append("```")
    lines.append("")
    lines.append("comms-web-full expands to:")
    lines.append("")
    lines.append("```text")
    lines.append(", ".join(alias_check.comms_web_full_expanded) if alias_check.comms_web_full_expanded else "(empty)")
    lines.append("```")
    lines.append("")
    if not alias_check.ok:
        lines.append("Failures:")
        lines.append("")
        for failure in alias_check.failures:
            lines.append(f"- {failure}")
        lines.append("")
    lines.append(f"## {X_GEARY_HEADER} allowlist")
    lines.append("")
    lines.append(f"Result: {'PASS' if allowlist_check.ok else 'FAIL'}")
    if not allowlist_check.ok:
        lines.append("")
        for offender in allowlist_check.offenders:
            lines.append(f"- {offender}")
    lines.append("")
    lines.append("## Secret hygiene")
    lines.append("")
    lines.append(f"Result: {'PASS' if secret_check.ok else 'FAIL'}")
    if not secret_check.ok:
        lines.append("")
        for offender in secret_check.offenders:
            lines.append(f"- {offender}")
    lines.append("")
    warnings = [(r.path, r.warnings) for r in results if r.warnings]
    if warnings:
        lines.append("## Warnings")
        lines.append("")
        for path, items in warnings:
            rel = format_path(path)
            for item in items:
                lines.append(f"- {rel}: {item}")
        lines.append("")
    errors = [(r.path, r.validation_errors) for r in results if r.validation_errors]
    if errors:
        lines.append("## Validation errors")
        lines.append("")
        for path, items in errors:
            rel = format_path(path)
            lines.append(f"### {rel}")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def yaml_dump(value: Any, indent: int = 0) -> str:
    spacing = "  " * indent
    if isinstance(value, dict):
        lines: List[str] = []
        for key in value:
            val = value[key]
            if isinstance(val, (dict, list)):
                lines.append(f"{spacing}{key}:")
                lines.append(yaml_dump(val, indent + 1))
            else:
                lines.append(f"{spacing}{key}: {format_scalar(val)}")
        return "\n".join(lines)
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{spacing}-")
                lines.append(yaml_dump(item, indent + 1))
            else:
                lines.append(f"{spacing}- {format_scalar(item)}")
        return "\n".join(lines)
    return f"{spacing}{format_scalar(value)}"


def format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "" or re.search(r"[:#\n]", text) or text.strip() != text:
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return text


def ordered_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    top_order = ["version", "slice", "depends_on", "provides", "spine", "policy", "files_verified"]
    slice_order = ["id", "number", "band", "title", "description", "owner"]
    provides_order = ["objects", "apex", "lwc", "reports"]
    def order_map(data: Dict[str, Any], order: List[str]) -> Dict[str, Any]:
        ordered: Dict[str, Any] = {}
        for key in order:
            if key in data:
                ordered[key] = data[key]
        for key in sorted(data.keys()):
            if key not in ordered:
                ordered[key] = data[key]
        return ordered
    ordered = order_map(entry, top_order)
    if "slice" in ordered and isinstance(ordered["slice"], dict):
        ordered["slice"] = order_map(ordered["slice"], slice_order)
    if "provides" in ordered and isinstance(ordered["provides"], dict):
        ordered["provides"] = order_map(ordered["provides"], provides_order)
    return ordered


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile DIG Ops catalog and report.")
    parser.add_argument("--quiet", action="store_true", help="Suppress stdout output.")
    args = parser.parse_args()

    if not SCHEMA_PATH.exists():
        print(f"Missing schema at {SCHEMA_PATH}", file=sys.stderr)
        return 1

    schema = load_json(SCHEMA_PATH)
    example_paths = sorted(REPO_ROOT.glob(EXAMPLES_GLOB))
    if not example_paths:
        print(f"No examples found for {EXAMPLES_GLOB}", file=sys.stderr)
        return 1

    results: List[EntryResult] = []

    for path in example_paths:
        try:
            data, line_map = load_yaml(path)
        except Exception as exc:  # noqa: BLE001 - want a per-file error
            results.append(
                EntryResult(
                    path=path,
                    data={},
                    normalized={},
                    validation_errors=[f"YAML parse error: {exc}"],
                    missing_files=[],
                    warnings=[],
                )
            )
            continue
        if not isinstance(data, dict):
            results.append(
                EntryResult(
                    path=path,
                    data={},
                    normalized={},
                    validation_errors=["$ : root must be a mapping"],
                    missing_files=[],
                    warnings=[],
                )
            )
            continue
        validation_errors = validate_against_schema(data, schema, line_map)
        normalized_paths = normalize_paths(data)
        refs = collect_file_refs(normalized_paths)
        missing_files = check_files_exist(refs)
        warnings: List[str] = []
        slice_info = data.get("slice", {}) if isinstance(data.get("slice"), dict) else {}
        if "description" not in slice_info:
            warnings.append("slice.description is missing")
        if "owner" not in slice_info:
            warnings.append("slice.owner is missing")
        normalized = normalize_against_schema(normalized_paths, schema)
        normalized["files_verified"] = len(missing_files) == 0
        results.append(
            EntryResult(
                path=path,
                data=data,
                normalized=normalized,
                validation_errors=validation_errors,
                missing_files=missing_files,
                warnings=warnings,
            )
        )

    def sort_key(res: EntryResult):
        slice_data = res.normalized.get("slice", {}) if isinstance(res.normalized, dict) else {}
        number = slice_data.get("number")
        title = slice_data.get("title") or slice_data.get("id") or ""
        if isinstance(number, int):
            return (0, number, title)
        return (1, title, "")

    results_sorted = sorted(results, key=sort_key)
    catalog_entries = [ordered_entry(r.normalized) for r in results_sorted]
    catalog_text = yaml_dump(catalog_entries, indent=0)

    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(catalog_text + "\n", encoding="utf-8")

    alias_check = check_alias_boundedness()
    allowlist_check = check_x_geary_key_allowlist()
    secret_check = check_secret_hygiene()

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        generate_report(results_sorted, alias_check, allowlist_check, secret_check),
        encoding="utf-8",
    )

    has_errors = any(r.validation_errors or r.missing_files for r in results_sorted)
    if not alias_check.ok:
        has_errors = True
    if not allowlist_check.ok:
        has_errors = True
    if not secret_check.ok:
        has_errors = True

    if not args.quiet:
        status = "PASS" if not has_errors else "FAIL"
        print(f"Catalog compile: {status}")

    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
