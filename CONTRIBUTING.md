# Contributing to deafingov Salesforce

## Validate first
Always run the repo-level validation target before shipping metadata.
```bash
make dig-validate
```
If the validation target fails, move the troublemaker into `manifest/quarantine.xml` (and `fixtures/_incoming/broken/`) before retrying.

## Deployment pattern
1. Validate with `make dig-validate`.
2. Deploy core slices only once validation is stable (e.g., governance → membership → ops list views).
3. Use the specific slice manifest when deploying: `manifest/governance-mvp.xml`, `manifest/membership-core.xml`, `manifest/ops-listviews.xml`, etc.
4. If you must deploy dashboards/reports or other UI artifacts that currently fail, stage them via `manifest/quarantine.xml` and fix them in a future pass.

## Adding a manifest slice
1. Add the slice XML under `manifest/` with the new slice name and the metadata members you need.
2. Update `docs/architecture/metadata-inventory.md` to document where the slice fits (CORE/OPTIONAL/QUARANTINE).
3. Describe the slice in `README.md` and `docs/runbooks/deploy-slices.md` so operators know how to use it.
4. Run `make dig-validate` before committing.
