# DIG Ops Admin Runbook (Internal Cockpit + Work Queue)

**Audience:** DIG internal operators/admins  
**Scope:** Membership, Events, Communications, Fundraising, Governance (and optional IT/Website)  
**Source of Truth Recommendation:** **Salesforce Case** (Service Cloud) unless you are explicitly standardizing on M365/SharePoint.

---

## 0) Operating Model

### DIG Ops Admin is
- A **single front door** for requests
- A **work queue** with owners + due dates + status
- A **cockpit dashboard** showing health + bottlenecks
- A **change log** for decisions and key updates

### DIG Ops Admin is not
- A complicated ticketing bureaucracy
- A replacement for CRM objects (Contacts/Campaigns/Events/etc.)
- A place where tasks disappear without ownership

**Hard rules**
1. No work starts without a ticket (**unless true emergency**).
2. Every ticket gets an **Owner + Due Date + Next Action** within 24 hours.
3. Anything that changes process/policy/public-facing info gets logged in the **Ops Change Log**.

---

## 1) Core Work Objects (Minimal + Durable)

### Option A — Salesforce-native (recommended): **Case** = “Ops Ticket”
Use **Case** as the work item with record types:
- Membership Ops  
- Events Ops  
- Communications Ops  
- Fundraising Ops  
- Governance Ops  
- IT/Website Ops (optional)

**Why Case:** queues, assignment rules, SLAs, Email-to-Case, built-in reporting, and a mature operational model.

### Option B — M365 / SharePoint-native: **DIG Ops Queue** list
Use a SharePoint List called **DIG Ops Queue** with columns (schema below).  
Power Automate handles notifications + status nudges.

> Pick one platform as the source of truth. Don’t split queues across tools.

---

## 2) Standard Fields (Work Item Schema)

### Required fields (every work item)
- **Title** (short, action-oriented)
- **Category** (Membership / Events / Comms / Fundraising / Governance / IT)
- **Requester** (person + contact info)
- **Owner** (assignee)
- **Status** (New, Triage, In Progress, Blocked, Waiting on Requester, Done, Closed)
- **Priority** (P0, P1, P2)
- **Due Date**
- **Description** (what’s needed + context)
- **Definition of Done** (one sentence)

### Recommended fields
- **Impact** (Low/Medium/High)
- **Effort** (S/M/L)
- **Related Record** (Contact/Campaign/Event/Opportunity/etc.)
- **Attachments/Links**
- **Approver** (if needed)
- **SLA Target** (date/time)
- **Completed Date**

---

## 3) Intake (Single Front Door)

### Intake methods (choose 1–2)
- **Email-to-Case** (e.g., `ops@dig...`) **OR**
- **Salesforce Web-to-Case** (public form) **OR**
- **Microsoft Form** (creates ticket via automation)
- Slack/Teams: acceptable *only* if it **creates a ticket** (shortcut to the form)

### Intake form minimum fields
- Category
- Desired deadline
- Who is impacted
- Links/attachments
- Approval needed? (Y/N)

---

## 4) Triage Rules (15 minutes/day)

### Status meanings
- **New:** arrived, not yet reviewed
- **Triage:** clarifying/scoping/assigning
- **In Progress:** actively executing
- **Blocked:** explicit external dependency (capture reason)
- **Waiting on Requester:** question asked; clock paused
- **Done:** work complete, awaiting closure/confirm
- **Closed:** confirmed + documented

### Priority rules
- **P0:** time-critical, reputation/legal risk, same-day
- **P1:** this week
- **P2:** backlog / next cycle

### Assignment rule
Every item gets:
- **Owner**
- **Due date**
- **Next action** (task/comment) within 24 hours

---

## 5) Cockpit Dashboards (What You See Every Day)

### Daily tiles
- Open items by status
- Overdue items
- Blocked items (with reason)
- Waiting on requester
- Due today

### Weekly tiles
- Throughput (items closed this week)
- Aging (time in New/Triage/Blocked)
- Work by category
- Top requesters (pattern fixes)

