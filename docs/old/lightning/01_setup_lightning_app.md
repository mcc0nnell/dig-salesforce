# DIG Ops Admin - Lightning App Setup

## Goal
Create the **DIG Ops Admin** Lightning App with the required navigation order, then set the App Home to feature the cockpit dashboard.

## Metadata (if deploying)
- App definition: `dig-src/main/default/applications/DIG_Ops_Admin.app-meta.xml`
- Ops Change Log tab: `dig-src/main/default/tabs/Ops_Change_Log__c.tab-meta.xml`

Deploy:
```bash
sf project deploy start --target-org deafingov --metadata CustomApplication:DIG_Ops_Admin
sf project deploy start --target-org deafingov --metadata CustomTab:Ops_Change_Log__c
# or
sf project deploy start --target-org deafingov --manifest manifest/dig_ops_lightning_app.xml
```

## UI steps (exact flow)
1) Setup → App Manager → New Lightning App
2) App Name: **DIG Ops Admin**
3) App Options:
   - Navigation Style: Standard
   - App Branding: (optional)
4) Navigation Items (in this exact order):
   - Home
   - Cases
   - Dashboards
   - Reports
   - Contacts
   - Campaigns
   - Summit Events objects (only if Summit package is installed)
   - Ops Change Log
   - Files (optional)
5) Assign to Profiles:
   - System Administrator
   - DIG Ops permission set users (if you’ve created a `DIG_Ops_Admin` permission set)
6) Finish and Save.

## App Home: Pin the cockpit dashboard
1) App Manager → **DIG Ops Admin** → Edit
2) Click **App Options** → App Home Page
3) Create or edit the App Home page in Lightning App Builder:
   - Add a Dashboard component
   - Select **DIG Ops Admin - Cockpit**
   - Save and Activate for this app
4) Open the app and confirm the dashboard renders on the Home tab.

## Notes
- Deploy `manifest/dig_ops_change_log.xml` before the CustomTab if this is a fresh org.
- If Summit objects exist, insert them after Campaigns to keep the lane order consistent.
- If the dashboard component is hidden due to permissions, confirm Report/Dashboard folder access.
