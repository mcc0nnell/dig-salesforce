# DIG Ops Admin Runbook (Internal Cockpit + Work Queue)

**Purpose:** Build the “DIG Ops Admin” cockpit that replaces tribal knowledge with an operational system: **what’s open, who owns it, what’s due, and what’s blocked**—across membership, events, communications, fundraising, and governance.

**Outcome:** DIG runs like a small, disciplined operations team: clear intake, clear ownership, measurable throughput, and board-ready visibility.

---

## 0) Operating Model

### DIG Ops Admin is:
- A **single front door** for requests
- A **work queue** with owners + due dates + status
- A **dashboard** showing health and bottlenecks
- A **change log** for decisions and key updates

### DIG Ops Admin is NOT:
- A complicated ticketing bureaucracy
- A replacement for your CRM (it sits on top)
- A place where tasks disappear without ownership

---

## 1) Core Work Objects (Minimal + Durable)

### Option A (Salesforce-native, recommended)
Use **Case** as the DIG Ops work item (“Ops Ticket”), with record types:
- Membership Ops
- Events Ops
- Communications Ops
- Fundraising Ops
- Governance Ops
- IT/Website Ops (optional)

**Why Case:** built-in queues, assignment rules, SLAs, email-to-case, reporting.

### Option B (M365 / SharePoint-native)
Use a **SharePoint List** called **DIG Ops Queue** with columns (below).
Power Automate handles notifications and status changes.

> Pick one platform as the source of truth. Don’t split queues across tools.

---

## 2) Standard Fields (Work Item Schema)

### Required fields (every work item)
- **Title** (short, action-oriented)
- **Category** (Membership / Events / Comms / Fundraising / Governance / IT)
- **Requester** (person + contact info)
- **Owner** (DIG Ops assignee)
- **Status** (New, Triage, In Progress, Blocked, Waiting on Requester, Done, Closed)
- **Priority** (P0, P1, P2)
- **Due Date**
- **Description** (what’s needed + context)
- **Definition of Done** (one sentence)

### Recommended fields
- **Impact** (Low/Medium/High)
- **Effort** (S/M/L)
- **Related Record** (link to Contact/Opportunity/Event/Campaign/etc.)
- **Attachments/Links**
- **Approver** (if needed)
- **SLA Target** (date/time)
- **Completed Date**

---

## 3) Intake (Single Front Door)

### Intake methods (choose 1–2)
- **Email-to-Case** (e.g., `ops@dig...`) OR
- **Microsoft Form / Salesforce Web-to-Case** OR
- **Slack/Teams channel + form shortcut** (but form creates the ticket)

### Intake form minimum fields
- Request type (Category)
- Desired deadline
- Who is impacted
- Any links/attachments
- Approval needed? (Y/N)

**Rule:** No work starts without a ticket (unless true emergency).

---

## 4) Triage Rules (15 minutes/day)

### Status meanings
- **New:** arrived, not yet reviewed
- **Triage:** clarifying, scoping, assigning
- **In Progress:** actively being executed
- **Blocked:** needs external dependency (explicit)
- **Waiting on Requester:** you asked a question; clock paused
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

## 5) DIG Ops Admin “Cockpit” Dashboards

### Daily dashboard tiles
- **Open items by status**
- **Overdue items**
- **Blocked items** (with reason)
- **Waiting on requester**
- **Today’s due items**

### Weekly dashboard tiles
- **Throughput** (items closed this week)
- **Aging** (how long items sit in New/Triage/Blocked)
- **Work by category** (Membership vs Fundraising vs Comms)
- **Top requesters** (useful for pattern fixes)

### Monthly/Board tiles (lightweight)
- **Operational highlights** (top 5 completed)
- **Risks/issues** (top 5 blocked/overdue)
- **Trends** (volume by category)

---

## 6) Operational Rituals (The “Run the Org” Cadence)

### Daily (15 minutes)
1. Triage New
2. Clear Overdue / set next actions
3. Unblock Blocked (one outreach per blocked item)

### Weekly (30 minutes)
1. Review category lanes:
   - Membership
   - Events
   - Comms
   - Fundraising
   - Governance
2. Close stale tickets (“kill or commit”)
3. Publish a 5-bullet “Ops Update” (internal)

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

### 7.3 “Waiting on requester” timer
- Auto-remind requester after 3 days
- Auto-close after 14 days of no response (with reopen path)

### 7.4 Done → Archive
- When Closed:
  - create an entry in a simple **Ops Change Log**
  - attach final artifacts/links

---

## 8) Standard Views (Queues You Actually Use)

- **My Work (Open)**
- **New / Needs Triage**
- **Overdue**
- **Blocked**
- **Waiting on Requester**
- **This Week**
- **By Category** (Membership / Events / Comms / Fundraising / Governance)

---

## 9) Governance & Change Log

Create a lightweight **DIG Ops Change Log** record/list with:
- Date
- Summary
- Tickets linked
- Decision(s) made
- Approver (if any)
- Artifacts/links

**Rule:** Anything that changes process, policy, or public-facing info gets logged.

---

## 10) Verification Checklist (Go-Live)

- [ ] Single intake method works (email or form)
- [ ] Work item schema includes owner + due date + status
- [ ] Category lanes exist (Membership/Events/Comms/Fundraising/Gov)
- [ ] Dashboards show open/overdue/blocked
- [ ] Auto-reminders and escalation rules active
- [ ] Standard views created
- [ ] Change log exists and is used
- [ ] First week: 100% of work goes through the queue

---

## 11) Change Log (fill in)

- Date:
- Changed by:
- Platform:
  - [ ] Salesforce Case-based queue
  - [ ] SharePoint list-based queue
- Notes / exceptions:

