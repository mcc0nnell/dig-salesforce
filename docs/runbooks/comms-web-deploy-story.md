# Comms Web Deploy Story (Narrative + Decision Log)

## Overview
This is a concise, bureaucrat-proof narrative of the comms stack deploy journey from first failure to final success. It captures symptoms, root causes, decisions, and the final order that worked.

## Initial failure symptoms (exact messages)
- LWC deploy failed: “Unable to find Apex action class referenced as 'CommsService'”.
- Apex deploy failed due to missing CustomObject object-meta.xml for `Comms_Message__c` and `Comms_Preference__c`.
- Field deploy failed due to required lookup missing delete behavior (cascade vs restrict).
- Permission set deploy failed due to apexClass refs missing (`CommsService` / `CommsSendQueueable`).
- Production org constraint: `NoTestRun` not allowed.
- Apex coverage gate: org-wide must be >= 75%.

## Root cause summary
- LWC depended on Apex actions that were not yet deployed.
- Apex tests referenced objects/fields before schema existed.
- Required lookup fields must specify delete behavior (cascade/restrict).
- Permission sets referenced Apex classes that did not exist yet.
- Production deploys require tests; `NoTestRun` is invalid.
- Coverage was below 75% due to missing tests.

## Fixes applied (in order)
1) Create `Comms_Message__c.object-meta.xml` and `Comms_Preference__c.object-meta.xml`.
2) Fix required lookup delete constraint for `Comms_Preference__c.Contact__c` (must specify cascadeDelete or restrictDelete).
3) Deploy schema first (Case fields + comms objects).
4) Deploy Apex with production-safe test level (`RunLocalTests`).
5) Add missing tests for trigger coverage:
   - `DigCaseTriggerTests`
   - `DIG_TA_DispatcherTests`
   - `CoverageBumpTests` to hit `MembershipTrigger` delete/undelete paths and required fields
6) Re-run tests until coverage gate cleared.
7) Deploy permission sets after Apex exists.
8) Deploy LWC last.

## Decision log (why this order)
- Schema before Apex: tests and code reference objects/fields; missing objects cause invalid type failures.
- Apex before perms: permsets include apexClass access; missing classes break permset deploy.
- LWC last: LWC calls Apex actions; missing actions fail at deploy or runtime.
- Production-safe tests: `RunLocalTests` is required in production; use stricter levels only by explicit request.

## Final success conditions
- Objects, fields, and Case custom fields deployed cleanly.
- Apex deployed with `RunLocalTests` in production.
- Coverage gate cleared (>= 75%).
- Permsets deployed without missing Apex class refs.
- LWC deployed with Apex actions present.

## How to repeat (see steps)
For copy/paste commands and verification, see `docs/runbooks/comms-web-deploy-steps.md`.
