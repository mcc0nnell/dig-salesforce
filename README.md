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
| `manifest/ops-listviews.xml` | DIG Ops Case list views that validate reliably | `sf project deploy start --target-org deafingov --manifest manifest/ops-listviews.xml` |
| `manifest/ops-reports.xml` | DIG Ops Admin report folder (reports themselves live in quarantine) | `sf project deploy start --target-org deafingov --manifest manifest/ops-reports.xml` |
| `manifest/ops-dashboards.xml` | DIG Ops Admin dashboard folder (dashboards are quarantined) | `sf project deploy start --target-org deafingov --manifest manifest/ops-dashboards.xml` |
| `manifest/quarantine.xml` | Known-broken list views/reports/dashboards | Use only for diagnosis/retrieval | 

*Existing raw manifests live under `manifest/_archive/` (legacy names such as `dig_ops_dashboards.xml`). Use the new slices for day-to-day deploys.*

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
- A growing list of DIG Ops reports, dashboards, and the `Case.This_Week` list view break deployments because the folder ordering and filters collide with other metadata. Copies live in `fixtures/_incoming/broken/` and their entries appear in `manifest/quarantine.xml` so we can catalog and revisit them safely.
- Avoid retrieving or deploying the quarantine manifest during routine releases; pull it only when you need to inspect why a component keeps failing.

## Inventory & metadata guidance
- The canonical inventory is documented in `docs/architecture/metadata-inventory.md` with CORE vs OPTIONAL vs QUARANTINE categories.
- Keep DIG-owned metadata under `dig-src/main/default/` and avoid touching `force-app/` unless you are actively managing legacy artifacts.
- Use `manifest/dig.xml` (or a tight slice manifest) when a change spans multiple modules.

## Runbooks and deeper guidance
- Slice deploy playbook: `docs/runbooks/deploy-slices.md` (plus the other runbooks under `docs/runbooks/ops` and `docs/runbooks/lightning`).
- Use `docs/runbooks/ops/` runbooks for case, queue, email-to-case, and reporting setup that can’t live purely in source.

## Local housekeeping
- `tmp/` holds ephemeral files (ignored by Git), `fixtures/_incoming/` stages problematic metadata, and `scripts/` contains helper wrappers like `scripts/membership.sh`.
- Respect `.gitignore`, keep `.editorconfig` settings consistent, and do not introduce new package managers—only the existing npm tooling remains.
