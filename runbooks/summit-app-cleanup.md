# Summit App Cleanup (DIG Ops)

Purpose: replace daily use of the managed “Summit Events” Lightning app with a DIG-owned app shell that surfaces Summit tabs while keeping DIG ops workflows consistent and reproducible.

## UI setup (App Manager)

1) Setup → App Manager → New Lightning App
2) App Name: **DIG Ops** (or **Summit** if that is the preferred label)
3) App Options
   - Branding is optional; keep defaults if unsure.
4) Navigation Items (recommended)
   - Summit objects: Appointment Types / Event Instances / Registrations / Payments (and other Summit objects that exist)
   - Contacts
   - Campaigns
   - Reports
   - Dashboards
   - Cases
5) Explicitly omit
   - Leads
   - Opportunities
   - Forecasts
   - Products
   - Quotes
   - Orders

## Home page setup (FlexiPage)

1) From the new app, open the App Builder and create/edit **DIG Ops Home**
2) Set as **App Default** for the new app
3) Set as **Org Default** (optional but recommended)

## Retrieve the metadata after UI changes

Replace the API names if they differ in your org. Current prod uses `standard__LightningSales` for the DIG Ops app and `DIG_Ops_Home1` for the Home page.

```bash
sf project retrieve start --metadata "CustomApplication:standard__LightningSales"
sf project retrieve start --metadata "FlexiPage:DIG_Ops_Home1"
```

## Deploy using the manifest slice

```bash
sf project deploy start --manifest manifest/summit-ui.xml --target-org deafingov
```

## Notes

- Do not try to customize the managed **Summit Events** app.
- Summit Doctrine: all events (coffee hours → NTC) are run in Summit, but inside a DIG-owned app shell.
