# Emissions Console (DIG Ops Catalog)

## What it is
A bounded UI slice for the DIG Emissions console, backed by the Platform Event spine.

## What it provides
- LWC `digEmissionsConsole`
- Subscription to `/event/DIG_Emission__e`
- Operator view of the last 500 emissions with filters and detail panel

## What it depends on (and how to verify)
- `DIG_Emission__e` Platform Event
- `DIG_Emission__c` durable sink
- `DIG_Emissions_Perms` permission set

Verify by checking:
- `docs/dig/emissions.md`
- `dig-src/main/default/lwc/digEmissionsConsole/`
- `dig-src/main/default/objects/DIG_Emission__e/`
- `dig-src/main/default/objects/DIG_Emission__c/`
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
- **No events**: user lacks Create/Read on `DIG_Emission__e` or subscription dropped.
- **Anomalies**: check PrevHash rules and seq order in the publisher.
- **Catalog lint fails**: ensure the slice YAML points to this doc path.
- **Catalog lint fails**: ensure the slice YAML points to this doc path.
- **UI scope drift**: update this doc and re-run lint so the catalog stays aligned.
