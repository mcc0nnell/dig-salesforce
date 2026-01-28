# Geary comms-web

## What it does
`comms-web` is a deterministic, production-safe install sequence for the Comms stack. It enforces objects-case → objects-comms → Apex → perms → LWC order and applies production test-level rules automatically.

## Command
```bash
python tools/geary/geary.py install comms-web --target-org deafingov
```

## Sequence (deterministic)
1) `objects-case`
2) `objects-comms`
3) `apex-comms-core` (RunLocalTests on production unless stricter is specified)
4) `comms-perms`
5) `lwc-web`

## Guardrails
- Fails fast if a custom object has fields but is missing its `object-meta.xml`.
- Fails fast on required lookup fields missing delete behavior.
- Fails fast if permission sets reference Apex classes not present locally.
- Prevents `NoTestRun` on production orgs by switching to `RunLocalTests`.

## Notes
- Use `geary.py doctor` to check for missing object metadata, permset Apex references, and production test-level risks before deploying.
