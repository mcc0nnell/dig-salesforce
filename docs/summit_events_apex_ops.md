# Summit Events: Apex-First Ops Automation (Geary Cook/Runner Friendly)

**Goal:** Run Summit Events operations with **Apex as the automation spine**: deterministic status transitions, capacity enforcement, reminders, accessibility gates, and ops checklists — without relying on Flow.

This spec is written so you can:
- implement incrementally
- keep behavior configurable via Custom Metadata
- deploy/validate via CLI (and later: Geary Runner)

---

## 1) Assumptions

- You are using the **Summit Events** managed package objects (installed in your org).
- Object API names may be namespaced (e.g., `summit__Instance__c`) depending on packaging.
- We avoid hardcoding names in the **design**; implementation can be either:
  1) explicit API names (fastest), or  
  2) a lightweight “Object Map” via Custom Metadata (portable across orgs).

---

## 2) What Apex will own

### A) Event Instance lifecycle
On insert/update of an Event Instance:
- Normalize status based on dates and publication flags
- Generate/refresh a public “attendee landing URL”
- Create “ops checklist” Tasks when an instance becomes Scheduled/Open
- Compute risk flags (accessibility, capacity, missing logistics)

### B) Registration enforcement
On insert/update of a Registration:
- Confirm vs waitlist based on capacity
- Maintain attendee counts on the instance (denormalized for dashboards)
- Optionally: create follow-up Tasks (e.g., payment pending, waiver missing)

### C) Reminders + risk sweeps
Scheduled Apex:
- 24h and 1h reminders to confirmed registrants
- Accessibility “at risk” escalation if not confirmed by cutoff
- Post-event follow-up tasks (surveys, thank-you notes, member conversion)

---

## 3) Data model: minimum fields to add (if not already present)

Even if Summit provides many fields, you’ll want a consistent slice for ops.

### On Event Instance (or equivalent)
- `Ops_Status__c` (picklist): Draft, Scheduled, Open, RegClosed, Completed, Canceled
- `Capacity__c` (number)
- `Confirmed_Count__c` (number)
- `Waitlist_Count__c` (number)
- `Landing_Url__c` (URL/text)
- `Accessibility_Status__c` (picklist): NotStarted, Scheduled, Confirmed, AtRisk, Complete
- `Accessibility_Evidence__c` (URL/text)
- `Risk_Flags__c` (long text, or multiple checkboxes)

### On Registration (or equivalent)
- `Reg_Status__c` (picklist): Pending, Confirmed, Waitlisted, Canceled, NoShow
- `Reminder_24h_Sent__c` (checkbox)
- `Reminder_1h_Sent__c` (checkbox)

> If the package already has similar fields, map to them; don’t duplicate.

---

## 4) Config via Custom Metadata (portable + admin-tweakable)

Create Custom Metadata Types (CMDT) to avoid hardcoding rules.

### `Summit_Ops_Config__mdt`
Fields (examples):
- `Reminder24hHours__c` (default 24)
- `Reminder1hHours__c` (default 1)
- `AccessibilityCutoffHours__c` (default 72)
- `DefaultCapacity__c` (optional)
- `EnableHardAccessibilityGate__c` (bool)

### `Summit_Object_Map__mdt` (optional, but recommended if namespaced)
Map logical names → API names:
- Instance object API name
- Registration object API name
- Relationship field names (Instance lookup on Registration, etc.)
- Field API names for status/capacity/counts/landing URL

This lets the same code run across orgs where namespace differs.

---

## 5) Apex architecture (clean + testable)

**Pattern:** trigger → handler → service → selector

- `SummitEventInstanceTrigger` → `SummitEventInstanceHandler`
- `SummitRegistrationTrigger` → `SummitRegistrationHandler`

Services:
- `SummitLifecycleService` (status transitions, ops tasks, landing URL)
- `SummitRegistrationService` (confirm/waitlist, count maintenance)
- `SummitReminderService` (email send + flags)

Scheduler:
- `SummitOpsScheduler` implements `Schedulable`
- Optionally a `Queueable` for sending emails in batches

Selectors:
- `SummitSelectors` centralizes SOQL

---

## 6) Rules (deterministic)

### A) Status transition rules
- If canceled flag true → `Canceled`
- Else if now < start AND published/open flag true → `Open`
- Else if now < start AND scheduled flag true → `Scheduled`
- Else if end < now → `Completed`
- Else → `Draft`

### B) Capacity rules
On registration create/update:
- If Confirmed_Count < Capacity → Confirm
- Else → Waitlist
- If Capacity is null → use default capacity from config (or treat as unlimited)

### C) Accessibility gate (optional hard stop)
If `EnableHardAccessibilityGate`:
- Prevent `Open` unless accessibility status is Confirmed (or evidence present)
Else:
- Allow Open, but set `AtRisk` and auto-create a Task for the Accessibility owner

---

## 7) Dashboards the code enables (what you get immediately)

- **This Week’s Instances**: status + confirmed vs capacity + accessibility status
- **At Risk**: instances with Accessibility_Status=AtRisk OR missing evidence
- **Ops Checklist**: open Tasks created by Summit automation

---

## 8) Deployment notes (CLI / Geary Runner)

Deploy:
```bash
sf project deploy start -o deafingov -p force-app
```

Validate:
```bash
sf project deploy validate -o deafingov -p force-app
```

---

## 9) Next step: wire in your exact Summit object API names

Update:
- `SummitSchema.cls` constants, or
- implement CMDT-backed mapping

Everything else remains stable.

