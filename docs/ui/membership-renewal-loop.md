# Membership Renewal Loop (DIG Ops Catalog)

## What it is
A bounded slice describing the membership renewal loop orchestration (follow-ups, reminders, and renewal tracking).

## What it provides
- Renewal loop catalog entry
- Contract for how renewal logic is layered on top of membership MVP

## What it depends on (and how to verify)
- Depends on `digops-21-membership-mvp`
- Verify by confirming both catalog entries exist and lint passes:
  - `docs/ui/membership-renewal-loop.md`
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
- **Catalog lint fails**: ensure the `depends_on` entry matches `digops-21-membership-mvp`.
- **Renewal logic missing**: confirm the membership MVP slice is installed first.
- **Deploy errors**: prefer adding minimal required metadata over broad pulls.
