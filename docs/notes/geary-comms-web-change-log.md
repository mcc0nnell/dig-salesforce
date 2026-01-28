# Geary comms-web: deterministic, production-safe install

## What changed
- `comms-web` now runs a deterministic sequence: objects-case → objects-comms → apex-comms-core → comms-perms → lwc-web.
- Production test-level handling enforces `RunLocalTests` and blocks `NoTestRun` with explicit messaging.
- Coverage gate failures print an actionable hint pointing to `CoverageBumpTests` and org-wide >= 75%.
- Documentation updated to match the new comms-web ordering.

## Why it changed
- Prior deploys failed when schema, Apex, perms, and LWC were not ordered deterministically.
- Production orgs require test execution; `NoTestRun` is invalid.
- Coverage gate failures needed an immediate, actionable remediation path.

## New comms-web order (exact sequence)
objects-case → objects-comms → apex-comms-core → comms-perms → lwc-web

## Production test-level behavior (exact rules + messages)
- Rule: `NoTestRun` is not allowed on production orgs; default to `RunLocalTests` when no test level is provided.
- Message when overriding:
  - “NoTestRun is not allowed on production orgs; switching to RunLocalTests”
  - “Production org detected; defaulting to RunLocalTests”

## Coverage gate hinting (what triggers it + the exact suggested command)
- Trigger: deploy failure output contains a test coverage gate message.
- Hint shown:
  - “Coverage gate failed. Hint: run `sf apex test run --target-org deafingov --tests CoverageBumpTests --code-coverage --result-format human --wait 60` and ensure org-wide coverage >= 75%.”

## Verification performed (only the commands we ran)
- `python tools/geary/geary.py update --root .`
- `python tools/geary/geary.py list --root .`
- `python tools/geary/geary.py doctor --root .`

## Explicitly NOT performed
- `python tools/geary/geary.py install comms-web --target-org deafingov`

## Files edited
- `tools/geary/geary.py`
- `docs/geary/comms-web.md`
- `docs/runbooks/comms-stack-deploy.md`
