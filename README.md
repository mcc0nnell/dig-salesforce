# deafingov Salesforce

Operations-friendly Salesforce source for *deafingov*.
This repo keeps DIG-owned metadata in `dig-src/main/default/`, slices it into small manifests, and captures operator runbooks for retrieval/deploy/cleanup.

## Quick setup & validation
1. Authenticate and point `sf` at the default org:
   ```bash
   sf org display --target-org deafingov
   ```
2. Work out of `dig-src/main/default/` and edit metadata only when you understand the downstream deploy.
3. Validate before any deploy:
   ```bash
   make dig-validate
   ```

## Slice manifests (only deploy what you need)
| Slice | Description | Command |
| --- | --- | --- |
| `manifest/governance-mvp.xml` | Governance objects + tabs, flexipages, permission sets | `sf project deploy start --target-org deafingov --manifest manifest/governance-mvp.xml` |
| `manifest/membership-core.xml` | Membership object, supporting fields, flows, and permission sets | `sf project deploy start --target-org deafingov --manifest manifest/membership-core.xml` |
| `manifest/quarantine.xml` | Known-broken list views/reports/dashboards | Use only for diagnosis/retrieval | 

Back-compat manifests that operators may still use:
- `manifest/membership-mvp-package.xml` (legacy “MVP” membership slice; kept for existing deploy muscle memory).
- `manifest/governance-mvp-package.xml` (legacy governance slice; identical intent to `manifest/governance-mvp.xml`).

### Helpful wrappers
```bash
make dig-validate              # dry-run the entire dig source directory
make deploy-governance         # deploy governance MVP slice
make deploy-membership         # deploy membership core slice
``` 

## Validation + deploy order tips
- Prefer validating against `manifest/governance-mvp.xml`/`membership-core.xml` before releasing.
- Deploy DIG Ops artifacts in order: list views → reports → dashboards (even if reports/dashboards live in quarantine, keep the run order documented in `docs/runbooks/deploy-slices.md`).
- Core objects (Case, Membership, Ops_Change_Log) should land before UI metadata that depends on them.

## Known issues & quarantine
- Quarantine is for metadata we want tracked but not shipped by default. In this repo it currently captures experimental UI metadata (see `manifest/quarantine.xml`) and is excluded from normal validate/deploy via `.forceignore`.
- Avoid retrieving or deploying the quarantine manifest during routine releases; pull it only when you need to inspect why a component keeps failing.

## Inventory & metadata guidance
- The canonical inventory is documented in `docs/architecture/metadata-inventory.md` with CORE vs OPTIONAL vs QUARANTINE categories.
- Keep DIG-owned metadata under `dig-src/main/default/` and avoid touching `force-app/` unless you are actively managing legacy artifacts.
- Use `manifest/dig.xml` (or a tight slice manifest) when a change spans multiple modules.

## Runbooks and deeper guidance
- Slice deploy playbook: `docs/runbooks/deploy-slices.md`.
- Add new operator docs under `docs/runbooks/`.

## Local housekeeping
- `tmp/` holds ephemeral files (ignored by Git), `fixtures/_incoming/` stages problematic metadata, and `scripts/` contains helper wrappers like `scripts/membership.sh`.
- Respect `.gitignore`, keep `.editorconfig` settings consistent, and do not introduce new package managers—only the existing npm tooling remains.
