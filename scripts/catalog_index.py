#!/usr/bin/env python3
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "catalog" / "build" / "catalog.yml"
INDEX_PATH = REPO_ROOT / "docs" / "catalog" / "index.md"


class YamlParser:
    def __init__(self, text: str):
        self.lines: List[Tuple[int, str]] = []
        for idx, raw in enumerate(text.splitlines(), 1):
            stripped = self._strip_comment(raw)
            if stripped.strip() == "":
                continue
            self.lines.append((idx, stripped.rstrip("\n")))

    def parse(self) -> Any:
        value, idx = self._parse_block(0, 0)
        if idx != len(self.lines):
            raise ValueError("Invalid YAML structure")
        return value

    def _parse_block(self, idx: int, indent: int):
        if idx >= len(self.lines):
            return {}, idx
        line = self.lines[idx][1]
        if self._leading_spaces(line) < indent:
            return None, idx
        if line.strip().startswith("-"):
            return self._parse_list(idx, indent)
        return self._parse_map(idx, indent)

    def _parse_list(self, idx: int, indent: int):
        items: List[Any] = []
        while idx < len(self.lines):
            line = self.lines[idx][1]
            if self._leading_spaces(line) != indent or not line.strip().startswith("-"):
                break
            content = line.strip()[1:].strip()
            if content == "":
                idx += 1
                child, idx = self._parse_block(idx, indent + 2)
                items.append(child)
                continue
            if ":" in content:
                key, value = self._split_kv(content)
                item_map: Dict[str, Any] = {}
                if value == "":
                    idx += 1
                    child, idx = self._parse_block(idx, indent + 2)
                    item_map[key] = child
                else:
                    value_obj, idx = self._parse_scalar_with_continuation(
                        value, idx + 1, indent
                    )
                    item_map[key] = value_obj
                if idx < len(self.lines) and self._leading_spaces(self.lines[idx][1]) > indent:
                    child, idx = self._parse_block(idx, indent + 2)
                    if isinstance(child, dict):
                        item_map.update(child)
                    else:
                        item_map[key] = child
                items.append(item_map)
                continue
            value_obj, idx = self._parse_scalar_with_continuation(content, idx + 1, indent)
            items.append(value_obj)
        return items, idx

    def _parse_map(self, idx: int, indent: int):
        mapping: Dict[str, Any] = {}
        while idx < len(self.lines):
            line = self.lines[idx][1]
            if self._leading_spaces(line) != indent or line.strip().startswith("-"):
                break
            key, value = self._split_kv(line.strip())
            if value == "":
                idx += 1
                child_indent = indent + 2
                if idx < len(self.lines):
                    next_line = self.lines[idx][1]
                    if self._leading_spaces(next_line) == indent and next_line.strip().startswith("-"):
                        child_indent = indent
                child, idx = self._parse_block(idx, child_indent)
                mapping[key] = child
            else:
                value_obj, idx = self._parse_scalar_with_continuation(value, idx + 1, indent)
                mapping[key] = value_obj
        return mapping, idx

    def _parse_scalar_with_continuation(self, value: str, idx: int, indent: int):
        value_obj = self._parse_scalar(value)
        if isinstance(value_obj, str):
            while idx < len(self.lines):
                next_line = self.lines[idx][1]
                if self._leading_spaces(next_line) <= indent:
                    break
                stripped = next_line.strip()
                if stripped.startswith("-") or ":" in stripped:
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


