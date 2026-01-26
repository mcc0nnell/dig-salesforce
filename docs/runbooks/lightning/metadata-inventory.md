# Metadata inventory

This inventory captures the DIG metadata under `dig-src/main/default/` and assigns each artifact to CORE, OPTIONAL, or QUARANTINE slices.

## CORE
These items are actively deployed in production slices and should stay synced with the org.
- **Custom objects**: `Case`, `Membership__c`, `Ops_Change_Log__c`, `In_App_Checklist_Settings__c`, `Motion__c`, `Vote__c`.
- **Case fields**: all `Category__c`, `Ops_Status__c`, `Ops_Priority__c`, `Next_Action__c`, `Blocked_Reason__c`, `Due_Date__c`, `Effort__c`, `Impact__c`, `Requester__c`, `Requester_Email__c`, `Definition_of_Done__c`, `Related_Record_URL__c`.
- **Membership fields**: `AutoRenew__c`, `Contact__c`, `EndDate__c`, `Renewal_Due_Next_7_Days__c`, `Renewal_Due_Next_30_Days__c`, `StartDate__c`, `Status__c`.
- **Flows/definitions**: `DIG_Membership_OnCreate`, `DIG_Membership_OnUpdate_Status` (stable membership automations).
- **Permission sets**: `DIG_Board_Gov`, `DIG_Gov_Admin`, `DIG_Membership_Admin`, `DIG_Membership_Staff`, `DIG_Member_Gov`.
- **Queues**: `DIG_Ops_*` per discipline plus `DIG_Ops_Triage`.
- **Governance UI**: `DIG_Governance` app, `DIG_Governance_Home`, `Motion_Record_Page`, `Vote_Record_Page`, associated tabs.
- **Membership metadata**: the object, flows, and permission sets are deployed via `manifest/membership-core.xml`.
- **Governance metadata**: motion/vote objects, tabs, flexipages, and permission sets deploy via `manifest/governance-mvp.xml`.

## OPTIONAL
These artifacts exist for reference or future work; they are not part of the core validation/deploy flows yet.
- **Lightning app**: `DIG_Ops_Admin.app-meta.xml` and the `DIG_Ops_Admin` flexipage hierarchy (app nav that lives in Setup).
- **Flexipages**: `DIG_Ops_Home1`, `DIG_Governance_Home`, `Motion_Record_Page`, `Vote_Record_Page` (governance uses them, but they are only deployed with the governance slice when necessary).
- **Tabs**: `Motion__c`, `Vote__c`, `Ops_Change_Log__c` tabs—they deploy alongside the apps when needed.
- **Standard application** metadata: `standard__LightningSales.app` is captured for documentation but does not ship with every release.

## QUARANTINE & CRUFT
We quarantine metadata that consistently breaks validation/deploy, keeps us in sync via fixtures, or is not yet rescuable.
- **Reports**: the entire `DIG_Ops_Admin` folder lives in `manifest/quarantine.xml` (Broken copies in `fixtures/_incoming/broken/reports/DIG_Ops_Admin/`).
- **Dashboards**: both `DIG_Ops_Admin` dashboards are quarantined (`manifest/quarantine.xml` + `fixtures/_incoming/broken/dashboards/DIG_Ops_Admin/`).
- **List views**: `Case.This_Week` is quarantined because it hits ordering issues (copied to `fixtures/_incoming/broken/objects/Case/listViews/`).
- **Legacy manifests**: the older `manifest/dig_ops_*` slices moved to `manifest/_archive/` so we can consult them without cluttering production slices.
- **Other cruft**: any metadata that fails `make dig-validate` gets copied to `fixtures/_incoming/broken/` and listed in `manifest/quarantine.xml` rather than forcing the core slice to fail.
- **Record types**: the DIG Ops Case record types required missing business processes, so they now live under `fixtures/_incoming/broken/objects/Case/recordTypes/` and `manifest/quarantine.xml`.
