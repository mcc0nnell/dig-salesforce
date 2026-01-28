# DIG Comms Engine (Apex): Email-to-Case Triage + SLA + Agentforce Hooks

**Goal:** Make general DIG email comms operational:
- inbound email → Case
- classify + route deterministically
- auto-acknowledge with consistent tone
- SLA/escalation
- optional Agentforce drafting hooks (human-in-the-loop first)

This is written to be deployable via `sf project deploy validate` and to align with **Geary cook/run** later.

---

## 1) Architecture

### A) Intake spine: Email-to-Case
- Public inbox(es) forward into Salesforce as Cases.
- Routing addresses map email addresses → queues.

### B) Apex owns the “comms brain”
1) **Classification** (topic, urgency, member/non-member)
2) **Routing** (queue + owner)
3) **Acknowledgement** (template-driven)
4) **SLA tracking** (first response target, escalation)
5) **Agentforce hook** (optional): create a “Draft Requested” record/state

---

## 2) Recommended minimal Case fields (custom)

Add these on Case:

- `DIG_Topic__c` (Picklist): Membership, Summit, Governance, Sponsorship, General
- `DIG_Urgency__c` (Picklist): Low, Normal, High
- `DIG_SLA_FirstResponseBy__c` (Datetime)
- `DIG_SLA_Status__c` (Picklist): OnTrack, AtRisk, Breached
- `DIG_SourceEmail__c` (Email/Text)
- `DIG_AutoAck_Sent__c` (Checkbox)
- `DIG_AI_Draft_Status__c` (Picklist): None, Requested, Drafted, Sent, Suppressed

Optional:
- `DIG_Sensitive__c` (Checkbox) — true if payment/dispute/sensitive keywords detected

---

## 3) Classification rules (deterministic + auditable)

We use simple, explicit keyword rules first (you can swap to ML later):

Topic:
- Membership: "join", "renew", "dues", "member", "login"
- Summit: "summit", "event", "registration", "schedule", "ticket"
- Governance: "motion", "vote", "board", "minutes"
- Sponsorship: "sponsor", "donate", "partnership", "funding"
- Else: General

Urgency:
- High if: "urgent", "ASAP", "accessibility issue", "cannot access", "refund"
- Normal otherwise

Sensitive:
- if includes: "credit card", "payment", "chargeback", "SSN", "bank"

Everything written back to Case fields so you can explain “why it routed.”

---

## 4) SLA policy (default)

- First response target: **1 business day** (configurable)
- At-risk threshold: within 4 hours of breach
- Breach: now > FirstResponseBy

Escalation:
- create Task for queue lead
- optionally notify Slack/Email (future)

---

## 5) Agentforce hook pattern (safe)

Start with human-in-the-loop:

- When Case created and not sensitive:
  - set `DIG_AI_Draft_Status__c = Requested`
- A rep uses **Service Replies for Email** to draft in-console (manual)
- Later, you can add an async job that:
  - compiles “draft context” (case + knowledge refs)
  - requests a draft
  - stores it (as Case Comment or a custom Draft object)

This scaffold just creates the state + places to wire actions.

---

## 6) Included Apex scaffolding

- Trigger actions dispatcher (same as Summit scaffold)
- `DigCaseAction_ClassifyAndRoute`
- `DigCaseAction_AutoAcknowledge` (stub — email sending)
- `DigSlaScheduler` (sweep + mark AtRisk/Breached)
- Tests for classifier + bypass controls

---

## 7) Deploy / validate

```bash
sf project deploy validate -o deafingov -p force-app
sf project deploy start    -o deafingov -p force-app
```

---

## 8) Next step for you
1) Decide queues (Membership/Summit/Gov/Sponsor/General) and owners.
2) Paste your desired ack tone (2–3 templates).
3) Confirm the Email-to-Case routing addresses.

Then we can harden the actions to do real owner assignment + email send.
