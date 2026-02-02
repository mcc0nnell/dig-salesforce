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

## How to run / validate (commands)
```bash
bash scripts/catalog_lint.sh
python tools/geary/geary.py update --root .
```

## Failure modes + troubleshooting
- **No events**: user lacks Create/Read on `DIG_Emission__e` or subscription dropped.
- **Anomalies**: check PrevHash rules and seq order in the publisher.
- **Catalog lint fails**: ensure the slice YAML points to this doc path.
