#!/usr/bin/env python3
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import xml.etree.ElementTree as ET

MERMAID_BLOCK_RE = re.compile(r"```mermaid\s*(.*?)```", re.DOTALL | re.IGNORECASE)
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass
class Recipe:
    path: Path
    frontmatter: Dict[str, object]
    mermaid: str


@dataclass
class CompileResult:
    recipe: Recipe
    output_path: Optional[Path]
    changed: bool
    errors: List[str]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_frontmatter(text: str) -> Tuple[Dict[str, object], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError("Missing YAML frontmatter")
    block = match.group(1)
    rest = text[match.end():]
    data = parse_yaml(block)
    if not isinstance(data, dict):
        raise ValueError("Frontmatter must be a mapping")
    return data, rest


def parse_yaml(block: str):
    lines = []
    for raw in block.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if line.strip() == "":
            continue
        lines.append(line)
    obj, idx = parse_block(lines, 0, 0)
    if idx != len(lines):
        raise ValueError("Invalid YAML structure")
    return obj


def parse_block(lines: List[str], idx: int, indent: int):
    if idx >= len(lines):
        return {}, idx
    line = lines[idx]
    if leading_spaces(line) < indent:
        return None, idx
    if line.strip().startswith("- "):
        return parse_list(lines, idx, indent)
    return parse_map(lines, idx, indent)


def parse_list(lines: List[str], idx: int, indent: int):
    items = []
    while idx < len(lines):
        line = lines[idx]
        if leading_spaces(line) != indent or not line.strip().startswith("- "):
            break
        content = line.strip()[2:].strip()
        if content == "":
            idx += 1
            child, idx = parse_block(lines, idx, indent + 2)
            items.append(child)
            continue
        if ":" in content:
            key, value = split_kv(content)
            item_map: Dict[str, object] = {}
            if value == "":
                idx += 1
                child, idx = parse_block(lines, idx, indent + 2)
                item_map[key] = child
            else:
                item_map[key] = parse_scalar(value)
                idx += 1
            if idx < len(lines) and leading_spaces(lines[idx]) > indent:
                child, idx = parse_block(lines, idx, indent + 2)
                if isinstance(child, dict):
                    item_map.update(child)
                else:
                    item_map[key] = child
            items.append(item_map)
            continue
        items.append(parse_scalar(content))
        idx += 1
    return items, idx


def parse_map(lines: List[str], idx: int, indent: int):
    mapping: Dict[str, object] = {}
    while idx < len(lines):
        line = lines[idx]
        if leading_spaces(line) != indent or line.strip().startswith("- "):
            break
        key, value = split_kv(line.strip())
        if value == "":
            idx += 1
            child, idx = parse_block(lines, idx, indent + 2)
            mapping[key] = child
        else:
            mapping[key] = parse_scalar(value)
            idx += 1
    return mapping, idx


def split_kv(text: str) -> Tuple[str, str]:
    if ":" not in text:
        raise ValueError(f"Invalid YAML line: {text}")
    key, value = text.split(":", 1)
    return key.strip(), value.strip()


def parse_scalar(value: str):
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    if re.fullmatch(r"\d+(\.\d+)?", value):
        return value
    if value.startswith("[") and value.endswith("]"):
        inner = value.strip("[] ")
        if not inner:
            return []
        return [v.strip().strip('"\'') for v in inner.split(",") if v.strip()]
    return value.strip('"\'')


def leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def parse_mermaid_block(text: str) -> str:
    match = MERMAID_BLOCK_RE.search(text)
    if not match:
        raise ValueError("Missing Mermaid block")
    return match.group(1).strip()


def parse_recipe(path: Path) -> Recipe:
    text = read_text(path)
    frontmatter, rest = parse_frontmatter(text)
    mermaid = parse_mermaid_block(rest)
    return Recipe(path=path, frontmatter=frontmatter, mermaid=mermaid)


def recipe_paths(root: Path) -> List[Path]:
    recipes_dir = root / "recipes"
    if not recipes_dir.exists():
        return []
    return sorted(recipes_dir.rglob("*.md"))


def normalize_lines(text: str) -> List[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def parse_flowchart(mermaid: str):
    lines = normalize_lines(mermaid)
    if not lines or not lines[0].lower().startswith("flowchart"):
        raise ValueError("Mermaid block must start with 'flowchart' line")

    nodes: Dict[str, Dict[str, str]] = {}
    edges: List[Dict[str, str]] = []

    for line in lines[1:]:
        if "-->" in line:
            left, right = [part.strip() for part in line.split("-->", 1)]
            label = None
            if "|" in left:
                left, label = [part.strip() for part in left.split("|", 1)]
                label = label.strip("|")
            if "|" in right:
                # Keep right side label if present (rare)
                right = right.split("|", 1)[0].strip()
            try:
                source_id, source_data = parse_node(left)
                if source_id not in nodes or nodes[source_id].get("type") == "unknown":
                    nodes[source_id] = source_data
                source = source_id
            except Exception:
                source = left
            try:
                target_id, target_data = parse_node(right)
                if target_id not in nodes or nodes[target_id].get("type") == "unknown":
                    nodes[target_id] = target_data
                target = target_id
            except Exception:
                target = right
            edges.append({"source": source, "target": target, "label": label})
            continue
        if ":::" in line:
            line = line.split(":::", 1)[0].strip()
        if line:
            node_id, node_data = parse_node(line)
            nodes[node_id] = node_data

    # infer nodes from edges
    for edge in edges:
        for node_id in (edge["source"], edge["target"]):
            if node_id not in nodes:
                nodes[node_id] = {"type": "unknown", "label": node_id}
    return nodes, edges


def parse_node(line: str) -> Tuple[str, Dict[str, str]]:
    match = re.match(r"^([A-Za-z0-9_]+)\s*(.*)$", line)
    if not match:
        raise ValueError(f"Invalid node line: {line}")
    node_id = match.group(1)
    rest = match.group(2).strip()
    if rest.startswith("([Start"):
        return node_id, {"type": "start", "label": "Start"}
    if rest.startswith("([End"):
        return node_id, {"type": "end", "label": "End"}
    if rest.startswith("{{") and rest.endswith("}}"):
        inner = rest[2:-2].strip()
        return node_id, {"type": "decision", "label": inner}
    if rest.startswith("[") and rest.endswith("]"):
        inner = rest[1:-1].strip()
        if ":" in inner:
            kind, value = [part.strip() for part in inner.split(":", 1)]
            if kind == "Screen":
                return node_id, {"type": "screen", "screen": value}
            if kind == "Assignment":
                return node_id, {"type": "assignment", "expression": value}
            return node_id, {"type": "action", "action": kind, "value": value}
        return node_id, {"type": "action", "action": inner, "value": ""}
    return node_id, {"type": "unknown", "label": node_id}


def validate_graph(nodes, edges):
    errors = []
    start_nodes = [nid for nid, data in nodes.items() if data.get("type") == "start"]
    end_nodes = [nid for nid, data in nodes.items() if data.get("type") == "end"]
    if len(start_nodes) != 1:
        errors.append("Exactly one Start node required")
    if len(end_nodes) != 1:
        errors.append("Exactly one End node required")

    outgoing = {nid: [] for nid in nodes}
    incoming = {nid: [] for nid in nodes}
    for edge in edges:
        outgoing.setdefault(edge["source"], []).append(edge)
        incoming.setdefault(edge["target"], []).append(edge)

    for nid, data in nodes.items():
        if data.get("type") == "decision":
            if not outgoing.get(nid):
                errors.append(f"Decision {nid} has no outgoing edges")
            for edge in outgoing.get(nid, []):
                if not edge.get("label"):
                    errors.append(f"Decision {nid} outgoing edge missing label")

    # orphan nodes
    for nid in nodes:
        if nid in start_nodes:
            continue
        if not incoming.get(nid):
            errors.append(f"Node {nid} is unreachable")

    # cycle detection
    visited = set()
    visiting = set()

    def visit(node):
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for edge in outgoing.get(node, []):
            if visit(edge["target"]):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    if start_nodes:
        if visit(start_nodes[0]):
            errors.append("Graph is cyclic")

    return errors


def stable_name(flow_name: str, node_id: str, suffix: str) -> str:
    return f"{flow_name}__{node_id}_{suffix}"


def build_flow_xml(flow_name: str, api_version: str, nodes, edges, screens: Dict[str, object], record_vars: Dict[str, str]) -> str:
    ET.register_namespace("", "http://soap.sforce.com/2006/04/metadata")
    flow = ET.Element("Flow")
    api = ET.SubElement(flow, "apiVersion")
    api.text = str(api_version)
    label = ET.SubElement(flow, "label")
    label.text = flow_name
    status = ET.SubElement(flow, "status")
    status.text = "Active"

    for var_def in build_form_variables(screens):
        flow.append(var_def)
    for var_def in build_record_variables(record_vars):
        flow.append(var_def)

    # Build elements
    decisions = []
    actions = []
    assignments = []
    screens_nodes = []
    end_nodes = []
    start_nodes = []
    element_names = {}

    for node_id in sorted(nodes):
        data = nodes[node_id]
        ntype = data.get("type")
        if ntype == "start":
            start_nodes.append(node_id)
        elif ntype == "decision":
            decisions.append(node_id)
            element_names[node_id] = stable_name(flow_name, node_id, "Decision")
        elif ntype == "screen":
            screens_nodes.append(node_id)
            element_names[node_id] = stable_name(flow_name, node_id, "Screen")
        elif ntype == "action":
            actions.append(node_id)
            element_names[node_id] = stable_name(flow_name, node_id, "Action")
        elif ntype == "assignment":
            assignments.append(node_id)
            element_names[node_id] = stable_name(flow_name, node_id, "Assignment")
        elif ntype == "end":
            end_nodes.append(node_id)
            element_names[node_id] = stable_name(flow_name, node_id, "End")

    for node_id in decisions:
        decision = ET.SubElement(flow, "decisions")
        ET.SubElement(decision, "name").text = element_names[node_id]
        ET.SubElement(decision, "label").text = nodes[node_id].get("label", node_id)

        rules = []
        for edge in edges:
            if edge["source"] == node_id:
                rule = ET.Element("rules")
                ET.SubElement(rule, "name").text = stable_name(flow_name, f"{node_id}_{edge['label']}", "Rule")
                ET.SubElement(rule, "label").text = edge["label"] or "Outcome"
                rule.append(make_connector(element_names, edge["target"]))
                rules.append(rule)
        for rule in sorted(rules, key=lambda r: r.findtext("name")):
            decision.append(rule)

    for node_id in screens_nodes:
        screen_node = nodes[node_id]
        screen_key = screen_node.get("screen")
        screen_def = screens.get(screen_key, {})
        screen = ET.SubElement(flow, "screens")
        ET.SubElement(screen, "name").text = element_names[node_id]
        ET.SubElement(screen, "label").text = screen_def.get("label", screen_key or node_id)
        if screen_def.get("nextLabel"):
            ET.SubElement(screen, "nextLabel").text = str(screen_def.get("nextLabel"))
        if screen_def.get("backLabel"):
            ET.SubElement(screen, "backLabel").text = str(screen_def.get("backLabel"))
        fields = build_screen_fields(screen_key, screen_def)
        for field in fields:
            screen.append(field)
        for edge in edges:
            if edge["source"] == node_id:
                screen.append(make_connector(element_names, edge["target"]))
                break

    for node_id in actions:
        action = ET.SubElement(flow, "actions")
        ET.SubElement(action, "name").text = element_names[node_id]
        ET.SubElement(action, "label").text = node_id
        kind = nodes[node_id].get("action", "Action")
        target = nodes[node_id].get("value", "")
        ET.SubElement(action, "actionType").text = kind
        if target:
            ET.SubElement(action, "targetObject").text = target
        if kind == "RecordCreate":
            record_var = select_record_var(record_vars, target)
            if record_var:
                ET.SubElement(action, "inputReference").text = record_var
        for edge in edges:
            if edge["source"] == node_id:
                action.append(make_connector(element_names, edge["target"]))
                break

    for node_id in assignments:
        assignment = ET.SubElement(flow, "assignments")
        ET.SubElement(assignment, "name").text = element_names[node_id]
        ET.SubElement(assignment, "label").text = node_id
        expression = nodes[node_id].get("expression", "")
        assign_item = build_assignment_item(expression)
        assignment.append(assign_item)
        for edge in edges:
            if edge["source"] == node_id:
                assignment.append(make_connector(element_names, edge["target"]))
                break

    for node_id in end_nodes:
        end = ET.SubElement(flow, "end")
        ET.SubElement(end, "name").text = element_names[node_id]
        ET.SubElement(end, "label").text = "End"

    for node_id in start_nodes:
        start = ET.SubElement(flow, "start")
        ET.SubElement(start, "label").text = "Start"
        for edge in edges:
            if edge["source"] == node_id:
                start.append(make_connector(element_names, edge["target"]))
                break

    indent_xml(flow, indent="  ")
    xml_bytes = ET.tostring(flow, encoding="utf-8", xml_declaration=True, method="xml")
    return xml_bytes.decode("utf-8") + "\n"


def make_connector(element_names: Dict[str, str], target_node: str) -> ET.Element:
    connector = ET.Element("connector")
    ET.SubElement(connector, "targetReference").text = element_names.get(target_node, target_node)
    return connector


def indent_xml(elem: ET.Element, level: int = 0, indent: str = "  ") -> None:
    i = "\n" + indent * level
    if len(elem):
        if elem.text is None or elem.text.strip() == "":
            elem.text = i + indent
        for child in elem:
            indent_xml(child, level + 1, indent)
            if child.tail is None or child.tail.strip() == "":
                child.tail = i + indent
        if elem[-1].tail is not None:
            elem[-1].tail = i
    else:
        if elem.text is None:
            elem.text = ""
    return


def build_form_variables(screens: Dict[str, object]) -> List[ET.Element]:
    variables = []
    seen = set()
    for screen_key in sorted(screens):
        screen_def = screens.get(screen_key, {})
        for component in screen_def.get("components", []) or []:
            if not isinstance(component, dict):
                continue
            ctype = component.get("type")
            name = component.get("name")
            if not name or ctype in ("displayText", "lwc"):
                continue
            var_name = f"form_{name}"
            if var_name in seen:
                continue
            seen.add(var_name)
            data_type = screen_component_type(ctype)
            var = ET.Element("variables")
            ET.SubElement(var, "name").text = var_name
            ET.SubElement(var, "dataType").text = data_type
            ET.SubElement(var, "isCollection").text = "false"
            ET.SubElement(var, "isInput").text = "true"
            ET.SubElement(var, "isOutput").text = "true"
            variables.append(var)
    return variables


def build_record_variables(record_vars: Dict[str, str]) -> List[ET.Element]:
    variables = []
    for var_name in sorted(record_vars):
        var = ET.Element("variables")
        ET.SubElement(var, "name").text = var_name
        ET.SubElement(var, "dataType").text = "SObject"
        ET.SubElement(var, "isCollection").text = "false"
        ET.SubElement(var, "isInput").text = "false"
        ET.SubElement(var, "isOutput").text = "false"
        ET.SubElement(var, "objectType").text = record_vars[var_name]
        variables.append(var)
    return variables


def screen_component_type(ctype: str) -> str:
    if ctype in ("checkbox",):
        return "Boolean"
    return "String"


def build_screen_fields(screen_key: str, screen_def: Dict[str, object]) -> List[ET.Element]:
    fields = []
    display_count = 0
    lwc_count = 0
    for component in screen_def.get("components", []) or []:
        if not isinstance(component, dict):
            continue
        ctype = component.get("type")
        if ctype == "displayText":
            display_count += 1
            field = ET.Element("fields")
            ET.SubElement(field, "name").text = f"display_{screen_key}_{display_count}"
            ET.SubElement(field, "fieldType").text = "DisplayText"
            ET.SubElement(field, "fieldText").text = str(component.get("text", ""))
            fields.append(field)
            continue
        if ctype == "lwc":
            lwc_count += 1
            component_name = component.get("component") or component.get("name") or ""
            if not component_name:
                continue
            extension = component_name if ":" in component_name else f"c:{component_name}"
            field = ET.Element("fields")
            ET.SubElement(field, "name").text = f"lwc_{screen_key}_{lwc_count}"
            ET.SubElement(field, "fieldType").text = "ComponentInstance"
            ET.SubElement(field, "extensionName").text = extension
            if component.get("label"):
                ET.SubElement(field, "fieldText").text = str(component.get("label"))
            for param in normalize_component_params(component.get("inputs")):
                input_param = ET.SubElement(field, "inputParameters")
                ET.SubElement(input_param, "name").text = param["name"]
                value = ET.SubElement(input_param, "value")
                write_flow_value(value, param.get("value"))
            for param in normalize_component_params(component.get("outputs")):
                output_param = ET.SubElement(field, "outputParameters")
                ET.SubElement(output_param, "name").text = param["name"]
                assign_to = param.get("assignTo")
                if assign_to:
                    ET.SubElement(output_param, "assignToReference").text = assign_to
            fields.append(field)
            continue
        name = component.get("name")
        if not name:
            continue
        field = ET.Element("fields")
        ET.SubElement(field, "name").text = f"form_{name}"
        ET.SubElement(field, "fieldType").text = "InputField"
        ET.SubElement(field, "dataType").text = screen_component_type(ctype)
        ET.SubElement(field, "fieldText").text = str(component.get("label", name))
        required = component.get("required")
        if required is not None:
            ET.SubElement(field, "isRequired").text = "true" if required else "false"
        fields.append(field)
    return fields


def normalize_component_params(raw) -> List[Dict[str, str]]:
    if raw is None:
        return []
    if isinstance(raw, dict):
        return [{"name": k, "value": v} for k, v in raw.items()]
    if isinstance(raw, list):
        params = []
        for item in raw:
            if isinstance(item, dict) and item.get("name"):
                params.append(item)
        return params
    return []


def write_flow_value(value_elem: ET.Element, raw_value) -> None:
    if raw_value is None:
        return
    text = str(raw_value)
    if text.startswith("form."):
        text = "form_" + text.split(".", 1)[1]
    if text.startswith("form_"):
        ET.SubElement(value_elem, "elementReference").text = text
    else:
        ET.SubElement(value_elem, "stringValue").text = text


def build_assignment_item(expression: str) -> ET.Element:
    item = ET.Element("assignmentItems")
    lhs, rhs = parse_assignment_expression(expression)
    ET.SubElement(item, "assignToReference").text = lhs
    ET.SubElement(item, "operator").text = "Assign"
    value = ET.SubElement(item, "value")
    if rhs.startswith("form_"):
        ET.SubElement(value, "elementReference").text = rhs
    else:
        ET.SubElement(value, "stringValue").text = rhs
    return item


def parse_assignment_expression(expression: str) -> Tuple[str, str]:
    if "=" not in expression:
        return expression.strip(), ""
    lhs, rhs = [part.strip() for part in expression.split("=", 1)]
    if rhs.startswith("form."):
        rhs = "form_" + rhs.split(".", 1)[1]
    return lhs, rhs


def infer_record_vars(nodes: Dict[str, Dict[str, str]], screens: Dict[str, object]) -> Dict[str, str]:
    candidates = set()
    for data in nodes.values():
        if data.get("type") == "assignment":
            lhs, _ = parse_assignment_expression(data.get("expression", ""))
            match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)$", lhs.strip())
            if match:
                candidates.add(match.group(1))

    record_creates = []
    for data in nodes.values():
        if data.get("type") == "action" and data.get("action") == "RecordCreate":
            target = data.get("value")
            if target:
                record_creates.append(target)

    record_vars: Dict[str, str] = {}
    for var in sorted(candidates):
        if var == "contact":
            record_vars[var] = "Contact"
            continue
        if var == "membership":
            record_vars[var] = "Membership__c"
            continue
        inferred = infer_object_from_record_creates(var, record_creates)
        if inferred:
            record_vars[var] = inferred
    return record_vars


def infer_object_from_record_creates(var_name: str, record_creates: List[str]) -> str:
    normalized = normalize_object_name(var_name)
    for target in record_creates:
        if normalize_object_name(target) == normalized:
            return target
    return ""


def normalize_object_name(name: str) -> str:
    lower = name.lower()
    if lower.endswith("__c"):
        lower = lower[:-3]
    return lower


def select_record_var(record_vars: Dict[str, str], target_object: str) -> str:
    for var_name, object_type in record_vars.items():
        if object_type == target_object:
            return var_name
    return ""


def compile_recipe(recipe: Recipe, root: Path, write_output: bool = True) -> CompileResult:
    errors = []
    fm = recipe.frontmatter
    if fm.get("recipe") != "flow":
        errors.append("recipe must be 'flow'")
    flow_name = fm.get("name")
    if not flow_name:
        errors.append("name is required")
    api_version = fm.get("apiVersion") or "65.0"
    package_dir = fm.get("packageDir") or "dig-src"

    if errors:
        return CompileResult(recipe=recipe, output_path=None, changed=False, errors=errors)

    nodes, edges = parse_flowchart(recipe.mermaid)
    errors.extend(validate_graph(nodes, edges))
    if errors:
        return CompileResult(recipe=recipe, output_path=None, changed=False, errors=errors)

    screens = fm.get("screens", {})
    if screens is None:
        screens = {}
    if not isinstance(screens, dict):
        errors.append("screens must be a mapping")

    record_vars = infer_record_vars(nodes, screens)

    for node_id, data in nodes.items():
        if data.get("type") == "screen":
            screen_key = data.get("screen")
            if not screen_key or screen_key not in screens:
                errors.append(f"Screen node {node_id} references missing screen '{screen_key}'")

    if errors:
        return CompileResult(recipe=recipe, output_path=None, changed=False, errors=errors)

    flow_xml = build_flow_xml(flow_name, api_version, nodes, edges, screens, record_vars)
    out_path = root / package_dir / "main" / "default" / "flows" / f"{flow_name}.flow-meta.xml"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    existing = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
    changed = existing != flow_xml
    if write_output:
        out_path.write_text(flow_xml, encoding="utf-8")
    return CompileResult(recipe=recipe, output_path=out_path, changed=changed, errors=[])


def load_lockfile(path: Path):
    if not path.exists():
        return {"recipes": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def write_lockfile(path: Path, data: Dict[str, object]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def compile_all(root: Path) -> Tuple[List[CompileResult], Dict[str, object]]:
    results: List[CompileResult] = []
    lock = {"recipes": {}}

    for path in recipe_paths(root):
        recipe = parse_recipe(path)
        result = compile_recipe(recipe, root)
        results.append(result)
        recipe_hash = sha256_bytes(read_text(path).encode("utf-8"))
        output_hash = ""
        if result.output_path and result.output_path.exists():
            output_hash = sha256_bytes(result.output_path.read_bytes())
        lock["recipes"][str(path)] = {
            "recipeHash": recipe_hash,
            "output": str(result.output_path) if result.output_path else "",
            "outputHash": output_hash,
        }
    return results, lock


def doctor(root: Path) -> List[str]:
    issues = []
    lock_path = root / "geary" / "out" / "recipes.lock.json"
    lock = load_lockfile(lock_path)
    current = {}
    for path in recipe_paths(root):
        try:
            recipe = parse_recipe(path)
            result = compile_recipe(recipe, root, write_output=False)
            if result.errors:
                issues.extend([f"{path}: {err}" for err in result.errors])
            recipe_hash = sha256_bytes(read_text(path).encode("utf-8"))
            output_hash = ""
            if result.output_path and result.output_path.exists():
                output_hash = sha256_bytes(result.output_path.read_bytes())
            current[str(path)] = {"recipeHash": recipe_hash, "outputHash": output_hash}
        except Exception as exc:
            issues.append(f"{path}: {exc}")

    for path, data in lock.get("recipes", {}).items():
        current_data = current.get(path)
        if not current_data:
            issues.append(f"Lockfile has missing recipe: {path}")
            continue
        if current_data["recipeHash"] != data.get("recipeHash"):
            issues.append(f"Recipe changed since lockfile: {path}")
        if current_data["outputHash"] != data.get("outputHash"):
            issues.append(f"Output changed since lockfile: {path}")

    return issues


def load_alias_directives(root: Path):
    directives = []
    for path in recipe_paths(root):
        try:
            recipe = parse_recipe(path)
        except Exception:
            continue
        fm = recipe.frontmatter
        alias = None
        slice_cfg = fm.get("slice", {})
        if isinstance(slice_cfg, dict):
            alias = slice_cfg.get("alias")
            with_deps = slice_cfg.get("withDeps", False)
        else:
            alias = fm.get("slice.alias")
            with_deps = fm.get("slice.withDeps", False)
        deploy_cfg = fm.get("deploy", {})
        target_org = None
        if isinstance(deploy_cfg, dict):
            target_org = deploy_cfg.get("targetOrg")
        else:
            target_org = fm.get("deploy.targetOrg")
        if alias:
            directives.append({"alias": alias, "withDeps": bool(with_deps), "targetOrg": target_org})
    return directives


def recipe_index(root: Path) -> List[Dict[str, object]]:
    items = []
    for path in recipe_paths(root):
        try:
            recipe = parse_recipe(path)
        except Exception:
            continue
        fm = recipe.frontmatter
        name = fm.get("name")
        slice_cfg = fm.get("slice", {}) if isinstance(fm.get("slice"), dict) else {}
        deploy_cfg = fm.get("deploy", {}) if isinstance(fm.get("deploy"), dict) else {}
        items.append(
            {
                "path": str(path),
                "name": name,
                "alias": slice_cfg.get("alias"),
                "targetOrg": deploy_cfg.get("targetOrg"),
            }
        )
    return items


def merge_aliases(alias_path: Path, slice_names: List[str], directives: List[Dict[str, object]]):
    if not directives:
        return "aliases: added 0, skipped 0 (already exists), skipped 0 (missing target slice)"

    valid = []
    for directive in directives:
        includes = ["flows"]
        if all(item in slice_names for item in includes):
            valid.append({"alias": directive["alias"], "includes": includes, "withDeps": directive.get("withDeps", False)})
    skipped_missing = len(directives) - len(valid)

    if not alias_path.exists():
        lines = ["version: 1", "aliases:"]
        added = 0
        for item in sorted(valid, key=lambda x: x["alias"]):
            lines.extend(render_alias(item))
            added += 1
        alias_path.parent.mkdir(parents=True, exist_ok=True)
        alias_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return f"aliases: added {added}, skipped 0 (already exists), skipped {skipped_missing} (missing target slice)"

    content = alias_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    existing_aliases = set()
    aliases_index = None
    for idx, line in enumerate(lines):
        if line.strip() == "aliases:":
            aliases_index = idx
            break
    if aliases_index is not None:
        idx = aliases_index + 1
        while idx < len(lines):
            line = lines[idx]
            if line and not line.startswith(" "):
                break
            if line.startswith("  ") and line.strip().endswith(":") and not line.strip().startswith("-"):
                existing_aliases.add(line.strip()[:-1])
            idx += 1
        insert_at = idx
    else:
        lines.append("aliases:")
        insert_at = len(lines)

    added = 0
    skipped_exists = 0
    to_add = []
    for item in sorted(valid, key=lambda x: x["alias"]):
        if item["alias"] in existing_aliases:
            skipped_exists += 1
            continue
        to_add.extend(render_alias(item))
        added += 1

    if to_add:
        lines[insert_at:insert_at] = to_add
    alias_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f"aliases: added {added}, skipped {skipped_exists} (already exists), skipped {skipped_missing} (missing target slice)"


def render_alias(item: Dict[str, object]) -> List[str]:
    lines = [f"  {item['alias']}:"]
    lines.append(f"    includes: [{', '.join(item['includes'])}]")
    if item.get("withDeps"):
        lines.append("    withDeps: true")
    return lines


def main(argv: List[str]) -> int:
    if not argv:
        print("Usage: recipes.py <compile|doctor>")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