### Monthly / Board tiles (lightweight)
- Operational highlights (top 5 completed)
- Risks/issues (top 5 blocked/overdue)
- Trends (volume by category)

---

## 6) Operational Rituals (Cadence)

### Daily (15 minutes)
1. Triage New
2. Clear overdue / set next actions
3. Unblock blocked (one outreach per blocked item)

### Weekly (30 minutes)
1. Review category lanes:
   - Membership, Events, Comms, Fundraising, Governance
2. Close stale tickets (“kill or commit”)
3. Publish a 5-bullet **Ops Update** (internal)

### Monthly (30 minutes)
1. Board-ready snapshot: wins + risks + metrics
2. Identify 1–2 systemic fixes (reduce recurring work)

---

## 7) Automation Pack (High Impact)

### 7.1 Auto-assign (Queues)
- Category → Queue mapping
- P0 items notify DIG Ops immediately

### 7.2 SLA nudges
- Reminder at 24 hours before due
- Escalation when overdue by 48 hours (to ops lead)

### 7.3 Waiting-on-requester timer
- Auto-remind requester after 3 days
- Auto-close after 14 days of no response (with reopen path)

### 7.4 Done → Archive
When **Closed**:
- create an entry in **Ops Change Log**
- attach final artifacts/links

---

## 8) Standard Views (Queues You Actually Use)

- My Work (Open)
- New / Needs Triage
- Overdue
- Blocked
- Waiting on Requester
- This Week
- By Category (Membership / Events / Comms / Fundraising / Governance)

---

## 9) Governance & Change Log

Create a lightweight **DIG Ops Change Log** record/list with:
- Date
- Summary
- Tickets linked
- Decision(s) made
- Approver (if any)
- Artifacts/links

**Rule:** anything that changes process, policy, or public-facing info gets logged.

---

## 10) Go-Live Verification Checklist

- [ ] Single intake method works (email or form)
- [ ] Work item schema includes owner + due date + status
- [ ] Category lanes exist (Membership/Events/Comms/Fundraising/Gov)
- [ ] Dashboards show open/overdue/blocked
- [ ] Auto-reminders and escalation rules active
- [ ] Standard views created
- [ ] Change log exists and is used
- [ ] First week: 100% of work goes through the queue

---

# Implementation Appendix A — Salesforce Build Steps (Case-based DIG Ops)

This appendix turns the runbook into an actual Salesforce build plan.

## A1) Objects & Metadata

### A1.1 Case Record Types
Create these **Case** record types:
- Membership Ops
- Events Ops
- Communications Ops
- Fundraising Ops
- Governance Ops
- IT/Website Ops (optional)

### A1.2 Picklists / Fields
Implement schema using standard + custom fields:

**Standard fields to use**
- Subject → **Title**
- Status → map to the Ops statuses below
- Priority → map to P0/P1/P2 (customize values if needed)
- Owner → user or queue
- Due Date → create custom field `Due_Date__c` (Date) if not present
- Description → standard Description

**Custom fields (recommended)**
- `Category__c` (Picklist): Membership, Events, Comms, Fundraising, Governance, IT
- `Impact__c` (Picklist): Low, Medium, High
- `Effort__c` (Picklist): S, M, L
- `Definition_of_Done__c` (Text 255)
- `Blocked_Reason__c` (Long Text) — show only when Status = Blocked
- `Requester__c` (Lookup Contact) — if requesters are Contacts
- `Requester_Email__c` (Email) — if requester may not be a Contact yet
- `Related_Record_URL__c` (URL) or use standard Related lookup patterns by object

### A1.3 Status values (Case)
Edit Case Status values (or use a dedicated Status picklist if org constraints apply):
- New
- Triage
- In Progress
- Blocked
- Waiting on Requester
- Done
- Closed

> If your org requires “Closed” statuses to be final, keep **Closed** as the only closed status, and treat **Done** as “resolved but not confirmed.”

---

## A2) Queues, Assignment Rules, & Email-to-Case

