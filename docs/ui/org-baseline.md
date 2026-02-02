# Org Baseline (DIG Ops Catalog)

## What it is
A bounded, catalog-only slice that documents the minimum org baseline for DIG Ops deployments (guardrails, naming, and validation expectations).

## What it provides
- A single source of truth for baseline expectations
- Catalog entry used by tooling and reviews

## What it depends on (and how to verify)
- No hard metadata dependencies yet
- Verify by ensuring this doc exists and catalog lint passes:
  - `docs/ui/org-baseline.md`
  - `bash scripts/catalog_lint.sh`

## How to run / validate (commands)
```bash
bash scripts/catalog_lint.sh
python tools/geary/geary.py update --root .
```

## Failure modes + troubleshooting
- **Catalog lint fails**: confirm the docs path in the slice YAML matches this file.
- **Slice missing from catalog**: rerun the lint/compile and check `catalog/build/catalog.yml` ordering.
- **Slice missing from catalog**: rerun the lint/compile and check `build/catalog.yml` ordering.
- **Baseline expectations drift**: update this doc first, then re-run lint so the catalog reflects it.
