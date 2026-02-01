# Membership MVP (DIG Ops Catalog)

## What it is
A bounded slice capturing the minimal membership domain surface needed for core status and reporting.

## What it provides
- Membership MVP catalog entry
- Reference point for membership-related slices

## What it depends on (and how to verify)
- No hard metadata dependencies declared in the catalog
- Verify by ensuring this doc exists and catalog lint passes:
  - `docs/ui/membership-mvp.md`
  - `bash scripts/catalog_lint.sh`

## How to run / validate (commands)
```bash
bash scripts/catalog_lint.sh
python tools/geary/geary.py update --root .
```

If you are deploying membership metadata, validate first and use the tracked manifest:
```bash
make dig-validate
sf project deploy start --target-org deafingov --manifest manifest/membership-mvp-package.xml
```

## Failure modes + troubleshooting
- **Catalog lint fails**: confirm the slice YAML references `docs/ui/membership-mvp.md`.
- **Deploy fails**: ensure you ran `make dig-validate` first and the manifest path is correct.
- **Missing dependencies**: add the minimal required metadata instead of broad pulls.
