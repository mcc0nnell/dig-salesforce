#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

FLOW_SUFFIX = ".flow-meta.xml"
REPORT_SUFFIX = ".report-meta.xml"
DASHBOARD_SUFFIX = ".dashboard-meta.xml"
REPORT_FOLDER_SUFFIX = ".reportFolder-meta.xml"
DASHBOARD_FOLDER_SUFFIX = ".dashboardFolder-meta.xml"

TYPE_ORDER = [
    "Flow",
    "ApexClass",
    "ApexTrigger",
    "ApexTestSuite",
    "LightningComponentBundle",
    "AuraDefinitionBundle",
    "PermissionSet",
    "Profile",
    "ReportFolder",
    "Report",
    "DashboardFolder",
    "Dashboard",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Generate geary slice manifests and registry.")
    parser.add_argument("--root", default=".", help="Repo root (default: .)")
    parser.add_argument("--out", default="geary/out", help="Output directory for registry files")
    parser.add_argument("--manifest-dir", default="manifest", help="Manifest output directory")
    parser.add_argument("--package-dir", action="append", help="Override package directory path (repeatable)")
    parser.add_argument("--include-empty", action="store_true", help="Include empty slices in output")
    return parser.parse_args()


def version_key(version_str):
    parts = []
    for chunk in version_str.strip().split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def detect_api_version(root: Path) -> str:
    candidates = set()
    manifest_dir = root / "manifest"
    xml_paths = []
    if manifest_dir.exists():
        xml_paths.extend(sorted(manifest_dir.rglob("*.xml")))
    xml_paths.extend(sorted(root.rglob("package.xml")))
    version_re = re.compile(r"<version>([^<]+)</version>")
    for path in xml_paths:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        match = version_re.search(text)
        if match:
            candidates.add(match.group(1).strip())
    if not candidates:
        return "60.0"
    return sorted(candidates, key=version_key)[-1]


def strip_suffix(name: str, suffix: str) -> str:
    if name.endswith(suffix):
        return name[: -len(suffix)]
    return name


def collect_text_nodes(elem):
    if elem.text:
        yield elem.text
    for child in elem:
        yield from collect_text_nodes(child)
        if child.tail:
            yield child.tail


def extract_report_refs(texts, known_reports):
    found = set()
    missing = set()
    pattern = re.compile(r"[A-Za-z0-9_ \-]+/[A-Za-z0-9_ \-]+")
    for text in texts:
        for match in pattern.findall(text):
            candidate = match.strip()
            if not candidate or "/" not in candidate:
                continue
            if candidate in known_reports:
                found.add(candidate)
            else:
                missing.add(candidate)
    return found, missing


def write_manifest(path: Path, api_version: str, members_by_type):
    lines = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>", "<Package xmlns=\"http://soap.sforce.com/2006/04/metadata\">"]
    for type_name in TYPE_ORDER:
        members = members_by_type.get(type_name, [])
        if not members:
            continue
        lines.append("  <types>")
        for member in members:
            lines.append(f"    <members>{member}</members>")
        lines.append(f"    <name>{type_name}</name>")
        lines.append("  </types>")
    lines.append(f"  <version>{api_version}</version>")
    lines.append("</Package>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_alias_file(alias_path: Path, slice_names):
    desired_aliases = {
        "all-flows": {"includes": ["flows"], "withDeps": False},
        "all-apex": {"includes": ["apex"], "withDeps": False},
        "all-apex-classes": {"includes": ["apex-classes"], "withDeps": False},
        "all-apex-triggers": {"includes": ["apex-triggers"], "withDeps": False},
        "all-lwc": {"includes": ["lwc"], "withDeps": False},
        "all-aura": {"includes": ["aura"], "withDeps": False},
        "all-permissionsets": {"includes": ["permissionsets"], "withDeps": False},
        "all-profiles": {"includes": ["profiles"], "withDeps": False},
        "summit-reports": {"includes": ["reports-summit__SummitEventsReports"], "withDeps": False},
        "summit-analytics": {"includes": ["dashboards-summit__SummitEventsDashboards"], "withDeps": True},
        "all-reports": {"includes": ["reports"], "withDeps": False},
        "all-analytics": {"includes": ["dashboards"], "withDeps": True},
    }

    def valid_aliases():
        valid = {}
        for alias, data in desired_aliases.items():
            includes = data.get("includes", [])
            if includes and all(item in slice_names for item in includes):
                valid[alias] = data
        return valid

    def alias_lines(alias, data):
        lines = [f"  {alias}:"]
        lines.append(f"    includes: [{', '.join(data['includes'])}]")
        if data.get("withDeps"):
            lines.append("    withDeps: true")
        return lines

    valid = valid_aliases()

    added = 0
    skipped_exists = 0
    skipped_missing = len(desired_aliases) - len(valid)

    if not alias_path.exists():
        lines = ["version: 1", "aliases:"]
        for alias in sorted(valid):
            lines.extend(alias_lines(alias, valid[alias]))
            added += 1
        alias_path.parent.mkdir(parents=True, exist_ok=True)
        alias_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"aliases: added {added}, skipped {skipped_exists} (already exists), skipped {skipped_missing} (missing target slice)")
        return

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

    to_add = []
    for alias in sorted(valid):
        if alias in existing_aliases:
            skipped_exists += 1
            continue
        to_add.extend(alias_lines(alias, valid[alias]))
        added += 1

    if to_add:
        lines[insert_at:insert_at] = to_add

    alias_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"aliases: added {added}, skipped {skipped_exists} (already exists), skipped {skipped_missing} (missing target slice)")


