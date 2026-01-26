# DIG Ops Fundraising Runbook (50/50 Donations + Sponsorships)

**Purpose:** Stand up a lightweight, operationally solid fundraising system for DIG that supports **individual donations** and **organizational sponsorships** at roughly a 50/50 mix, with fast receipts, clear stewardship, and board-ready reporting.

**Design principle:** Use **Salesforce Opportunity** as the single source of truth for revenue, with **two record types** and **label-first** changes (avoid breaking API/developer names).

---

## 0) Operating Model

### Revenue lanes
- **Donation lane** (individuals; sometimes checks/ACH; sometimes online)
- **Sponsorship lane** (organizations; proposals, invoices, benefit fulfillment)

### What “done” looks like
- Every dollar maps to an **Opportunity**
- Receipts issued within **48 hours**
- Sponsorships have a **trackable pipeline** + **deliverable checklist**
- Board can see: **YTD**, **pipeline**, **top donors**, **campaign performance**

---

## 1) Data Model (Minimal + Durable)

### Standard Objects
- **Account** — organizations (sponsors, employers, partners)
- **Contact** — individuals (donors, sponsor points-of-contact)
- **Opportunity** — *each* donation or sponsorship
- **Campaign** — optional but recommended (Annual Drive, Giving Tuesday, Event Sponsorship)

### Optional Custom Objects (if you want “benefits” tracking to be real, not tribal)
- **Sponsorship Package** (Gold/Silver/Bronze/Custom; benefits + default amount)
- **Benefit Delivery** (logo placement, newsletter mention, speaking slot, etc.)
- **Stewardship Task** (structured follow-ups; can also be Tasks with a “Type”)

**MVP path:** Opportunity + Tasks + Campaigns only.

---

## 2) Configure Opportunities (Two Record Types)

### 2.1 Create Record Types
- Opportunity Record Type: **Donation**
- Opportunity Record Type: **Sponsorship**

### 2.2 Donation Stages (simple and operational)
1. **Pledged**
2. **Received**
3. **Thanked**
4. **Closed Lost**

### 2.3 Sponsorship Stages (pipeline + delivery)
1. **Prospecting**
2. **Proposal Sent**
3. **Committed**
4. **Invoiced**
5. **Paid**
6. **Fulfilled**
7. **Closed Lost**

> Tip: Keep stage meanings crisp. “Committed” means verbal/written yes; “Paid” means money received; “Fulfilled” means benefits delivered.

---

## 3) Fields (Bureaucrat-Proof Minimum)

### 3.1 Donation fields (Opportunity)
**Required**
- Amount
- Close Date
- **Payment Method** (Picklist: Card, ACH, Check, Other)
- **Receipt Status** (Picklist: Not Sent, Sent, Not Required)
- **Recognition Preference** (Picklist: Public, Anonymous, Name As…)
- **Donor Type** (Picklist: Individual, Household if you use it)

**Optional but useful**
- **Receipt Email Override** (Text/Email)
- **Receipt Notes** (Long text)
- **Employer Match** (Checkbox)

### 3.2 Sponsorship fields (Opportunity)
**Required**
- Amount
- Close Date (expected)
- **Package Level** (Picklist: Gold, Silver, Bronze, Custom)
- **Invoice Needed** (Checkbox)
- **Invoice Status** (Picklist: Not Sent, Sent, Paid, Not Required)
- **Term** (Picklist or Date fields: Start Date / End Date)

**Optional but useful**
- **Primary Benefits** (Multi-select picklist)
- **Logo Received** (Checkbox)
- **Public Recognition Name** (Text)
- **Fulfillment Notes** (Long text)

### 3.3 Account/Contact fields (recommended)
- **Last Gift Date** (Date) *(can be formula/reporting if no rollups)*
- **Lifetime Giving** (Currency) *(rollup if possible; else report)*
- **YTD Giving** (Currency) *(report)*
- **Donor Tier** (Picklist; derived via automation or report)

---

## 4) Email Templates (Day-1 Must Have)

### Donation templates
- **Donation Thank You + Receipt** (includes nonprofit receipt language)
- **Donation Thank You (No Receipt Required)** (for edge cases)

### Sponsorship templates
- **Sponsorship Proposal Sent**
- **Sponsorship Commitment Confirmation**
- **Invoice Email** (if invoicing)
- **Paid Confirmation + Next Steps**
- **Benefits Fulfilled + Thanks**
- **Renewal Warm-Up**

**Template rule:** Put “DIG Ops” branding in footer and keep subjects consistent:
- “DIG Receipt: Thank you for your support”
- “DIG Sponsorship: Proposal”
- “DIG Sponsorship: Invoice”
- “DIG Sponsorship: Benefits & Recognition”

