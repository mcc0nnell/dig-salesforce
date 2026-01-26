# dig-sf

Salesforce DX (SFDX) project for Deaf in Government (DIG). This repo keeps DIG-owned metadata in a clean source root and avoids pulling noisy org metadata unless explicitly needed. It also documents the small but important UI-only configuration we’re choosing not to version in metadata.

## Quickstart

Prereqs
- Salesforce CLI (`sf`) installed
- Org alias `dig` authenticated

Verify org
```bash
sf org display --target-org dig
```

Common commands
```bash
make help
make whoami
make dig-retrieve
make dig-validate
make org

# Membership (combined slice)
sf project deploy start --target-org dig --manifest manifest/membership-all-package.xml
```

## What’s in-scope vs out-of-scope

**In-scope (versioned in git)**
- DIG-owned metadata under `dig-src/` (custom objects/fields, permission sets, flows *when stable*)
- Manifests under `manifest/` that define deployable “slices”
- Reports/Dashboards when we want versioned operational views

**Out-of-scope (documented here; configured in UI)**
- Lightning App navigation / pinned items / org home page tweaks
- List Views (unless we intentionally decide to version them later)
- Managed package metadata (we configure; we don’t own)

## Project structure

- `dig-src/` is the authoritative source root
  - `dig-src/main/default/flows/`
  - `dig-src/main/default/flowDefinitions/`
  - `dig-src/main/default/permissionsets/`
  - `dig-src/main/default/objects/`
  - `dig-src/main/default/reports/` (preferred for versioned ops views)
- `manifest/dig.xml` is the canonical DIG slice (broader; use intentionally)
- Membership manifests (tight scope)
  - `manifest/membership-mvp-package.xml` (initial MVP slice)
  - `manifest/membership-update-status-package.xml` (update-status flow only)
  - `manifest/membership-all-package.xml` (object + fields + both flows + permsets)
- `Makefile` provides standardized CLI targets
- `agents.md` contains AI agent instructions

## Project-local defaults

Set defaults for this repo (no global flags):
- Default org (direct): `sf config set target-org deafingov`
- Use alias as default: `sf config set target-org dig`
- Optional Dev Hub: `sf config set target-dev-hub deafingov`
- Verify: `sf config get target-org` and `sf config get target-dev-hub`

## Standard workflow

1) Retrieve only what you need
```bash
sf project retrieve start --target-org dig --manifest manifest/dig.xml
```

2) Edit metadata in `dig-src/`

3) Validate before any deploy
```bash
make dig-validate
```

4) Deploy
```bash
sf project deploy start --target-org dig --manifest manifest/dig.xml
```

## Data model decisions (current)

- **Contact is the spine.** We track people as Contacts whether or not they are currently paid members.
- Membership status is reflected via membership fields/records and reports (we can refine the exact schema later).
- Campaigns stand on their own; Summit Events can associate events with campaigns.

## Membership slice

Retrieve (combined)
```bash
sf project retrieve start --target-org dig --manifest manifest/membership-all-package.xml
```

Deploy (combined)
```bash
sf project deploy start --target-org dig --manifest manifest/membership-all-package.xml
```

Renewal fields
```bash
sf project retrieve start --target-org dig --manifest manifest/membership-renewal-fields-package.xml
```

## Wild Apricot import notes

We imported members from Wild Apricot into Salesforce (Contacts). Some records were skipped due to **duplicate emails**; those can be scrubbed and re-imported later.

Operational guidance:
- Treat Contacts as the canonical person record.
- Prefer importing into Contacts first, then linking/deriving membership status.
- Keep an eye on duplicates and decide on a dedupe rule (email-first is usually fine for MVP).

## UI configuration we’re not versioning (for now)

We currently treat the items below as **UI-only configuration** (not retrieved into `dig-src`). Document changes here so the setup is reproducible.

### Membership list views (UI)

Reproducible checklist (created in UI):
1) Active Members
   - Status = Active
2) Lapsed Members
   - Status = Lapsed
3) Renewals Due - Next 7 Days
   - Status = Active
   - Renewal Due Next 7 Days = True (field: `Renewal_Due_Next_7_Days__c`)
4) Renewals Due - Next 30 Days
   - Status = Active
   - Renewal Due Next 30 Days = True (field: `Renewal_Due_Next_30_Days__c`)

Note: if we need versioned ops views, prefer **Reports/Dashboards** (metadata) rather than List Views.


### Lightning apps / navigation

- The internal ops app is **DIG Ops** (renamed from the default Sales label).
- Summit Events navigation has some limitations (e.g., favorites support varies). If the navbar can’t be made perfect, we prioritize **clarity + discoverability** over pixel-perfect parity.

### Summit Events (DIG standard)

We run **all events** in DIG using Summit Events — from informal coffee hours to major conferences (e.g., **NTC**).

### Summit Events Doctrine

We standardize on Summit for every event so operations stay consistent, reporting stays centralized, and staff can rely on one system of record regardless of event size or format. Summit is managed-package infrastructure; our ownership is the DIG app shell and the way we present Summit to users.

Current posture:
- Summit is the **system of record for event operations** (event types, instances/occurrences, registration/payments).
- We treat Summit as a **managed package**: configure in UI, document choices here, and avoid pulling Summit-owned metadata into `dig-src`.

Operational conventions (keep it simple):
- Use **Appointment Types / Event Types** to represent the category of event (Coffee Hour, Webinar, Training, NTC, etc.).
- Use **Instances** to represent specific dates/times (occurrences) of an event type.
- When an event supports an outreach goal, tie it to a **Campaign** (Campaigns stand on their own; Summit events may associate).
- Use **Payments/Registration** only when needed; free events still live in Summit as types + instances.

Minimal smoke test (after any config changes):
1) Create/confirm an Appointment Type
2) Create an Instance for a future date/time
3) (Optional) Associate to a Campaign
4) Validate that ops users can find the records from **DIG Ops** navigation

Note: for stable, versioned operational views, prefer **Reports/Dashboards** rather than relying on managed-package list views or navbar behavior.

### Summit UI Slice

Retrieve the app + home page metadata after UI changes:
```bash
sf project retrieve start --metadata "CustomApplication:DIG_Ops"
sf project retrieve start --metadata "FlexiPage:DIG_Ops_Home"
```

Deploy with the minimal manifest slice:
```bash
sf project deploy start --manifest manifest/summit-ui.xml --target-org dig
```

## Guardrails

- Do not retrieve or deploy layouts/profiles unless explicitly requested (avoid profile/layout drift).
- Flows can be brittle as metadata; if deploy errors occur, prefer rebuilding in Flow Builder and then re-retrieving stable metadata.
- Do not paste access tokens or auth secrets into logs or commits.
- Keep commits small and focused.
- List views for Membership are treated as UI configuration; document changes in README. Prefer Reports for versioned artifacts.
- Document UI-only setup changes in this README so the org is reproducible even when metadata isn’t.
