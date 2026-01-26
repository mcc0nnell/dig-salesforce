# AI Agent Instructions (DIG Salesforce DX)

## Do / Don't

DO
- Do run `make dig-validate` before any deploy.
- Do prefer retrieval via a tight manifest like `manifest/dig.xml`.
- Do deploy using the target manifest: `sf project deploy start --target-org deafingov --manifest manifest/membership-mvp-package.xml`.
- Do treat `deafingov` as the default target org alias.
- Do work primarily from `dig-src/`.

DON'T
- Don't retrieve or deploy large Layout/Profile metadata unless explicitly requested.
- Don't print or paste access tokens or sensitive auth fields.
- Don't run destructive commands (e.g., `rm -rf`, `git reset --hard`) without explicit instruction.

## Quickstart

Use these exact commands:

```bash
sf org display --target-org deafingov
make dig-validate
sf project deploy start --target-org deafingov --manifest manifest/membership-mvp-package.xml
make dig-retrieve
make org
```

## Project structure

- `dig-src/main/default/` contains DIG-owned metadata (flows, permission sets, custom objects).
- `force-app/` is legacy/noisy and should be avoided unless explicitly requested.
- `manifest/dig.xml` defines the canonical DIG metadata slice for retrieval.

## Standard workflow

1) Retrieve the minimal metadata you need.
2) Edit metadata in `dig-src/`.
3) Validate deployment with `make dig-validate`.
4) Deploy with `sf project deploy start --target-org deafingov --manifest manifest/membership-mvp-package.xml`.

Git hygiene
- Use branches for changes.
- Keep commits small and scoped.
- Use meaningful commit messages.

PR notes must include
- `git status --porcelain` output.
- `sf project deploy start --target-org deafingov --manifest manifest/membership-mvp-package.xml --dry-run` results.

## Troubleshooting

Metadata list errors
- If `sf org list metadata` fails with a missing metadata-type error, re-run with explicit `--metadata-type` values that exist in the org. Do not assume all types are available.

Permission-gated metadata
- If permissions issues occur (especially layouts or profiles), narrow the manifest and avoid layouts. These areas are frequently permission-gated.

Missing dependencies
- If deploy fails due to missing dependencies, prefer adding the minimal required metadata to `dig-src/` and/or `manifest/dig.xml` rather than broad pulls.

## What to ask the human

- Are we working in the production DIG org or a scratch/dev org?
- Which DIG modules are in scope (Membership, Events, Fundraising, Comms)?
- Should layouts/profiles be managed in source control for this task?