---

## 5) Automations (Flows / Power Automate)

### 5.1 Donation automation (fast receipts)
**Trigger:** Opportunity (Donation) Stage changes to **Received**
- If Receipt Status = Not Required → send “thank you” email only
- Else:
  - Send **receipt email**
  - Send **thank you email** (can be one combined email)
  - Create Task: “Stewardship follow-up” if Amount ≥ threshold (default $1,000)
  - Option A: move Stage → **Thanked** automatically
  - Option B: keep Stage at Received and create Task “Mark thanked” (manual control)

### 5.2 Sponsorship automation (pipeline + deliverables)
- Stage → **Proposal Sent**:
  - Create follow-up Task due in 7 days
- Stage → **Committed**:
  - If Invoice Needed = true:
    - Create Task “Send invoice” due in 1 day
    - Set Invoice Status = Not Sent
  - Create Task “Sponsor onboarding email” due in 1 day
- Stage → **Invoiced**:
  - Set Invoice Status = Sent
  - Create Task “Confirm receipt / payment ETA” due in 7 days
- Stage → **Paid**:
  - Set Invoice Status = Paid
  - Create benefit delivery Tasks (logo, newsletter mention, event signage, etc.)
- Stage → **Fulfilled**:
  - Create Task “Renewal warm-up” due 60 days before End Date (or 300 days after Paid if annual)

**MVP:** Use standard Tasks with a picklist field “Task Type”:
- Receipt
- Thank-you call
- Sponsorship follow-up
- Invoice
- Benefit delivery
- Renewal

---

## 6) Operating Queues (What DIG Ops Works Each Week)

Create saved report views / list views:

### Daily
- **Receipts to Send** (Donation: Stage = Received AND Receipt Status = Not Sent)
- **Thank-you Calls Due** (Tasks due today/overdue; type = Thank-you call)

### Weekly
- **Sponsorship Follow-ups** (Sponsorship: Stage in Prospecting/Proposal Sent and next task overdue)
- **Invoices to Send** (Invoice Status = Not Sent)
- **Benefits to Deliver** (Paid sponsors with incomplete benefit tasks)

### Monthly
- **Lapsed Donors** (Last Gift > 365 days)
- **Renewals Coming Up** (End Date within 60–90 days)

---

## 7) Campaigns (Optional but Recommended)

Create Campaigns for:
- **Annual Drive 2026**
- **Giving Tuesday 2026**
- **Spring Fundraiser Event 2026**
- **Sponsor Program FY26**

**Rule:** Every Opportunity should map to exactly one Campaign whenever possible.

---

## 8) Board-Ready Dashboards (Minimum Pack)

1. **YTD Revenue**: Donations vs Sponsorships (sum by record type)
2. **Monthly Trend**: last 12 months revenue
3. **Sponsorship Pipeline**: Amount by stage + expected close date
4. **Top 10 Donors / Sponsors**: YTD and Lifetime (separate views)
5. **Receipts SLA**: % receipts sent within 48 hours (proxy via CreatedDate vs Stage change date / receipt task completion)

---

## 9) Payment Capture (Practical MVP → Integration Later)

### MVP (fastest)
- Money arrives via your payment platform/bank/check.
- DIG Ops logs an Opportunity and marks stage appropriately.

### Next step (integration)
- Payment platform creates Opportunities automatically and attaches receipts.
- Keep Salesforce as system of record; payment platform as processor.

---

## 10) Weekly “DIG Ops Fundraising” Ritual (30 minutes)

1. Clear **Receipts to Send**
2. Review **Thank-you calls due**
3. Advance **Sponsorship pipeline** (next actions set on every open sponsor)
4. Check **Benefits to Deliver**
5. Snapshot: update dashboard and export 1-page summary for leadership

---

## 11) Verification Checklist (Go-Live)

- [ ] Donation record type exists with correct stages
- [ ] Sponsorship record type exists with correct stages
- [ ] Required fields configured and on layouts
- [ ] Receipt + thank-you templates present
- [ ] Donation “Received → receipt” automation works end-to-end
- [ ] Sponsorship stage automations create tasks reliably
- [ ] Saved views/queues exist for daily/weekly work
- [ ] Dashboard pack returns sane numbers
- [ ] Test: one donation + one sponsorship from start to finish

---

## 12) Change Log

- Date:
- Changed by:
- Notes / exceptions:
- Thresholds:
  - Stewardship task threshold: $______
  - Receipt SLA target: ______ hours

