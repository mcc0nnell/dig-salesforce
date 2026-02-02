# Geary Muni

## What Geary is
Geary is “apt-get for Salesforce metadata slices.” A slice is a generated `package.xml` manifest that targets a specific set of metadata (flows, reports, dashboards). An alias is a human-friendly name that maps to one or more slices.

## Quickstart
```bash
python tools/geary/geary.py update --root .
python tools/geary/geary.py list
python tools/geary/geary.py doctor --root .
python tools/geary/geary.py install flows --target-org deafingov
python tools/geary/geary.py install dashboards-summit__SummitEventsDashboards --target-org deafingov --with-deps
```

## Capabilities (at a glance)
- Slice builder: scans package directories and generates deterministic `package.xml` slices for flows, reports, and dashboards (including folder metadata).
- Dependency resolver: wires dashboards to their referenced report folders/slices.
- Alias layer: human-friendly names map to one or more slices with optional dependency behavior.
- Health checks: `doctor` flags missing slices, missing folder metadata, and empty slices.
- Recipes (v1): compile Mermaid flowcharts into Flow XML, maintain a lockfile, and install via aliases.

## CLI reference (core)
```bash
python tools/geary/geary.py update --root .
python tools/geary/geary.py list
python tools/geary/geary.py graph
python tools/geary/geary.py doctor --root .
python tools/geary/geary.py doctor
python tools/geary/geary.py install <slice-or-alias> --target-org deafingov --with-deps
python tools/geary/geary.py install --all --target-org deafingov
```

## How it works
Slices live in:
- `manifest/slice-*.xml`
- `geary/out/slices.json`
- `geary/out/slices.md`

Geary scans `packageDirectories` from `sfdx-project.json` (commonly `dig-src`). Ordering is deterministic: type/member ordering is stable, and outputs are repeatable. Dependency rules:
- `dashboards-*` depends on the `reports-*` it references
- global `dashboards` depends on global `reports`

### Slice builder details
- Scans all `packageDirectories` (or `--package-dir` overrides) and looks under `main/default`.
- Produces global slices (`flows`, `reports`, `dashboards`, `apex`) and per-folder slices (`reports-<Folder>`, `dashboards-<Folder>`).
- Produces per-type Apex slices (`apex-classes`, `apex-triggers`) when those members exist.
- Optionally produces UI/security slices (`lwc`, `aura`, `permissionsets`, `profiles`) when those members exist.
- Dashboards slices include referenced reports and report folders.
- Empty slices are not emitted by default (use `--include-empty` if needed).

### Determinism guarantees
- Stable type ordering and member ordering.
- No timestamps in generated files.
- Recipes lockfile tracks hashes of recipe inputs and outputs.

## Folder metadata nuance
SFDX source stores folder metadata in:
- `dig-src/main/default/reports/<Folder>.reportFolder-meta.xml`
- `dig-src/main/default/dashboards/<Folder>.dashboardFolder-meta.xml`

Geary supports both legacy and SFDX layouts. Missing folder metadata breaks fresh-org installs because the folder itself must exist before report/dashboard members can deploy cleanly.

## Aliases (how to use and edit)
Aliases live in `geary/slices.yml` and map to one or more canonical slices. `withDeps` controls default dependency installation.

Example:
```yaml
aliases:
  summit-analytics:
    includes: [dashboards-summit__SummitEventsDashboards]
    withDeps: true
```

Safety rule: aliases must target existing slices; `geary doctor` flags broken aliases.

Alias behavior:
- `geary install <name>` accepts either a canonical slice name or an alias.
- Aliases can include multiple slices; install order is deterministic and respects dependencies.

## Getting analytics into source
List folders:
```bash
sf org list metadata -o deafingov -m ReportFolder
sf org list metadata -o deafingov -m DashboardFolder
```

List items in a folder (Summit example):
```bash
sf org list metadata -o deafingov -m Report --folder summit__SummitEventsReports --json > /tmp/summit_reports.json
sf org list metadata -o deafingov -m Dashboard --folder summit__SummitEventsDashboards --json > /tmp/summit_dashboards.json
```

Retrieve folder metadata:
```bash
sf project retrieve start -o deafingov --metadata "ReportFolder:summit__SummitEventsReports"
sf project retrieve start -o deafingov --metadata "DashboardFolder:summit__SummitEventsDashboards"
```

Retrieve members:
```bash
python - <<'PY'
import json, subprocess

def retrieve(kind, json_path):
    d=json.load(open(json_path))
    items=[r["fullName"] for r in d.get("result",[])]
    if not items:
        raise SystemExit(f"No {kind} items in {json_path}")
    for full in items:
        meta=f"{kind}:{full}"
        print("Retrieving", meta)
        subprocess.run(["sf","project","retrieve","start","-o","deafingov","--metadata",meta], check=True)

retrieve("Report", "/tmp/summit_reports.json")
retrieve("Dashboard", "/tmp/summit_dashboards.json")
PY
```

Then run:
```bash
python tools/geary/geary.py update --root .
```

## Troubleshooting
- “zsh: command not found: #” → don’t paste comment lines; only paste commands
- “No metadata found for type Report/Dashboard” → must list by folder; use ReportFolder/DashboardFolder first
- “Slice has 0 members” → add metadata to source or use `--include-empty` / fix scan paths
- “Managed package assets” → retrieve may be allowed; if blocked, use your own non-namespaced folder