def resolve_package_dirs(root: Path, override_paths):
    if override_paths:
        return [root / Path(item) for item in override_paths]

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


def compute_counts(members_by_type):
    return {
        "dashboards": len(members_by_type.get("Dashboard", [])),
        "reports": len(members_by_type.get("Report", [])),
        "folders": len(members_by_type.get("DashboardFolder", [])) + len(members_by_type.get("ReportFolder", [])),
        "flows": len(members_by_type.get("Flow", [])),
        "apexClasses": len(members_by_type.get("ApexClass", [])),
        "apexTriggers": len(members_by_type.get("ApexTrigger", [])),
        "apexTestSuites": len(members_by_type.get("ApexTestSuite", [])),
        "lwc": len(members_by_type.get("LightningComponentBundle", [])),
        "aura": len(members_by_type.get("AuraDefinitionBundle", [])),
        "permissionSets": len(members_by_type.get("PermissionSet", [])),
        "profiles": len(members_by_type.get("Profile", [])),
    }


def main():
    args = parse_args()
    root = Path(args.root).resolve()
    out_dir_arg = Path(args.out)
    manifest_dir_arg = Path(args.manifest_dir)
    if out_dir_arg.is_absolute():
        out_dir = out_dir_arg
        out_dir_rel = out_dir_arg
    else:
        out_dir_rel = out_dir_arg
        out_dir = (root / out_dir_rel).resolve()
    if manifest_dir_arg.is_absolute():
        manifest_dir = manifest_dir_arg
        try:
            manifest_dir_rel = manifest_dir_arg.relative_to(root)
        except ValueError:
            manifest_dir_rel = manifest_dir_arg
    else:
        manifest_dir_rel = manifest_dir_arg
        manifest_dir = (root / manifest_dir_rel).resolve()
    api_version = detect_api_version(root)

    package_dirs = resolve_package_dirs(root, args.package_dir)

    flows = []
    reports = []
    dashboards = []
    apex_classes = []
    apex_triggers = []
    apex_test_suites = []
    lwc_bundles = []
    aura_bundles = []
    permission_sets = []
    profiles = []
    reports_by_folder = {}
    dashboards_by_folder = {}
    report_folders = set()
    dashboard_folders = set()
    report_folder_meta = set()
    dashboard_folder_meta = set()
    dashboard_refs_by_folder = {}
    dashboard_missing_by_folder = {}
    dashboard_parse_errors = {}

    def bundle_has_files(bundle_path: Path) -> bool:
        return any(child.is_file() for child in bundle_path.rglob("*"))

    for package_dir in package_dirs:
        base = package_dir / "main" / "default"
        flows_dir = base / "flows"
        classes_dir = base / "classes"
        triggers_dir = base / "triggers"
        test_suites_dir = base / "testSuites"
        lwc_dir = base / "lwc"
        aura_dir = base / "aura"
        permissionsets_dir = base / "permissionsets"
        profiles_dir = base / "profiles"
        reports_dir = base / "reports"
        dashboards_dir = base / "dashboards"
        report_folders_dir = base / "reportFolders"
        dashboard_folders_dir = base / "dashboardFolders"

        if flows_dir.exists():
            flows.extend(
                strip_suffix(path.name, FLOW_SUFFIX)
                for path in flows_dir.glob(f"*{FLOW_SUFFIX}")
            )

        if classes_dir.exists():
            apex_classes.extend(
                strip_suffix(path.name, ".cls")
                for path in classes_dir.glob("*.cls")
            )
            apex_classes.extend(
                strip_suffix(strip_suffix(path.name, ".xml"), ".cls-meta")
                for path in classes_dir.glob("*.cls-meta.xml")
            )

        if triggers_dir.exists():
            apex_triggers.extend(
                strip_suffix(path.name, ".trigger")
                for path in triggers_dir.glob("*.trigger")
            )
            apex_triggers.extend(
                strip_suffix(strip_suffix(path.name, ".xml"), ".trigger-meta")
                for path in triggers_dir.glob("*.trigger-meta.xml")
            )

        if test_suites_dir.exists():
            apex_test_suites.extend(
                strip_suffix(strip_suffix(path.name, ".xml"), ".testSuite-meta")
                for path in test_suites_dir.glob("*.testSuite-meta.xml")
            )

        if lwc_dir.exists():
            lwc_bundles.extend(
                sorted([p.name for p in lwc_dir.iterdir() if p.is_dir() and bundle_has_files(p)])
            )

        if aura_dir.exists():
            aura_bundles.extend(
                sorted([p.name for p in aura_dir.iterdir() if p.is_dir() and bundle_has_files(p)])
            )

        if permissionsets_dir.exists():
            permission_sets.extend(
                strip_suffix(strip_suffix(path.name, ".xml"), ".permissionset-meta")
                for path in permissionsets_dir.glob("*.permissionset-meta.xml")
            )

        if profiles_dir.exists():
            profiles.extend(
                strip_suffix(strip_suffix(path.name, ".xml"), ".profile-meta")
                for path in profiles_dir.glob("*.profile-meta.xml")
            )

        if reports_dir.exists():
            for path in reports_dir.glob(f"*/*{REPORT_SUFFIX}"):
                folder = path.parent.name
                name = strip_suffix(path.name, REPORT_SUFFIX)
                reports.append(f"{folder}/{name}")
                reports_by_folder.setdefault(folder, []).append(name)
                report_folders.add(folder)

        if report_folders_dir.exists():
            report_folder_meta.update(
                strip_suffix(path.name, REPORT_FOLDER_SUFFIX)
                for path in report_folders_dir.glob(f"*{REPORT_FOLDER_SUFFIX}")
            )
        if reports_dir.exists():
            # Sanity: dig-src/main/default/reports/Summit.reportFolder-meta.xml should be detected.
            report_folder_meta.update(
                strip_suffix(path.name, REPORT_FOLDER_SUFFIX)
                for path in reports_dir.glob(f"*{REPORT_FOLDER_SUFFIX}")
            )

        if dashboards_dir.exists():
            for path in dashboards_dir.glob(f"*/*{DASHBOARD_SUFFIX}"):
                folder = path.parent.name
                name = strip_suffix(path.name, DASHBOARD_SUFFIX)
                dashboards.append(f"{folder}/{name}")
                dashboards_by_folder.setdefault(folder, []).append(name)
                dashboard_folders.add(folder)

        if dashboard_folders_dir.exists():
            dashboard_folder_meta.update(
                strip_suffix(path.name, DASHBOARD_FOLDER_SUFFIX)
                for path in dashboard_folders_dir.glob(f"*{DASHBOARD_FOLDER_SUFFIX}")
            )
        if dashboards_dir.exists():
            # Sanity: dig-src/main/default/dashboards/Summit.dashboardFolder-meta.xml should be detected.
            dashboard_folder_meta.update(
                strip_suffix(path.name, DASHBOARD_FOLDER_SUFFIX)
                for path in dashboards_dir.glob(f"*{DASHBOARD_FOLDER_SUFFIX}")
            )

    for folder, names in reports_by_folder.items():
        reports_by_folder[folder] = sorted(names)
    for folder, names in dashboards_by_folder.items():
        dashboards_by_folder[folder] = sorted(names)

    flows = sorted(set(flows))
    reports = sorted(set(reports))
    dashboards = sorted(set(dashboards))
    apex_classes = sorted(set([name for name in apex_classes if name]))
    apex_triggers = sorted(set([name for name in apex_triggers if name]))
    apex_test_suites = sorted(set([name for name in apex_test_suites if name]))
    lwc_bundles = sorted(set([name for name in lwc_bundles if name]))
    aura_bundles = sorted(set([name for name in aura_bundles if name]))
    permission_sets = sorted(set([name for name in permission_sets if name]))
    profiles = sorted(set([name for name in profiles if name]))
    report_folder_meta = sorted(report_folder_meta)
    dashboard_folder_meta = sorted(dashboard_folder_meta)

    known_reports = set(reports)
    for package_dir in package_dirs:
        dashboards_dir = package_dir / "main" / "default" / "dashboards"
        if dashboards_dir.exists():
            for path in dashboards_dir.glob(f"*/*{DASHBOARD_SUFFIX}"):
                folder = path.parent.name
                name = strip_suffix(path.name, DASHBOARD_SUFFIX)
                try:
                    tree = ET.parse(path)
                    texts = list(collect_text_nodes(tree.getroot()))
                    found, missing = extract_report_refs(texts, known_reports)
                except ET.ParseError:
                    found, missing = set(), set()
                    dashboard_parse_errors.setdefault(folder, set()).add(name)

                if found:
                    dashboard_refs_by_folder.setdefault(folder, set()).update(found)
                if missing:
                    dashboard_missing_by_folder.setdefault(folder, set()).update(missing)

    all_report_folders = sorted(set(report_folders) | set(report_folder_meta))
    all_dashboard_folders = sorted(set(dashboard_folders) | set(dashboard_folder_meta))

    slices = []

    def add_slice(name, kind, manifest_path, members_by_type, folders=None, depends_on=None, notes=None):
        counts = compute_counts(members_by_type)
        if not args.include_empty and sum(counts.values()) == 0:
            return
        slice_entry = {
            "name": name,
            "manifest": manifest_path,
            "kind": kind,
            "counts": counts,
            "dependsOn": sorted(depends_on or []),
        }
        if folders:
            slice_entry["folders"] = folders
        if notes:
            slice_entry["notes"] = sorted(notes)
        slices.append((name, slice_entry, members_by_type))

    manifest_dir.mkdir(parents=True, exist_ok=True)

    # Flows slice
    flow_members = {"Flow": flows}
    add_slice(
        "flows",
        "flows",
        str((manifest_dir_rel / "slice-flows.xml").as_posix()),
        flow_members,
    )

    # Apex slice
    apex_members = {
        "ApexClass": apex_classes,
        "ApexTrigger": apex_triggers,
        "ApexTestSuite": apex_test_suites,
    }
    add_slice(
        "apex",
        "apex",
        str((manifest_dir_rel / "slice-apex.xml").as_posix()),
        apex_members,
    )

    # Apex classes slice
    add_slice(
        "apex-classes",
        "apex",
        str((manifest_dir_rel / "slice-apex-classes.xml").as_posix()),
        {"ApexClass": apex_classes},
    )

    # Apex triggers slice
    add_slice(
        "apex-triggers",
        "apex",
        str((manifest_dir_rel / "slice-apex-triggers.xml").as_posix()),
        {"ApexTrigger": apex_triggers},
    )

    # LWC slice
    add_slice(
        "lwc",
        "lwc",
        str((manifest_dir_rel / "slice-lwc.xml").as_posix()),
        {"LightningComponentBundle": lwc_bundles},
    )

    # Aura slice
    add_slice(
        "aura",
        "aura",
        str((manifest_dir_rel / "slice-aura.xml").as_posix()),
        {"AuraDefinitionBundle": aura_bundles},
    )

    # Permission sets slice
    add_slice(
        "permissionsets",
        "permissionsets",
        str((manifest_dir_rel / "slice-permissionsets.xml").as_posix()),
        {"PermissionSet": permission_sets},
    )

    # Profiles slice
    add_slice(
        "profiles",
        "profiles",
        str((manifest_dir_rel / "slice-profiles.xml").as_posix()),
        {"Profile": profiles},
    )

    # Reports global slice
    report_folder_members = sorted(report_folder_meta)
    report_members = sorted(reports)
    report_notes = []
    for folder in sorted(report_folders):
        if folder not in report_folder_meta:
            report_notes.append(f"missing_report_folder: {folder}")
    add_slice(
        "reports",
        "reports",
        str((manifest_dir_rel / "slice-reports.xml").as_posix()),
        {"ReportFolder": report_folder_members, "Report": report_members},
        notes=report_notes or None,
    )

    # Dashboards global slice
    dashboard_folder_members = sorted(dashboard_folder_meta)
    dashboard_members = sorted(dashboards)
    referenced_reports = sorted({ref for refs in dashboard_refs_by_folder.values() for ref in refs})
    referenced_report_folders = sorted({ref.split("/")[0] for ref in referenced_reports})
    referenced_report_folder_members = sorted([folder for folder in referenced_report_folders if folder in report_folder_meta])
    dashboard_notes = []
    for folder in sorted(dashboard_folders):
        if folder not in dashboard_folder_meta and dashboards_by_folder.get(folder):
            dashboard_notes.append(f"missing_dashboard_folder: {folder}")
    for folder in referenced_report_folders:
        if folder not in report_folder_meta:
            dashboard_notes.append(f"missing_report_folder: {folder}")
    for folder, missing in dashboard_missing_by_folder.items():
        for ref in sorted(missing):
            dashboard_notes.append(f"missing_report: {ref}")
    for folder, missing in dashboard_parse_errors.items():
        for name in sorted(missing):
            dashboard_notes.append(f"dashboard_parse_error: {folder}/{name}")

    add_slice(
        "dashboards",
        "dashboards",
        str((manifest_dir_rel / "slice-dashboards.xml").as_posix()),
        {
            "ReportFolder": referenced_report_folder_members,
            "Report": referenced_reports,
            "DashboardFolder": dashboard_folder_members,
            "Dashboard": dashboard_members,
        },
        depends_on=["reports"],
        notes=dashboard_notes or None,
    )

    # Per-folder report slices
    for folder in all_report_folders:
        report_members = [f"{folder}/{name}" for name in reports_by_folder.get(folder, [])]
        folder_members = [folder] if folder in report_folder_meta else []
        notes = []
        if folder not in report_folder_meta and report_members:
            notes.append(f"missing_report_folder: {folder}")
        add_slice(
            f"reports-{folder}",
            "reports",
            str((manifest_dir_rel / f"slice-reports-{folder}.xml").as_posix()),
            {"ReportFolder": folder_members, "Report": report_members},
            folders=[folder],
            notes=notes or None,
        )

    # Per-folder dashboard slices
    for folder in all_dashboard_folders:
        dashboard_members = [f"{folder}/{name}" for name in dashboards_by_folder.get(folder, [])]
        folder_members = [folder] if folder in dashboard_folder_meta else []
        referenced_reports = sorted(dashboard_refs_by_folder.get(folder, set()))
        referenced_report_folders = sorted({ref.split("/")[0] for ref in referenced_reports})
        referenced_report_folder_members = [rf for rf in referenced_report_folders if rf in report_folder_meta]
        depends_on = [f"reports-{rf}" for rf in referenced_report_folders if rf in report_folders or rf in report_folder_meta]
        notes = []
        if folder not in dashboard_folder_meta and dashboard_members:
            notes.append(f"missing_dashboard_folder: {folder}")
        for rf in referenced_report_folders:
            if rf not in report_folder_meta:
                notes.append(f"missing_report_folder: {rf}")
        for ref in sorted(dashboard_missing_by_folder.get(folder, set())):
            notes.append(f"missing_report: {ref}")
        for name in sorted(dashboard_parse_errors.get(folder, set())):
            notes.append(f"dashboard_parse_error: {folder}/{name}")
        add_slice(
            f"dashboards-{folder}",
            "dashboards",
            str((manifest_dir_rel / f"slice-dashboards-{folder}.xml").as_posix()),
            {
                "ReportFolder": referenced_report_folder_members,
                "Report": referenced_reports,
                "DashboardFolder": folder_members,
                "Dashboard": dashboard_members,
            },
            folders=[folder],
            depends_on=depends_on,
            notes=notes or None,
        )

    # Deterministic ordering: globals then per-folder
    def slice_sort_key(item):
        name = item[0]
        if name == "flows":
            return (0, name)
        if name == "apex":
            return (1, name)
        if name == "apex-classes":
            return (2, name)
        if name == "apex-triggers":
            return (3, name)
        if name == "lwc":
            return (4, name)
        if name == "aura":
            return (5, name)
        if name == "permissionsets":
            return (6, name)
        if name == "profiles":
            return (7, name)
        if name == "reports":
            return (8, name)
        if name == "dashboards":
            return (9, name)
        if name.startswith("reports-"):
            return (10, name)
        if name.startswith("dashboards-"):
            return (11, name)
        return (12, name)

    slices.sort(key=slice_sort_key)

    slice_names = {name for name, _, _ in slices}
    for _, entry, _ in slices:
        if entry.get("dependsOn"):
            entry["dependsOn"] = [dep for dep in entry["dependsOn"] if dep in slice_names]

    for name, _, members_by_type in slices:
        manifest_path = manifest_dir / f"slice-{name}.xml"
        write_manifest(manifest_path, api_version, members_by_type)

    registry = {
        "apiVersion": api_version,
        "generatedFrom": "repo scan",
        "slices": [entry for _, entry, _ in slices],
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "slices.json").write_text(
        json.dumps(registry, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    md_lines = [
        "# Geary Slices",
        "",
        f"API version: {api_version}",
        "",
    ]
    if not reports:
        md_lines.extend(["WARNING: No reports found in scanned package directories.", ""])
    if not dashboards:
        md_lines.extend(["WARNING: No dashboards found in scanned package directories.", ""])
    md_lines.extend([
        "## Index",
    ])
    for _, entry, _ in slices:
        md_lines.append(f"- {entry['name']} ({entry['kind']})")
        md_lines.append(f"  manifest: {entry['manifest']}")
        counts = entry["counts"]
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
        md_lines.append("  counts: " + " ".join(counts_line))
        deps = entry.get("dependsOn", [])
        if deps:
            md_lines.append(f"  dependsOn: {', '.join(deps)}")
        notes = entry.get("notes")
        if notes:
            md_lines.append(f"  notes: {', '.join(notes)}")
    (out_dir / "slices.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    ensure_alias_file(root / "geary" / "slices.yml", slice_names)

    summary = {
        "flows": len(flows),
        "apexClasses": len(apex_classes),
        "apexTriggers": len(apex_triggers),
        "apexTestSuites": len(apex_test_suites),
        "lwc": len(lwc_bundles),
        "aura": len(aura_bundles),
        "permissionSets": len(permission_sets),
        "profiles": len(profiles),
        "reports": len(reports),
        "dashboards": len(dashboards),
        "reportFolders": len(all_report_folders),
        "dashboardFolders": len(all_dashboard_folders),
        "slices": len(slices),
    }
    print("geary slices: " + json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    sys.exit(main() or 0)
