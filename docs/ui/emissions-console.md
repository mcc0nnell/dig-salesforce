# Emissions Console (DIG Ops Catalog)

## What it is
A bounded UI slice that describes the emissions console experience for visibility, review, and operational controls.

## What it provides
- Emissions console documentation anchor
- UI expectations for operators and reviewers

## What it depends on (and how to verify)
- No hard metadata dependencies declared in the catalog
- Verify by checking the doc and lint output:
  - `docs/ui/emissions-console.md`
  - `bash scripts/catalog_lint.sh`

## How to run / validate (commands)
```bash
bash scripts/catalog_lint.sh
python tools/geary/geary.py update --root .
```

## Failure modes + troubleshooting
- **Catalog lint fails**: ensure the slice YAML points to this doc path.
- **UI scope drift**: update this doc and re-run lint so the catalog stays aligned.
