# DIG Ops Catalog Compiler + Lint

This catalog tooling compiles DIG Ops slice examples into a normalized catalog and enforces boundedness and hygiene checks.

## Run locally

Compile + report:

```bash
python scripts/catalog_compile.py
```

Lint gate (compile + hard checks):

```bash
bash scripts/catalog_lint.sh
```

## Outputs

- `catalog/build/catalog.yml`: normalized catalog entries (stable ordering)
- `catalog/build/catalog_report.md`: lint findings + summary
- `docs/catalog/index.md`: generated slice index (stable ordering)

## Lint checks

- Schema validation against `catalog/schema/slice.schema.json`
- File existence for referenced manifests and docs
- Mermaid boundedness: `mermaid-intake` must not be included by `comms-web` or `comms-web-full`
- X Geary Key allowlist: only allowed files may reference the header
- Secret hygiene: no committed secret values (detects GEARY_KEY env var assignments or X Geary Key header values)

## Manifest references

Example YAML must reference manifest files that are committed to the repo. The lint gate checks that paths exist on disk in CI, and `manifest/slice-*.xml` files are ignored by git. Prefer tracked manifests like `manifest/*-package.xml`.

## Troubleshooting

- If you see schema errors, align the example YAML with `catalog/schema/slice.schema.json` or remove fields not allowed by the schema.
- If file checks fail, ensure referenced paths exist under `manifest/` or `docs/` and are tracked by git (not ignored).
- If boundedness fails, update `geary/slices.yml` so `comms-web` and `comms-web-full` do not include `mermaid-intake` (directly or via aliases).
- If allowlist fails, move X Geary Key usage into the allowed files or update the allowlist in `scripts/catalog_compile.py`.

## CI

The GitHub Action runs `scripts/catalog_lint.sh` on PRs and `main`. The job fails if any lint gate fails.
