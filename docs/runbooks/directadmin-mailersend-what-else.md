# What DirectAdmin + MailerSend Can Do for DIG Ops

**Context:** DirectAdmin gives you DNS + mailboxes + domain control. MailerSend gives you deliverability, campaigns, automations, analytics, and (optionally) inbound routing. Together they become a lightweight, controlled communications platform for **DIG Ops**.

---

## 1) Member-Facing Messaging

### 1.1 Welcome / onboarding series
- Trigger: new member joins (Salesforce) or form submission
- Send: Day 0 / Day 3 / Day 7 emails:
  - how to engage with DIG
  - how to update preferences
  - next events and volunteer options

### 1.2 Renewal journeys
- Trigger: membership expiration date
- Sends:
  - 30 days before expiry
  - 14 days before expiry
  - 3 days before expiry
  - grace-period follow-ups (7/14 days after expiry)

### 1.3 Segment updates
- Federal vs non-federal
- Region/chapter
- Members vs non-members
- Event attendees (last 90 days)
- Sponsors contacts

### 1.4 Transactional email
- event confirmations and reminders
- form acknowledgments
- password reset/portal notifications (if applicable)

---

## 2) Fundraising + Sponsorship

### 2.1 Donation receipts
- Trigger: payment captured (processor) or marked Received in Salesforce
- Deliver: immediate thank-you + receipt
- Track: receipt status and SLA (target: within 48 hours)

### 2.2 Sponsorship pipeline messaging
- Proposal sent → follow-up cadence
- Committed → invoice + onboarding
- Paid → benefit delivery checklist and confirmation
- Fulfilled → renewal warm-up 60–90 days before term end

### 2.3 Sponsor stewardship
- Quarterly impact updates
- Sponsor recognition confirmations
- Renewal and upgrade prompts

### 2.4 Campaign launches
- Giving Tuesday
- Annual drive
- Event fundraising
- Track click-through and conversions by segment

---

## 3) DIG Ops “Front Door” Automation

### 3.1 Role-based inboxes
Create mailboxes/aliases such as:
- `ops@...` (DIG Ops Admin intake)
- `comms@...`
- `fundraising@...`
- `receipts@...`
- `events@...`

### 3.2 Inbound routing (optional but powerful)
If you enable MailerSend Inbound Routes:
- `ops@...` → create an Ops ticket (Salesforce Case or SharePoint list item) via webhook
- `events@...` → create an event request intake item
- `fundraising@...` → log sponsor inquiries automatically
- Attach original email text + metadata to the ticket for traceability

---

## 4) Deliverability + Domain Protection

### 4.1 Authentication
- SPF: authorizes sending sources
- DKIM: cryptographic signing
- Return-Path: bounce handling
- DMARC: reporting + spoof protection

### 4.2 DMARC enforcement plan
- Start: `p=none` (monitoring)
- Move to: `p=quarantine` (reduce abuse)
- End: `p=reject` (block spoofing)

### 4.3 Split sending streams (recommended)
Use subdomains to protect reputation:
- `news.deafingov.org` — bulk newsletter/campaigns
- `ops.deafingov.org` — transactional/ops communications

---

## 5) Web + Archive

### 5.1 “View in browser” archive
- MailerSend hosted pages (“view in browser”) can serve as an archive

### 5.2 Website archive (recommended)
- Auto-post each send to WordPress (or Astro) as a public archive entry
- Benefits:
  - transparency
  - institutional memory
  - accessible reference for members

---

## 6) Analytics You Can Actually Use

### Per send
- delivered
- click-through rate (most actionable)
- unsubscribe rate
- bounce rate
- segment size

### Monthly
- list growth
- best CTAs
- best-performing segments
- campaign performance (fundraising/event conversion drivers)

---

## 7) The 3 DIG Power Moves

1) **Subdomain separation:** `news.` (bulk) vs `ops.` (transactional)  
2) **Inbound Routes for ops@:** emails become Ops tickets automatically  
3) **Lifecycle journeys:** onboarding + renewals + lapsed-member reactivation  

---

## 8) Next-Step Selector (Pick One)

Choose the next automation to build:
- Renewals journey
- Event comms lifecycle
- Donation receipts + thank-you
- Ops intake (ops@ → ticket)

For whichever you pick, implement:
- triggers
- segments
- templates
- logging/archiving
- success metrics

