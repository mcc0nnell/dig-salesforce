# Ops Envelope (DIG Ops Catalog)

## What it is
A bounded, catalog-only slice that defines the operational envelope for DIG Ops (policy, observability, and guardrail expectations).

## What it provides
- Shared operational envelope reference for other slices
- Documentation anchor for ops-wide constraints

## What it depends on (and how to verify)
- No hard metadata dependencies yet
- Verify by checking the doc and catalog entry exist:
  - `docs/ui/ops-envelope.md`
  - `bash scripts/catalog_lint.sh`

## How to run / validate (commands)
```bash
bash scripts/catalog_lint.sh
python tools/geary/geary.py update --root .
```

## Failure modes + troubleshooting
- **Catalog lint fails**: ensure the slice YAML points to `docs/ui/ops-envelope.md`.
- **Envelope out of date**: update this doc, then re-run lint to refresh the catalog.
