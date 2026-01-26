# dig-sf

DIG’s Salesforce repo. Built to be **reproducible**, **sliceable**, and **immune to metadata sprawl**.

The vibe:
- **Small blast radius.** Deploy slices, not the universe.
- **Noisy stuff stays out.** Profiles/layouts/managed package internals don’t get to ruin your diffs.
- **UI-only changes are real.** If we do it in Setup, we write it down here.

---

## Quickstart

### Prereqs
- Salesforce CLI (`sf`)
- Org alias authenticated: `deafingov`

### Sanity check
```bash
sf org display --target-org deafingov
```

### Common moves
```bash
make help
make whoami
make dig-retrieve
make dig-validate
make org

# Membership (combined slice)
sf project deploy start --target-org deafingov --manifest manifest/membership-all-package.xml
```

---

## Repo map

### Source of truth
Everything DIG-owned lives under:
- `dig-src/main/default/`
  - `objects/`
  - `permissionsets/`
  - `flows/`
  - `flowDefinitions/`
  - `reports/` (preferred “ops views” that *can* be versioned)

### Manifests (deployable slices)
- Canonical (bigger): `manifest/dig.xml`

Membership
- `manifest/membership-mvp-package.xml`
- `manifest/membership-update-status-package.xml`
- `manifest/membership-all-package.xml`
- `manifest/membership-renewal-fields-package.xml`

Email/Comms
- `manifest/email-comms.xml`

Governance
- `manifest/governance-mvp-package.xml`

Summit UI
- `manifest/summit-ui.xml`

---

## Helper scripts (macOS/Linux)

These wrap `sf ...` so you don’t fat-finger commands.

- Email/Comms: `scripts/email-comms.sh retrieve|deploy|validate`
- Membership: `scripts/membership.sh <slice> <command>`
  - slices: `mvp`, `all`, `update-status`, `renewal-fields`
- Events (Summit UI): `scripts/events.sh retrieve|deploy|validate`
- Governance: `scripts/governance.sh retrieve|deploy|validate`
- Canonical DIG: `scripts/dig.sh retrieve|deploy|validate`
- Org info: `scripts/org.sh display|list`

Windows: use Git Bash/WSL or run the underlying `sf` commands directly.

---

## Defaults (project-local)

Set defaults for *this repo* (avoid global CLI drift):
```bash
sf config set target-org deafingov
# optional
sf config set target-dev-hub deafingov

sf config get target-org
sf config get target-dev-hub
```

---

## Standard workflow (don’t freestyle)

### 1) Retrieve only what you need
```bash
sf project retrieve start --target-org deafingov --manifest manifest/dig.xml
```

### 2) Edit in `dig-src/`

### 3) Validate before you deploy
```bash
make dig-validate
```

### 4) Deploy a slice
```bash
sf project deploy start --target-org deafingov --manifest manifest/dig.xml
```

---

## Scope rules

### In-scope (versioned)
- DIG-owned metadata under `dig-src/`
  - custom objects/fields
  - permission sets
  - flows **when stable**
  - reports/dashboards when we want versioned ops views
- Manifests under `manifest/`

### Out-of-scope (UI-only; documented here)
- Lightning app navigation / pinned items / org home page tweaks
- List Views (unless we intentionally decide to version later)
- Managed package metadata (we configure it; we don’t own it)

---

## Data model decisions (current)

- **Contact is the spine.** People exist as Contacts whether or not they’re paid up.
- Membership status is expressed via membership fields/records + reporting.
- Campaigns stand on their own; Summit Events can associate events with campaigns.

---

## Membership slice

Retrieve (combined)
```bash
sf project retrieve start --target-org deafingov --manifest manifest/membership-all-package.xml
```

Deploy (combined)
```bash
sf project deploy start --target-org deafingov --manifest manifest/membership-all-package.xml
```

Renewal fields only
```bash
sf project retrieve start --target-org deafingov --manifest manifest/membership-renewal-fields-package.xml
```

---

## Email/Comms slice

What it does
- Renewal reminders via Scheduled Flow + Lightning Email Templates
- Throttling so we don’t spam members daily

