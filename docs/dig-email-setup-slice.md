# DIG Email Setup Slice (Transactional + Broadcast)

> Goal: enable reliable email from Salesforce for DIG, with a durable pattern:
> - **Transactional email** (renewals, confirmations, governance/event notices) via Flow + templates
> - **Broadcast email** (newsletter/announcements) via Salesforce Foundations marketing or an external ESP (MailerSend) as scale grows

---

## Two Lanes

### Lane A — Transactional (recommended first)
Use this for:
- Membership renewal reminders (7 / 30 days)
- Membership lapsed notifications
- Governance motion opened/closed notices
- Event registration confirmations (later)

**Why:** low volume, high importance, deterministic triggers, best handled by Flow.

### Lane B — Broadcast (newsletter)
Use this for:
- DIG newsletter
- announcements to all members
- campaigns

**Note:** Salesforce Foundations marketing has monthly send limits; use it for early-stage lists, switch to MailerSend as list grows.

---

## Transactional Email: Setup Checklist (Salesforce)

### 1) Deliverability
**Setup → Deliverability**
- Set **Access Level** to **All Email**

> If this is “System Email Only”, templates/flows won’t send to real recipients.

---

### 2) Org-Wide Email Addresses (OWEA)
**Setup → Organization-Wide Addresses → Add**
Create (at minimum) one sender identity:

Suggested:
- `membership@deafingov.org` (renewals + membership operations)
Optional:
- `ops@deafingov.org` (general operations)
- `noreply@deafingov.org` (if you want “no replies”)

Steps:
1. Add the address
2. Verify it via email link
3. Set it as the **Default** sender if desired

---

### 3) Default No-Reply
Salesforce increasingly expects a verified return/no-reply address.

- In **Organization-Wide Addresses**, designate a **Default No-Reply** address and verify it.

---

### 4) Authentication (recommended)
#### DKIM
**Setup → DKIM Keys**
- Generate DKIM key(s)
- Add the CNAME(s) to your DNS (deafingov.org)
- Activate DKIM in Salesforce

#### SPF / DMARC (domain-level)
In DNS for `deafingov.org`:
- Ensure SPF includes Salesforce sending (and any ESP like MailerSend)
- Ensure DMARC exists (start with `p=none`, move to `quarantine/reject` once stable)

> DKIM + DMARC materially improves inbox placement.

---

## Transactional Email: Templates + Flow Wiring

### Templates (Lightning Email Templates)
Create these templates (folder: `DIG Email`):

1) **Membership Renewal – Next 7 Days**
- Subject: `DIG Membership renewal due in 7 days`
- Body: include Contact name, End Date, renewal instructions/link

2) **Membership Renewal – Next 30 Days**
- Subject: `DIG Membership renewal due in 30 days`

3) **Membership Lapsed**
- Subject: `Your DIG membership has lapsed`

Optional later:
- Governance motion opened
- Governance motion closed (result)
- Event registration confirmation

---

### Flow pattern (recommended)
Use a **Scheduled Flow** (daily) rather than a record-triggered flow for reminders.

**Why:** record-triggered flows fire on edits, not “time passing”.

#### Scheduled Flow: `DIG_Membership_Renewal_Reminders_Daily`
- Runs daily at (e.g.) 8:00 AM
- Query Memberships where:
  - `Status__c = "Active"`
  - and (`Renewal_Due_Next_7_Days__c = TRUE` OR `Renewal_Due_Next_30_Days__c = TRUE`)
- For each record:
  - Send email using the appropriate template
  - Record “last reminder sent” (recommended) to avoid daily spam

#### Anti-spam fields (strongly recommended)
Add these fields to `Membership__c`:
- `Last_Renewal_Reminder_7D_Sent__c` (Date)
- `Last_Renewal_Reminder_30D_Sent__c` (Date)

Logic:
- Only send 7D email if last sent date is blank or < today
- Only send 30D email if last sent date is blank or < today

---

## Broadcast Email Options

### Option 1 — Salesforce Foundations Marketing (good for early stage)
Pros:
- In-platform segmentation
- Quick to start

Cons:
- Monthly send limits and feature caps

Recommended use:
- Monthly newsletter
- Small list

### Option 2 — MailerSend (recommended as you scale)
Pros:
- Better bulk deliverability tooling
- Scales cleanly with list size
- Dedicated sending infrastructure

Pattern:
- Salesforce = source of truth for Contacts + consent flags
- Export/Sync segments to MailerSend
- Send newsletter from MailerSend
- (Optional) write back high-level engagement metrics to Salesforce

---

## Minimal “Do Today” Plan (30 minutes)

1. Set Deliverability to **All Email**
2. Add and verify `membership@deafingov.org` as an Org-Wide Email Address
3. Add and verify a **Default No-Reply**
4. Create the **Membership Renewal – Next 7 Days** template
5. Create a **Scheduled Flow** stub that:
   - Finds memberships due in 7 days
   - Sends the template
6. Send a test email to yourself

---

## Version Control (SFDX)

Track in git:
- Email templates
- Flows / FlowDefinitions
- Permission sets related to email actions
- Any custom fields added to support reminder throttling

Avoid tracking:
- UI list views (document in README; prefer Reports for versioned views)

Create manifests for tight slices:
- `manifest/membership-email-package.xml` (templates + flows + fields)

---

## Notes / Guardrails

- Always verify OWEA addresses before enabling production sends.
- Use scheduled flow for time-based reminders.
- Add “last sent” fields to prevent spamming members.
- Prefer Reports/Dashboards for versioned operational views.
