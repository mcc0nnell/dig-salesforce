# Deploy slice manifests

Slice manifests keep deployments small and predictable. Instead of deploying the entire repo, deploy only the metadata you intend to change.

## Why slices exist
- Salesforce metadata often has hidden dependencies and ordering constraints.
- Small manifests are easier to validate (and easier to quarantine when something is broken).
- Operators can deploy just “governance” or just “membership” without bringing unrelated changes along.

## Core slice manifests
- `manifest/governance-mvp.xml`: Governance objects + UI + permission sets.
- `manifest/membership-core.xml`: Membership object + flows + permission sets.
- `manifest/quarantine.xml`: Known-cruft and “don’t ship by default” metadata.

## Recommended deployment order
1. **Core data model first**: custom objects, fields, record types.
2. **Automation next**: flows + flow definitions.
3. **Security next**: permission sets.
4. **UI last**: tabs, flexipages, apps.

If you are deploying Ops artifacts, keep the ordering stable:
- List views → reports → dashboards.

## How quarantine works
Quarantine is a safety valve:
- Keep problematic/experimental metadata tracked in git.
- Exclude it from normal validate/deploy (via `.forceignore` and by keeping it out of core slice manifests).
- Record any “this breaks deploy” artifacts under `fixtures/_incoming/broken/` (preserving relative paths) so we can revisit and fix later.

## Commands
Validate before any deploy:
```bash
make dig-validate
```

Deploy slices:
```bash
make deploy-governance
make deploy-membership
```

Deploy directly with `sf` if needed:
```bash
sf project deploy start --target-org deafingov --manifest manifest/governance-mvp.xml
sf project deploy start --target-org deafingov --manifest manifest/membership-core.xml
```