UI prerequisites
- Setup → Deliverability: Access Level = **All Email**
- Setup → Org-Wide Email Addresses: add/verify `membership@deafingov.org`
- Setup → DKIM Keys: generate key(s) + publish the provided DNS CNAME(s)

Runbook
- `runbooks/email-comms.md`

Retrieve after UI creation
```bash
sf project retrieve start --target-org deafingov --manifest manifest/email-comms.xml
```

Deploy
```bash
sf project deploy start --target-org deafingov --manifest manifest/email-comms.xml
```

Validate (dry run)
```bash
sf project deploy validate --target-org deafingov --manifest manifest/email-comms.xml
```

---

## Governance MVP slice

Runbook
- `runbooks/flexipage-lightning-app.md`

Validate (dry run)
```bash
sf project deploy validate --target-org deafingov --manifest manifest/governance-mvp-package.xml
```

Deploy
```bash
sf project deploy start --target-org deafingov --manifest manifest/governance-mvp-package.xml
```

---

## Wild Apricot import notes

We imported members from Wild Apricot into Salesforce (Contacts). Some records were skipped due to **duplicate emails**; those can be scrubbed and re-imported later.

Ops guidance
- Contacts are canonical.
- Import Contacts first; derive/link membership second.
- Pick a dedupe rule early (email-first is fine for MVP).

---

## UI configuration (not versioned yet)

### Membership list views (UI)

Repro checklist:
1) **Active Members**
   - Status = Active
2) **Lapsed Members**
   - Status = Lapsed
3) **Renewals Due – Next 7 Days**
   - Status = Active
   - `Renewal_Due_Next_7_Days__c` = True
4) **Renewals Due – Next 30 Days**
   - Status = Active
   - `Renewal_Due_Next_30_Days__c` = True

Rule of thumb: if we need something durable and shareable, prefer **Reports/Dashboards** over List Views.

### Lightning apps / navigation

- Internal ops app label is **DIG Ops** (renamed from the default Sales label).
- Summit navigation is “good enough.” We prioritize **findability** over perfection.
- Preference: keep DIG Ops nav minimal (Home) and use App Launcher/search for Summit objects.

---

## Summit Events standard (DIG doctrine)

We run **all events** in DIG using Summit Events — coffee hours to major conferences (e.g., **NTC**).

Why
- One system of record
- Centralized reporting
- One workflow staff can learn once

Posture
- Summit is the **system of record for event operations** (types, instances, registrations/payments).
- Summit is a **managed package**: configure in UI, document choices here, avoid pulling Summit-owned metadata into `dig-src/`.

Operational conventions
- **Appointment Types / Event Types** = category (Coffee Hour, Webinar, Training, NTC, …)
- **Instances** = specific dates/times (occurrences)
- Use **Campaigns** for outreach goals; associate Summit events as needed
- Payments/registration only when needed; free events still get types + instances

Minimal smoke test
1) Create/confirm an Appointment Type
2) Create an Instance for a future date/time
3) (Optional) Associate to a Campaign
4) Confirm ops users can find records from **DIG Ops**

### Summit UI slice

Retrieve the app + home page metadata after UI changes (API names may differ; current prod uses `standard__LightningSales` and `DIG_Ops_Home1`):
```bash
sf project retrieve start --target-org deafingov --metadata "CustomApplication:standard__LightningSales"
sf project retrieve start --target-org deafingov --metadata "FlexiPage:DIG_Ops_Home1"
```

Deploy
```bash
sf project deploy start --target-org deafingov --manifest manifest/summit-ui.xml
```

---

## Guardrails

- **No layouts/profiles** unless explicitly requested.
- Flows are fragile as metadata; if deploy breaks, rebuild/re-save in Flow Builder, then re-retrieve.
- Never commit secrets.
- Keep commits small and surgical.
- UI-only setup changes must be written here.

---

## Troubleshooting

### Flow deploy failures
If a Flow deploy fails with structure/metadata errors:
1) Rebuild or re-save the Flow in Flow Builder (UI)
2) Re-retrieve just the Flow + FlowDefinition
3) Validate and deploy again

### “Why isn’t X in git?”
If it’s app nav, list views, pinned items, org homepage tweaks, or managed-package behavior: it’s probably **intentionally UI-only**. Document it in this README.