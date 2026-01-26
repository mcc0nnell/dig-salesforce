# DIG Salesforce Runbook (Sales + Service Cloud)
**Purpose:** A repeatable, “bureaucrat-proof” playbook to configure, deploy, and operate DIG’s Salesforce org using a **CLI-first, Git-tracked** approach.

**Scope (Phase 1):**
- Org access + admin safety (avoid lockouts)
- Repo + Salesforce CLI workflow
- Core data foundations
- **Membership** (custom object pattern)
- **Summit Events App** (install + configuration overlay)
- Deployment, rollback, and troubleshooting

**Audience:** DIG admins (Robert, Jim) + any future Operations/IT volunteers.

---

## 0) Non-negotiables
1. **Two admins minimum** (Robert + Jim) with working MFA.
2. A **break-glass admin** exists and is tested.
3. All configuration changes are either:
   - committed to Git and deployed via CLI, or
   - documented in the Change Log when UI-only.

---

## 1) Roles and Responsibilities
- **Primary Admin:** Robert McConnell — architecture, standards, governance.
- **Secondary Admin:** Jim — recovery, validation, peer review.
- **Ops (future):** executes imports, sends comms, event setup.
- **Support:** Salesforce Support (only for platform-level issues / lockouts without admin path).

---

## 2) Access and Admin Safety
### 2.1 Break-glass admin (required)
**Create:** a dedicated sysadmin user with:
- separate email inbox (not shared with daily use)
- separate MFA device
- stored recovery codes offline (secure storage)

**Test cadence:** quarterly.
- Confirm login works from a clean browser session.
- Confirm at least 2 MFA methods are enrolled.

### 2.2 MFA policy
For every admin user:
- MFA method #1: passkey/security key (if desired)
- MFA method #2: TOTP authenticator app (backup)

**Rule:** No admin should have only one MFA method.

### 2.3 Domain changes
Any My Domain / login URL changes require a mini change-management event:
- Before change: confirm break-glass works.
- After change: confirm each admin can log in and re-enroll passkeys if needed.
- Record the change in the Change Log.

---

## 3) Tooling (Local Machine)
### 3.1 Install prerequisites
- Salesforce CLI (`sf`)
- Git
- VS Code (recommended) with Salesforce extensions (optional)
- A password manager / secure vault for credentials and recovery codes

### 3.2 CLI sanity checks
```bash
sf --version
sf org list
```

---

## 4) Repo and Branching Model
### 4.1 Repository
Create a dedicated repository, e.g.:
- `dig-salesforce-config`

### 4.2 Structure (recommended)
```
dig-salesforce-config/
  force-app/main/default/      # metadata overlay
  data/                        # CSVs for seed/import (no sensitive data)
  scripts/                     # repeatable CLI scripts
  docs/
    CHANGELOG.md
    RUNBOOK.md                 # this document
```

### 4.3 Branching
- `main`: stable, deployable
- `dev`: active work
- feature branches: `feat/membership`, `feat/events`, etc.

**Rule:** Deploy to production from `main` only.

---

## 5) Standard CLI Workflow
### 5.1 Connect and set target org
```bash
sf org login web --alias digprod
sf config set target-org=digprod
```

### 5.2 Deploy overlay metadata
```bash
sf project deploy start --source-dir force-app/main/default
```

### 5.3 Verify quickly
- Setup → **Setup Audit Trail**
- Object Manager → confirm object/fields exist
- App Launcher → confirm tabs/lists as expected

### 5.4 Rollback strategy
- Preferred: revert Git commit and redeploy
- If a deploy fails mid-way: fix forward; Salesforce deployments can be partial depending on what failed

---

## 6) Change Control
### 6.1 Change log
Maintain `docs/CHANGELOG.md` with:
- date/time
- who changed what
- why
- rollback note
- link to PR/commit (if applicable)

### 6.2 UI-only changes
Some settings are UI-only or painful as metadata. If done in UI:
- Document it in the Change Log.
- If possible, capture screenshots and store in `docs/screens/`.

---

## 7) Data Foundations
### 7.1 Contact “golden fields” (Phase 1 baseline)
Decide and standardize:
- Primary Email
- Mobile Phone
- Mailing Address
- Preferred Name (if used)
- Email Consent / Opt-in Source / Opt-in Date

### 7.2 Dedup rules
- Matching rule: email (case-insensitive)
- Duplicate rule: block or alert on create depending on risk tolerance
- Import policy: **Contacts first**, then related objects

---

# PART A — Membership (Phase 1)

## 8) Membership Data Model (recommended)
### 8.1 Custom object: `Membership__c`
**Why:** preserves history and avoids overwriting Contact fields.

