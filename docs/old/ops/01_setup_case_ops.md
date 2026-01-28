# DIG Ops Admin - Case Ops Setup

## Purpose
Establish Case as the Ops Ticket with DIG Ops record types and fields, then align the UI to enforce the operating model.

## Deploy metadata (record types + fields)
1) Deploy Case fields:
   - `sf project deploy start --target-org deafingov --manifest manifest/dig_ops_case_fields.xml`
2) Deploy Case record types:
   - `sf project deploy start --target-org deafingov --manifest manifest/dig_ops_case_recordtypes.xml`

## UI steps (Setup)
1) Setup → Object Manager → Case → Record Types
   - Confirm these record types exist:
     - Membership Ops
     - Events Ops
     - Communications Ops
     - Fundraising Ops
     - Governance Ops
     - IT/Website Ops
2) Setup → Object Manager → Case → Fields & Relationships
   - Confirm custom fields are present (Due Date, Category, Ops Status, Ops Priority, Next Action, etc.).
3) Setup → Object Manager → Case → Page Layouts
   - Create or update a minimal “DIG Ops Case” layout.
   - Add the custom fields in a single “Ops” section:
     - Due Date, Category, Ops Status, Ops Priority
     - Next Action, Definition of Done
     - Blocked Reason, Impact, Effort
     - Requester, Requester Email, Related Record URL
   - Mark Due Date and Next Action as required on the layout.
4) Setup → Object Manager → Case → Record Type Assignments
   - Assign the “DIG Ops Case” layout to all DIG Ops record types.

## Permissioning (avoid Profiles)
1) Create a Permission Set (e.g., `DIG_Ops_Admin`) or update an existing DIG Ops permission set.
2) Grant access to:
   - Case object + all new fields
   - Record Types listed above
   - Ops Change Log object (if using)

## Lightning App (UI)
1) Setup → App Manager → New Lightning App
   - Name: **DIG Ops Admin**
   - Navigation items (suggested): Cases, Ops Change Logs, Reports, Dashboards, Contacts
2) Assign the app to the DIG Ops users/permission set.

## Notes
- Ops Status/Priority are custom fields (`Ops_Status__c`, `Ops_Priority__c`) to avoid altering standard values.
- Next Action is a Text(255) field so it can be shown in list views.
