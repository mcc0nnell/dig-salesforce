# DIG Ops Admin - Reports + Dashboard Setup

## Deploy report and dashboard metadata
1) Deploy reports:
   - `sf project deploy start --target-org deafingov --manifest manifest/dig_ops_reports.xml`
2) Deploy dashboard:
   - `sf project deploy start --target-org deafingov --manifest manifest/dig_ops_dashboards.xml`

## Verify in UI
1) App Launcher → Reports
   - Open the **DIG Ops Admin** report folder.
   - Confirm these reports exist:
     - Open by Status
     - Overdue
     - Blocked
     - Waiting on Requester
     - Closed This Week
     - Work by Category
     - Change Log By Month
     - Change Log Recent
2) App Launcher → Dashboards
   - Open **DIG Ops Admin - Cockpit**.
   - Confirm all tiles render.

## Adjustments (if needed)
- If any report columns/filters render incorrectly, open the report in the builder, adjust fields, and save.
- After UI changes, retrieve the report metadata back into the repo:
  - `sf project retrieve start --target-org deafingov --manifest manifest/dig_ops_reports.xml`

## Dashboard running user
- Keep `LoggedInUser` for visibility, or set a specific running user if required by your security model.