Core fields:
- `Member__c` (Lookup to Contact)
- `Status__c` (Prospect, Active, Lapsed, Suspended, Honorary)
- `Start_Date__c` (Date)
- `End_Date__c` (Date)
- `Membership_Type__c` (Individual, Student, Supporting, Lifetime)
- `Source__c` (Wild Apricot Import, Website Form, Manual, Event Signup, Referral)
- `Notes__c` (Long text)

### 8.2 Contact snapshot fields (for segmentation)
- `Current_Membership_Status__c`
- `Current_Membership_Type__c`
- `Current_Membership_End_Date__c`

### 8.3 Permission set
- `DIG_Membership_Admin` (CRUD on Membership; Read/Edit on snapshot fields)

---

## 9) Membership Automation (Flows)
**Deploy order:** objects/fields first → then flows.

### 9.1 Flow 1: Sync Contact Snapshot
Trigger: Membership create/update
- Update Contact snapshot fields from Membership

### 9.2 Flow 2: Auto-lapse expired memberships
Scheduled daily
- If `Status = Active` and `End_Date < TODAY` → set to `Lapsed`
- Update Contact snapshot fields accordingly

---

## 10) Membership Import Runbook (Wild Apricot)
### 10.1 Prepare CSVs (no secrets)
1) `data/contacts_import.csv`
2) `data/memberships_import.csv`

### 10.2 Import sequence
1) Import Contacts (dedupe by email)
2) Import Membership__c (link to Contact)

### 10.3 Post-import checks
- Report: Active memberships
- List view: Active members (Contact snapshot)
- Spot-check 25 random records

---

# PART B — Summit Events App (SEA)

## 11) Summit Events App — Install vs Configure
**Install:** typically done via MetaDeploy / package installer (UI).  
**Configure:** can be scripted via metadata overlay + CLI.

### 11.1 Install (UI)
- Install the “Base Plan” (or standard plan) into DIG production org.
- After install: follow post-install instructions.

### 11.2 Overlay configuration (CLI)
Use Codex + SFDX metadata to create:
- `DIG_SEA_Admin` permset
- `DIG_SEA_Staff` permset
- `DIG_SEA_Guest_Account_Read` permset (for Experience Cloud guest)
- SEA Custom Metadata records for contact matching field mapping (email-first)

### 11.3 Guest user setup (likely UI step)
- Experience Cloud Site → Guest User → assign:
  - packaged SEA registrant permset (if required by SEA)
  - `DIG_SEA_Guest_Account_Read` (overlay)

---

## 12) SEA Smoke Test (2-minute)
1) App Launcher → Summit Events
2) Create a Summit Event
3) Create an Event Instance
4) Ensure Instance is **Active** and capacity is set
5) Open registration link and perform a test registration

**Acceptance criteria:** registration creates/associates Contact cleanly; event staff can view registration.

---

# PART C — Operations

## 13) Core Reports (Phase 1)
### Membership
- Active Members
- Expiring in 30 days
- New Members this month
- Lapsed Members

### Events (SEA)
- Registrations by Event Instance
- Attended vs No-show (if tracking)
- New registrants by source

---

## 14) Backup / Recovery
- Maintain break-glass credentials offline
- Quarterly access test
- Export critical data monthly (Contacts, Membership, Events/Registrations)

---

## 15) Troubleshooting Playbook
### 15.1 Locked out / MFA issues
- If any admin can log in: generate temporary verification code or disconnect MFA method for affected user.
- If no admins can log in: escalate to Salesforce Support with org ownership verification.

### 15.2 Deploy failures
- Read the deploy error message
- Fix forward (most common: missing field references, permission issues)
- Re-run deploy
- Log the incident in Change Log

### 15.3 Data import problems
- If duplicates explode: pause imports, refine matching rules, re-import in smaller batches
- Always keep raw export snapshots (read-only) for backtracking

---

## 16) “Definition of Done” for Phase 1
- [ ] Two admins + break-glass admin tested
- [ ] Membership object live + permission set assigned
- [ ] Two membership flows enabled
- [ ] Active Member list view works from Contact snapshot fields
- [ ] Summit Events installed + overlay deployed
- [ ] SEA smoke test passed
- [ ] Change Log started and used

---

## Appendix A — Suggested Naming Conventions
- Flows: `FLOW – Membership – Sync Contact Snapshot`
- Permission sets: `DIG_*`
- Reports: `RPT – Membership – Active`
- List views: `Active Members`

---

## Appendix B — What to automate later (not Phase 1)
- Paid dues (payments + receipts)
- Advanced household/org memberships
- Portal/Experience for members
- Marketing Cloud / Account Engagement integrations
- Complex approval processes
