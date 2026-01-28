# Comms Web Deploy Steps (Copy/Paste)

## Final working sequence (exact commands)
```bash
python tools/geary/geary.py install comms-schema --target-org deafingov
python tools/geary/geary.py install comms-apex   --target-org deafingov --test-level RunLocalTests
python tools/geary/geary.py install comms-perms  --target-org deafingov
python tools/geary/geary.py install lwc-web      --target-org deafingov
```

## Verification

### Expected step output (high level)
- Step 1/4: schema deploy succeeds (objects + fields + Case fields present).
- Step 2/4: apex deploy succeeds with `RunLocalTests` (no missing object errors).
- Step 3/4: permsets deploy succeeds (no missing apexClass refs).
- Step 4/4: LWC deploy succeeds (no “Unable to find Apex action class…” errors).

### CLI checks
Run local tests and confirm org-wide coverage >= 75%:
```bash
sf apex test run --target-org deafingov --test-level RunLocalTests --code-coverage --result-format human --wait 60
```
Good looks like:
- Test summary: Passed
- Org Wide Coverage: >= 75%

Optional targeted check (if you need to confirm trigger coverage):
```bash
sf apex test run --target-org deafingov --tests CoverageBumpTests --code-coverage --result-format human --wait 60
```
Good looks like:
- MembershipTrigger shows 100% coverage

## Debugging quick map (if something fails)
- Missing Apex action in LWC → deploy Apex first; confirm `CommsService` exists in Setup → Apex Classes.
- Invalid type for Comms objects → deploy schema first; confirm object-meta.xml exists.
- Required lookup missing delete behavior → fix `deleteConstraint` (Restrict/Cascade) before deploying fields.
- Permset missing Apex classes → deploy Apex before perms.
- Production org `NoTestRun` error → use `RunLocalTests`.
- Coverage < 75% → add or extend tests and rerun.
