# Metadata inventory

This inventory captures the DIG metadata under `dig-src/main/default/` and assigns each artifact to CORE, OPTIONAL, or QUARANTINE slices.

## CORE
These items are actively deployed in production slices and should stay synced with the org.
- **Custom objects**: `Membership__c`, `Motion__c`, `Vote__c`.
- **Membership flows/definitions**: `DIG_Membership_OnCreate`, `DIG_Membership_OnUpdate_Status`.
- **Permission sets**: `DIG_Board_Gov`, `DIG_Gov_Admin`, `DIG_Membership_Admin`, `DIG_Membership_Staff`, `DIG_Member_Gov`.
- **Governance UI**: `DIG_Governance` app, `DIG_Governance_Home`, `Motion_Record_Page`, `Vote_Record_Page`, and the `Motion__c`/`Vote__c` tabs.
- **Slice manifests**: `manifest/governance-mvp.xml`, `manifest/membership-core.xml`.

## OPTIONAL
These artifacts exist for reference or future work; they are not part of the core validation/deploy flows yet.
- **None currently**. Prefer moving “maybe later” metadata into quarantine so `make dig-validate` stays green and deploys remain predictable.

## QUARANTINE & CRUFT
We quarantine metadata that consistently breaks validation/deploy, keeps us in sync via fixtures, or is not yet rescuable.
- **Experimental UI**: `standard__LightningSales` application metadata and `DIG_Ops_Home1` flexipage live in `manifest/quarantine.xml` and are excluded from normal validate/deploy via `.forceignore`.
- **Process rule**: any metadata that fails `make dig-validate` should be copied into `fixtures/_incoming/broken/` (preserving relative paths) and listed in `manifest/quarantine.xml` rather than forcing the core slice to fail.