## Operator checklist
- Pull latest source and confirm `sf` auth for `deafingov`.
- Run `python tools/geary/geary.py update --root .` to refresh slices.
- Run `python tools/geary/geary.py doctor --root .` and fix errors before deploy.
- Use `python tools/geary/geary.py list` to confirm aliases/slices.
- Install with `--with-deps` when deploying dashboards or aliases that expect dependencies.
- Re-run `recipe compile` if any recipe files changed.

## Recipes (v1)
Recipes live in `recipes/` as Markdown with YAML frontmatter and exactly one Mermaid `flowchart TD` block. They compile into deterministic Flow metadata under `dig-src/main/default/flows/` and maintain a lockfile at `geary/out/recipes.lock.json`.
Generated Flow XML is deterministically pretty-printed for human review.
Mermaid intake (AST cache only): `docs/geary/mermaid-intake.md`.

Commands:
```bash
python tools/geary/geary.py recipe compile --root .
python tools/geary/geary.py recipe doctor --root .
python tools/geary/geary.py recipe install summit-sample --target-org deafingov
```

Recipe behavior:
- `compile` validates all recipes and writes Flow XML + lockfile.
- `doctor` checks recipe validity and lockfile consistency.
- `install` compiles recipes, runs `geary update`, then installs by alias or falls back to the `flows` slice.
- If a recipe frontmatter defines `slice.alias`, Geary safely merges it into `geary/slices.yml` when the target slice exists.

Node conventions:
- Start and End: `Start([Start])` and `End([End])`
- Decisions: `D{{Decision: "Question"}}` with labeled outgoing edges (e.g., `D|Yes| --> ...`)
- Actions: `[RecordCreate: ObjectApiName]`, `[RecordUpdate: ObjectApiName]`, `[Apex: Class.method]`, `[Subflow: FlowApiName]`
- Screens: `[Screen: Key]` where `Key` is defined under `screens:` in frontmatter
- Assignments: `[Assignment: lhs = rhs]` (use `form.<name>` to read screen inputs; compiler writes `form_<name>` variables)
  - Assignments to `recordVar.Field` auto-create a record variable and are used as input for `RecordCreate` of the matching object.

Screens frontmatter example:
```yaml
screens:
  Welcome:
    label: "Welcome"
    nextLabel: "Continue"
    backLabel: "Back"
    components:
      - type: inputText
        name: firstName
        label: "First name"
        required: true
```

LWC screen component example:
```yaml
screens:
  Overview:
    label: "Overview"
    components:
      - type: lwc
        component: digMembershipPanel
        label: "Membership panel"
```

## Apex (optional)
Geary can slice Apex metadata when it exists in source:
- Classes: `*/main/default/classes/*.cls` (+ `*.cls-meta.xml`)
- Triggers: `*/main/default/triggers/*.trigger` (+ `*.trigger-meta.xml`)
- Test suites (optional): `*/main/default/testSuites/*.testSuite-meta.xml`

Deploying Apex often requires tests. Use the install flags to control test behavior:
```bash
python tools/geary/geary.py install apex --target-org deafingov --test-level RunLocalTests
python tools/geary/geary.py install apex --target-org deafingov --test-level RunSpecifiedTests --tests DigOps_MembershipServiceTest,DigOps_MembershipControllerTest
python tools/geary/geary.py install apex-classes --target-org deafingov --test-level RunLocalTests
python tools/geary/geary.py install apex-triggers --target-org deafingov --test-level RunLocalTests
```

Troubleshooting:
- “Apex present” note in `doctor` → include `--test-level` in installs.
- “Invalid tests” → confirm test class names exist in source and are included in the slice.

## LWC (optional)
Lightning Web Components are detected from:
- `dig-src/main/default/lwc/<BundleName>/...`

Deploy with:
```bash
python tools/geary/geary.py install lwc --target-org deafingov
```

Troubleshooting:
- “LWC present” note in `doctor` → ensure CSP Trusted Sites / CORS endpoints exist for external API calls.

## CSP Trusted Sites (optional)
CSP Trusted Sites metadata lives in:
- `dig-src/main/default/cspTrustedSites/`

Deploy with:
```bash
python tools/geary/geary.py install csp --target-org deafingov
```

Bundle LWC + CSP with an alias (if both slices exist):
```yaml
aliases:
  lwc-web:
    includes: [lwc, csp]
```

Troubleshooting:
- If LWCs call external endpoints, add `CSPTrustedSite` metadata and deploy the `csp` slice.
- Profiles are noisy and often permission-gated; deploy them only if required.

## FAQ
**Which org alias should I use?**  
Use `deafingov` unless you’ve been told otherwise.

**Why did my dashboard slice fail?**  
Dashboards depend on reports and report folders. Use `--with-deps` or install the related reports slice first.

**Why is my alias missing?**  
Aliases only get created for slices that exist. Run `geary update` and confirm the slice appears in `geary/out/slices.json`.

**Why is a slice empty or missing?**  
The scanner only includes metadata present under `packageDirectories`. Add the metadata to source or run `slices.py` with `--include-empty`.

**Do recipes overwrite my flows?**  
Recipes write deterministic Flow XML for the recipe’s `name`. Changes are tracked in `geary/out/recipes.lock.json`.
## Repo conventions
Target org alias is `deafingov`. The default API version is derived from the repo/manifest (currently 65.0).