def load_yaml(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    parser = YamlParser(text)
    return parser.parse()


@dataclass
class SliceRow:
    slice_id: str
    title: str
    band: str
    owner: str
    docs: List[str]
    bounded: str
    requires: List[str]
    deploy_manifests: List[str]
    deploy_packages: List[str]


def normalize_docs(paths: Any) -> List[str]:
    if not paths:
        return []
    if isinstance(paths, list):
        return [str(p) for p in paths if p]
    return [str(paths)]


def doc_link(path: str) -> str:
    if path.startswith("docs/"):
        rel = "../" + path[len("docs/") :]
    else:
        rel = path
    label = Path(path).stem.replace("-", " ").title()
    return f"[{label}]({rel})"


def file_link(path: str) -> str:
    if path.startswith("manifest/"):
        rel = "../../" + path
    elif path.startswith("docs/"):
        rel = "../" + path[len("docs/") :]
    else:
        rel = path
    return f"[{Path(path).name}]({rel})"


def bounded_label(value: Any) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


def row_key(row: SliceRow) -> Tuple[int, str]:
    number_match = re.search(r"-(\d+)-", row.slice_id)
    if number_match:
        return (int(number_match.group(1)), row.slice_id)
    return (9999, row.slice_id)


def render_table(rows: List[SliceRow]) -> str:
    header = (
        "| id | name | band | owner | docs | bounded | requires | deploy |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    )
    lines = list(header)
    for row in rows:
        docs = "<br>".join(doc_link(p) for p in row.docs) if row.docs else "-"
        requires = ", ".join(row.requires) if row.requires else "-"
        if row.deploy_manifests or row.deploy_packages:
            counts = f"manifests:{len(row.deploy_manifests)} packages:{len(row.deploy_packages)}"
            links = [file_link(p) for p in row.deploy_manifests + row.deploy_packages]
            deploy = counts + ("<br>" + "<br>".join(links) if links else "")
        else:
            deploy = "-"
        line = (
            f"| {row.slice_id} | {row.title} | {row.band} | {row.owner} | "
            f"{docs} | {row.bounded} | {requires} | {deploy} |"
        )
        lines.append(line)
    return "\n".join(lines)


def main() -> int:
    if not CATALOG_PATH.exists():
        print(f"Missing catalog: {CATALOG_PATH}", file=sys.stderr)
        return 1

    data = load_yaml(CATALOG_PATH)
    if not isinstance(data, list):
        print("Catalog YAML must be a list", file=sys.stderr)
        return 1

    rows: List[SliceRow] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        slice_info = entry.get("slice") or {}
        policy = entry.get("policy") or {}
        deploy = entry.get("deploy") or {}
        slice_id = str(slice_info.get("id", "")).strip()
        title = str(slice_info.get("title", "")).strip() or slice_id
        band = str(slice_info.get("band", "")).strip()
        owner = str(slice_info.get("owner") or policy.get("owner") or "").strip()
        docs = normalize_docs(policy.get("docs"))
        bounded = bounded_label(policy.get("bounded"))
        requires = entry.get("depends_on") or []
        if isinstance(requires, str):
            requires = [requires]
        deploy_manifests = deploy.get("manifests") if isinstance(deploy, dict) else []
        if not isinstance(deploy_manifests, list):
            deploy_manifests = []
        deploy_packages = deploy.get("packages") if isinstance(deploy, dict) else []
        if not isinstance(deploy_packages, list):
            deploy_packages = []
        rows.append(
            SliceRow(
                slice_id=slice_id,
                title=title,
                band=band,
                owner=owner,
                docs=docs,
                bounded=bounded,
                requires=requires,
                deploy_manifests=[str(p) for p in deploy_manifests if p],
                deploy_packages=[str(p) for p in deploy_packages if p],
            )
        )

    rows = sorted(rows, key=row_key)
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    deploy_rows = [row for row in rows if row.deploy_manifests or row.deploy_packages]
    deploy_section: List[str] = []
    if deploy_rows:
        deploy_section.extend(
            [
                "## Deploy Map",
                "",
                "| id | manifests | packages |",
                "| --- | --- | --- |",
            ]
        )
        for row in deploy_rows:
            manifests = "<br>".join(file_link(p) for p in row.deploy_manifests) or "-"
            packages = "<br>".join(file_link(p) for p in row.deploy_packages) or "-"
            deploy_section.append(f"| {row.slice_id} | {manifests} | {packages} |")
        deploy_section.append("")

    content = "\n".join(
        [
            "# Slice Index",
            "",
            "Generated from `catalog/build/catalog.yml`.",
            "",
            render_table(rows),
            "",
            *deploy_section,
        ]
    )
    INDEX_PATH.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
