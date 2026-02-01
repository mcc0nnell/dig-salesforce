# Email Comms Runner (DIG Ops Catalog)

## What it is
A bounded slice that documents the email comms runner surface for scheduled and on-demand sends.

## What it provides
- Email comms runner documentation anchor
- Expectations for operators running comms workflows

## What it depends on (and how to verify)
- No hard metadata dependencies declared in the catalog
- Verify by ensuring the doc exists and catalog lint passes:
  - `docs/ui/email-comms-runner.md`
  - `bash scripts/catalog_lint.sh`

## How to run / validate (commands)
```bash
bash scripts/catalog_lint.sh
python tools/geary/geary.py update --root .
```

If you are deploying email comms metadata, validate first and use a tracked manifest:
```bash
make dig-validate
sf project deploy start --target-org deafingov --manifest manifest/email-comms.xml
```

## Failure modes + troubleshooting
- **Catalog lint fails**: ensure the slice YAML points to `docs/ui/email-comms-runner.md`.
- **Deploy errors**: confirm the manifest exists and avoid large layout/profile pulls.
- **Operator confusion**: update this doc to reflect the current comms runbook.
