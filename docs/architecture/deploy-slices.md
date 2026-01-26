# Deploying by slice

## Why slices exist
The repo slices metadata into narrow targets so DIG Ops can validate and deploy only what changed instead of shipping the entire org. Each slice focuses on a single domain (governance, membership, ops list views, etc.) and only references metadata that we know deploys cleanly, keeping the blast radius small.

## Deployment order
1. **Core objects first.** Deploy `Case`, `Membership__c`, and supporting custom objects/fields before UI layers that reference them. This keeps dependent metadata from failing on missing fields or record types.
2. **Slice-by-slice deploys.** Run the validation/deploy commands for each slice in the order you intend to release:
   - `sf project deploy start --target-org deafingov --manifest manifest/governance-mvp.xml`
   - `sf project deploy start --target-org deafingov --manifest manifest/membership-core.xml`
   - `sf project deploy start --target-org deafingov --manifest manifest/ops-listviews.xml`
   - `sf project deploy start --target-org deafingov --manifest manifest/ops-reports.xml`
   - `sf project deploy start --target-org deafingov --manifest manifest/ops-dashboards.xml`
3. **List views → Reports → Dashboards.** When working within the DIG Ops domain, deploy list views first, then reports, then dashboards. Reports/dashboards often rely on list views for filters/folder structure; keeping that order prevents dependencies from failing.

## How quarantine works
- Metadata that routinely fails validation (reports, dashboards, certain list views) is copied into `fixtures/_incoming/broken/` and added to `manifest/quarantine.xml`. The quarantine manifest exists only for inspection, not routine deploys.
- When validation fails on a component, copy it into the broken fixtures folder, add the entry to `manifest/quarantine.xml`, and remove it from your working slice manifest. Retry `make dig-validate` until the core slice is green.
- Use quarantine manifests/fixtures to document why a component is out of rotation rather than deleting it. Reintroduce quarantined metadata only after fixing the underlying issue.