### A2.1 Queues
Create queues:
- DIG Ops – Membership
- DIG Ops – Events
- DIG Ops – Comms
- DIG Ops – Fundraising
- DIG Ops – Governance
- DIG Ops – IT (optional)
- DIG Ops – Triage (optional “inbox” queue)

### A2.2 Assignment rule mapping
If using Email-to-Case or Web-to-Case, implement:
- If Category = Membership → queue DIG Ops – Membership
- If Category = Events → DIG Ops – Events
- etc.
- If Priority = P0 → notify ops lead + create chatter/email alert

### A2.3 Email-to-Case
- Create routing address: `ops@...`
- Configure Email-to-Case so emails create Cases with:
  - Status = New
  - Record Type = (default) “Membership Ops” or “Ops Ticket” if you create one umbrella RT
  - Owner = DIG Ops – Triage queue
- Use Email Templates for acknowledgements (“We got it; here’s your ticket # and next steps.”)

---

## A3) Page Layouts & Lightning App

### A3.1 Page layout essentials
- Put Owner, Status, Priority, Due Date, Category at the top
- Add a **Next Action** section (use Tasks or a custom text field)
- Add a **Blocked Reason** section (conditional visibility)
- Related Lists: Tasks, Emails, Files, Chatter, Related Contact/Campaign/Event if relevant

### A3.2 “DIG Ops Admin” Lightning App
Create a dedicated Lightning App:
- Navigation Items: Cases, Reports, Dashboards, Contacts, Campaigns, Events (Summit), Change Log object/list
- Home page: embed the cockpit dashboard(s) + quick links to queue views

---

## A4) Reports & Dashboards (minimum viable cockpit)

### A4.1 Reports to create
1. Open Cases by Status
2. Overdue Cases (Due Date < TODAY and not Closed)
3. Blocked Cases (Status = Blocked)
4. Waiting on Requester
5. Throughput: Closed this week
6. Aging: Average days in status (or bucket by Created Date)

### A4.2 Dashboard tiles (minimum)
- Open by status (stacked bar)
- Overdue count (metric)
- Blocked count (metric)
- Waiting-on-requester count (metric)
- Closed this week (metric)
- Work by category (donut/bar)

---

## A5) Automations (Flow / Rules)

### A5.1 Due-date reminders
Scheduled Flow:
- find cases due in 24 hours and not Closed → notify Owner
- find cases overdue by 48 hours → notify Ops Lead

### A5.2 Waiting-on-requester timer
Scheduled Flow:
- if Status = Waiting on Requester and Last Modified Date > 3 days → email reminder to requester
- if Status = Waiting on Requester and Last Modified Date > 14 days → set Status = Closed (Reason: No response) and include reopen instructions

### A5.3 Close → Change Log
Record-triggered Flow:
- when Status becomes Closed → create Change Log entry referencing the Case
- attach links/artifacts if provided

---

# Implementation Appendix B — SharePoint Build Steps (if M365 is the source of truth)

## B1) List: DIG Ops Queue
Columns:
- Title (single line text)
- Category (choice)
- Requester (person)
- Owner (person)
- Status (choice)
- Priority (choice)
- Due Date (date)
- Description (multiple lines)
- Definition of Done (single line)
- Impact (choice)
- Effort (choice)
- Blocked Reason (multiple lines)
- Related Record (hyperlink)
- Approver (person)
- Completed Date (date)

## B2) Views
- My Work (Owner = [Me], Status != Closed)
- Needs Triage (Status = New or Triage)
- Overdue (Due Date < Today, Status != Closed)
- Blocked
- Waiting on Requester
- This Week (Due Date between Today and Today+7)

## B3) Power Automate
- On create: assign to queue owner by category, notify owner
- Due-date reminders + escalation
- Waiting-on-requester reminders + auto-close
- Close → append to Change Log list

---

## 11) Change Log (fill in)

- Date:
- Changed by:
- Platform:
  - [ ] Salesforce Case-based queue
  - [ ] SharePoint list-based queue
- Notes / exceptions:
