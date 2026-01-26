# Runbook: FlexiPage + Lightning App (dig-sf)

## Purpose
Create a minimal Lightning app (CustomApplication) with tabs and FlexiPages in DIG's SFDX repo, using `dig-src/` as the source of truth and a tight manifest for deploy.

## Scope
- Target org alias: `deafingov`
- Source root: `dig-src/main/default/`
- Keep layouts/profiles out unless explicitly requested

## Prereqs
- You are in the repo root
- Org alias `deafingov` is authenticated

## Conventions
- Put all new metadata under `dig-src/`
- Use a dedicated manifest under `manifest/`
- Validate with `make dig-validate` before deploy
- Deploy with the manifest (no broad source deploys)

## Files and Folders
- FlexiPages: `dig-src/main/default/flexipages/`
- Lightning app: `dig-src/main/default/applications/`
- Tabs: `dig-src/main/default/tabs/`
- Objects/fields: `dig-src/main/default/objects/`
- Permission sets: `dig-src/main/default/permissionsets/`
- Manifest: `manifest/<your-package>.xml`

## Step-by-step

### 1) Decide the metadata slice
Write down:
- Objects needed (if new)
- Tabs needed (custom object tabs or standard tabs)
- FlexiPages (home and record pages)
- CustomApplication
- Permission sets (if required)

### 2) Create or update objects and fields
Create object folder and field files under `dig-src/main/default/objects/<Object__c>/fields/`.

### 3) Create custom tabs
For custom objects, create tab files under `dig-src/main/default/tabs/`.

Example for a custom object tab:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomTab xmlns="http://soap.sforce.com/2006/04/metadata">
    <customObject>true</customObject>
    <motif>Custom63: Document</motif>
</CustomTab>
```
Notes:
- Do not use `<sobjectName>` or `<object>` for custom object tabs.
- `mobileReady` is not valid in v65.0 and should be omitted.

### 4) Create a Lightning app (CustomApplication)
Create a file under `dig-src/main/default/applications/` with tabs and a home override.

Example skeleton:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomApplication xmlns="http://soap.sforce.com/2006/04/metadata">
    <actionOverrides>
        <actionName>Tab</actionName>
        <comment>Action override created by Lightning App Builder during activation.</comment>
        <content>Your_App_Home</content>
        <formFactor>Large</formFactor>
        <skipRecordTypeSelect>false</skipRecordTypeSelect>
        <type>Flexipage</type>
        <pageOrSobjectType>standard-home</pageOrSobjectType>
    </actionOverrides>
    <description>Short app description.</description>
    <formFactors>Small</formFactors>
    <formFactors>Large</formFactors>
    <label>Your App Label</label>
    <navType>Standard</navType>
    <setupExperience>all</setupExperience>
    <tabs>standard-home</tabs>
    <tabs>CustomObject__c</tabs>
    <tabs>standard-report</tabs>
    <tabs>standard-Dashboard</tabs>
    <uiType>Lightning</uiType>
</CustomApplication>
```

### 5) Create FlexiPages
Create these under `dig-src/main/default/flexipages/`:
- App home page (type `HomePage`)
- Record pages (type `RecordPage`)

#### Home page
Keep it minimal, usually a single `flexipage:richText` in the main region.

#### Record pages
Use the same structure as the known-good `Membership_Record_Page` from the org:
- `force:highlightsPanel` in header
- `force:detailPanel` in detail tab
- `force:relatedListContainer` in related tab
- `flexipage:tabset` with detail + related tabs
- `parentFlexiPage` and `template` set to `flexipage:recordHomeTemplateDesktop`

Tip: If unsure, retrieve `FlexiPage:Membership_Record_Page` and reuse the structure.

### 6) Permission sets (if needed)
Create permission sets with object-level permissions only (scaffolding), under
`dig-src/main/default/permissionsets/`.

### 7) Create a dedicated manifest
Create `manifest/<your-package>.xml` with only the metadata you are deploying.

Example:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
  <types>
    <members>Your_Object__c</members>
    <name>CustomObject</name>
  </types>
  <types>
    <members>Your_Object__c</members>
    <name>CustomTab</name>
  </types>
  <types>
    <members>Your_App</members>
    <name>CustomApplication</name>
  </types>
  <types>
    <members>Your_App_Home</members>
    <members>Your_Object_Record_Page</members>
    <name>FlexiPage</name>
  </types>
  <types>
    <members>Your_Permission_Set</members>
    <name>PermissionSet</name>
  </types>
  <version>65.0</version>
</Package>
```

## Validate and Deploy
Always validate before deploy:
```bash
make dig-validate
sf project deploy validate --target-org deafingov --manifest manifest/<your-package>.xml
```
Deploy after successful validation:
```bash
sf project deploy start --target-org deafingov --manifest manifest/<your-package>.xml
```

## Verify
- Open the org and confirm the app shows in the App Launcher:
```bash
sf org open --target-org deafingov
```
- Optionally confirm in metadata:
```bash
sf org list metadata --target-org deafingov --metadata-type CustomApplication
```

## Troubleshooting
- FlexiPage errors about `recordDetail`: use `force:detailPanel` + tabset structure (see Membership Record Page).
- CustomTab errors about invalid fields: use `<customObject>true</customObject>` and omit `mobileReady`.
- Missing dependencies: add only the minimal required metadata to `dig-src/` and your manifest.
- Permission issues (layouts/profiles): remove them and re-run validation.

## Cleanup
If you retrieve a FlexiPage for reference into a temp folder, remove it before commit (e.g., `tmp-flexipage/`).
