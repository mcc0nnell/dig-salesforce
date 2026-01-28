# Comms Stack Deployment Runbook

## Overview
This runbook documents the end-to-end Comms stack deployment (schema, Apex, perms, LWC) including failures, root causes, fixes, and the final successful sequence. It is written to be production-safe and reproducible.

## What we were trying to install
- Comms custom objects and fields (`Comms_Message__c`, `Comms_Preference__c`) and Case custom fields referenced by Comms tests.
- Comms Apex classes and triggers (Comms* + DIG_TA_* + DigCaseAction_* + DigCaseTrigger).
- Comms permission sets (notably `DIG_Comms_Admin`).
- Comms LWC bundle(s), including `commsPanel`.

## Initial failure symptoms (exact key error messages)
- LWC deploy failed: “Unable to find Apex action class referenced as ‘CommsService’.”
- Apex deploy failed due to missing schema:
  - Invalid type errors for `Comms_Message__c` and `Comms_Preference__c`.
  - Missing Case custom fields referenced by tests (e.g., `DIG_Topic__c`) until deployed.
- Object metadata missing:
  - `Comms_Message__c.object-meta.xml` and `Comms_Preference__c.object-meta.xml` absent (fields existed but object metadata required).
- Lookup integrity error on `Comms_Preference__c.Contact__c`:
  - “must specify either cascade delete or restrict delete for required lookup foreign key”.
- Permission set deployment failed:
  - `DIG_Comms_Admin` referenced `CommsService` / `CommsSendQueueable` before they existed.
- Production org constraint:
  - “testLevel of NoTestRun cannot be used in production organizations”.
- Coverage gating:
  - Average coverage was 74% (needs 75%).
  - `DigCaseTrigger` had 0% coverage initially; required a dedicated test.

## Root causes (bullet list)
- Schema prerequisites (Comms objects and Case fields) were not deployed before Apex tests that reference them.
- Object metadata files for `Comms_Message__c` and `Comms_Preference__c` were missing even though field metadata existed.
- A required lookup field on `Comms_Preference__c.Contact__c` had invalid delete behavior.
- Permission sets referenced Apex classes that were not yet deployed.
- Production orgs require `RunLocalTests`; `NoTestRun` is invalid.
- Apex coverage was below 75% due to missing tests (notably `DigCaseTrigger`).

## Fixes applied (bullet list)
- Deployed Comms schema first (objects + fields, plus required Case fields).
- Added missing `object-meta.xml` files for `Comms_Message__c` and `Comms_Preference__c`.
- Corrected lookup field delete behavior on `Comms_Preference__c.Contact__c`.
- Removed or deferred permset Apex class references until Apex was deployed.
- Ran Apex deploys in production with `--test-level RunLocalTests`.
- Added tests to raise coverage:
  - `DigCaseTriggerTests` (insert/update Case to fire `DigCaseTrigger`).
  - `DIG_TA_DispatcherTests` (missing locally at one point; created to match package.xml).
  - `CoverageBumpTests` to cover `MembershipTrigger` delete/undelete; raised `MembershipTrigger` to 100%.

## Final successful deploy sequence (copy/paste commands)
```bash
python tools/geary/geary.py install comms-schema --target-org deafingov
python tools/geary/geary.py install apex-comms-core --target-org deafingov --test-level RunLocalTests
python tools/geary/geary.py install comms-perms --target-org deafingov
python tools/geary/geary.py install lwc-web --target-org deafingov
```

Once Geary comms-web is fixed, use the single command:
```bash
python tools/geary/geary.py install comms-web --target-org deafingov
```

## Verification checklist (UI + CLI)
- Setup → Object Manager: `Comms_Message__c`, `Comms_Preference__c` exist.
- Setup → Apex Classes: `CommsService`, `CommsSendQueueable` exist.
- Permission Sets: `DIG_Comms_Admin` deploy present.
- LWC: `commsPanel` exists and loads (no missing apex action error).
- CLI: run local tests and confirm org-wide coverage >= 75%.

## Gotchas / production constraints
- Production orgs require `RunLocalTests`; `NoTestRun` is not allowed and will fail with the production-org constraint error.
- Deploy order matters: schema → Apex → perms → LWC.
- LWC depends on Apex actions; deploy Apex before LWC or expect missing action errors.
- Permission sets must not reference Apex classes until those classes exist in the org.

## Future improvements (what Geary should automate next)
- Enforce deploy ordering based on dependencies (schema before Apex, Apex before perms, perms before LWC).
- Detect missing `object-meta.xml` for custom objects when fields are present.
- Validate required lookup delete behavior in metadata before deploy.
- Auto-scan permsets for Apex class references not included in the target slice.
- Gate deployments on org-wide coverage threshold prior to running the deploy.
- Provide a “comms-stack” alias that chains the exact sequence with `RunLocalTests` in production.

## Final successful deploy evidence
- `apex-comms-core` succeeded with all tests passing (29/29).
- `comms-perms` succeeded.
- LWC deploy succeeded and created `commsPanel` and updated `digMembershipPanel`.
- Org-wide coverage is 88%.
- `sf apex test run --tests CoverageBumpTests` shows `MembershipTrigger` 100%.
