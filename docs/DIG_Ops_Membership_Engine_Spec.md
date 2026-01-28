# DIG Ops Membership Engine (Apex-first) — Spec + Build Plan

**Org alias:** `deafingov`  
**Date:** 2026-01-27  
**Goal:** Replace Flow-heavy membership automation with a deterministic, testable, accessible Apex + Custom Metadata “engine” that maintains a clean **Membership Spine** (Contact summary fields), generates renewal nudges, and emits an auditable decision trail.

---

## 0) What you’ll get out of this

- **Flowless core:** Membership state transitions computed in Apex (bulk-safe).
- **Admin knobs without Flow:** durations, grace periods, renewal notice windows, and level behavior live in **Custom Metadata Types**.
- **Fast reporting:** Contact has denormalized fields (`Is_Current_Member__c`, etc.) for dashboards and list views.
- **Bureaucrat-proof audit trail:** optional append-only “emissions” log records **why** automation changed something.
- **Deployable + testable:** a clean Apex package shape with unit tests and a daily scheduled job.

---

## 1) Canonical Data Model

### 1.1 Membership term object (source of truth)

Create (or standardize) a custom object:

**`Membership__c`** (one record per membership term; keep history)

Required fields (recommended):
- `Contact__c` *(Lookup → Contact, required)*
- `StartDate__c` *(Date, required)*
- `EndDate__c` *(Date, required)*
- `Status__c` *(Picklist: Pending, Active, Grace, Lapsed, Cancelled)*  
  - *Note: This can be computed (Apex sets it) rather than edited manually.*
- `Level__c` *(Picklist or Text: e.g., Individual, Student, Sponsor, etc.)*
- `PaidDate__c` *(Date, optional)*
- `PaymentRef__c` *(Text 255, optional)* — external payment ID / Opportunity ID / invoice ID
- `Source__c` *(Picklist: Manual, Web, Import, Summit, Other)*

Optional / nice-to-have:
- `CancelledDate__c` *(Date)*
- `Notes__c` *(Long Text)*

**Rule:** We prefer **term history** (multiple `Membership__c` records over time). “Current” is derived.

---

## 2) Contact Membership Summary Fields (fast reports)

Add fields on **Contact** (denormalized summary):
- `Is_Current_Member__c` *(Checkbox)*
- `Membership_Status_Summary__c` *(Picklist or Text: Active, Grace, Lapsed, None)*
- `Current_Membership_Level__c` *(Text or Picklist)*
- `Membership_End_Date__c` *(Date)*
- `Member_Since__c` *(Date)* — earliest known membership start date (never resets)
- `Membership_Last_Paid_Date__c` *(Date, optional)*

**Principle:** These fields are **computed** by Apex and should not be manually maintained.

---

## 3) Admin-configurable rules (Custom Metadata Types)

### 3.1 Membership Level config
**CMDT:** `DIG_MembershipLevel__mdt`

Fields:
- `LevelKey__c` *(Text 80, unique; e.g., INDIVIDUAL, STUDENT, SPONSOR)*
- `DurationMonths__c` *(Number 3,0; default 12)*
- `GraceDays__c` *(Number 3,0; default 30)*
- `IsPaidRequired__c` *(Checkbox; default true)*

Notes:
- If you don’t have level differences yet, create a single record: `INDIVIDUAL` (12 months, 30 grace).

### 3.2 Renewal notice windows
**CMDT:** `DIG_MembershipNoticeWindow__mdt`

Fields:
- `WindowDaysBeforeEnd__c` *(Number 3,0)* — e.g., 30, 14, 7
- `CreateTask__c` *(Checkbox; default true)*
- `TaskSubject__c` *(Text 255; e.g., “Membership renewal due in {days} days”)*
- `TaskOwnerMode__c` *(Picklist: ContactOwner, FixedUser, Queue)*
- `TaskOwnerId__c` *(Text 18; optional — UserId/QueueId if not ContactOwner)*
- `DedupeKey__c` *(Text 100; optional — to prevent duplicates, e.g., NOTICE_30)*

### 3.3 Optional: Status policy (if you want to tweak behavior)
**CMDT:** `DIG_MembershipStatusPolicy__mdt` (single record)

Fields:
- `UseGraceStatus__c` *(Checkbox; default true)*
- `DefaultGraceDays__c` *(Number 3,0; default 30)*
- `MemberSinceResetsOnRejoin__c` *(Checkbox; default false)*

---

## 4) Deterministic Status Computation

Given a term (`StartDate`, `EndDate`, `PaidDate`, `Level` config):

### 4.1 Status derivation
- **Cancelled** if `CancelledDate` is set OR `Status__c == Cancelled`
- **Pending** if `IsPaidRequired == true` AND `PaidDate` is null AND Today >= StartDate
- **Active** if `StartDate <= Today <= EndDate` AND (paid if required)
- **Grace** if `UseGraceStatus` AND `EndDate < Today <= EndDate + GraceDays`
- **Lapsed** if `Today > EndDate + GraceDays` OR (unpaid beyond start grace policy)

### 4.2 “Current Membership” selection
For each Contact:
1. Consider all non-cancelled memberships.
2. Choose the membership with the **latest EndDate**.
3. Compute status for that membership.
4. Populate Contact summary fields accordingly.

**Member Since**:
- default: earliest `StartDate__c` across all non-cancelled memberships (never resets).

---

## 5) Apex Implementation Plan (package shape)

### 5.1 Trigger + handler
**Trigger:** `MembershipTrigger` (after insert/update/delete/undelete)
- Collect affected Contact IDs.
- Call `DigOps_MembershipService.recompute(contactIds)`.

### 5.2 Service layer (bulk-safe, single entrypoint)
**Class:** `DigOps_MembershipService`
- `public static void recompute(Set<Id> contactIds)`
  - Query memberships for contacts (only needed fields).
  - Build per-contact “current term” (latest EndDate).
  - Compute term status.
  - Update Membership__c.Status__c (optional but recommended for transparency).
  - Update Contact summary fields.
  - Emit emissions log records (optional).

### 5.3 Rules reader (Custom Metadata)
**Class:** `DigOps_MembershipRules`
- `getLevelConfig(String levelKey)`
- `getNoticeWindows()` returns list of windows sorted by days descending
- `getPolicy()` returns status policy (single record or defaults)

### 5.4 Daily scheduled job (time-based notices + overnight cleanup)
**Class:** `DigOps_MembershipDailyJob implements Schedulable`
- Finds contacts with current membership end dates matching notice windows:
  - e.g., `Membership_End_Date__c = TODAY + 30`
- Creates renewal Tasks (deduped).
- Optionally calls `recompute()` for contacts whose terms crossed boundary (end/grace).

**Schedule recommendation:** daily at 9:05 AM local org time.

### 5.5 Optional: Emissions log (audit trail)
Custom object:
**`DIG_Emission__c`**
- `RecordId__c` *(Text 18)*
- `ObjectType__c` *(Text 40)*
- `Action__c` *(Text 60: MEMBERSHIP_RECOMPUTE / NOTICE_TASK_CREATE / etc.)*
- `RuleKey__c` *(Text 80; e.g., LevelKey or NoticeWindow key)*
- `BeforeJson__c` *(Long Text Area)*
- `AfterJson__c` *(Long Text Area)*
- `Reason__c` *(Long Text Area)*
- `Version__c` *(Text 40; git SHA or package version)*

**Class:** `DigOps_Emissions`
- `emit(action, recordId, beforeMap, afterMap, reason, ruleKey)`

---

## 6) Dedupe strategy for renewal Tasks

**Task fields**:
- `WhoId` = Contact Id
- `Subject` includes window marker: e.g., `[NOTICE_30] Membership renewal due in 30 days`
- `ActivityDate` = Today
- `Status` = Not Started
- `Priority` = Normal

**Dedupe**:
- Query for existing open Tasks for WhoId with Subject containing `[NOTICE_XX]` created in last N days (e.g., 60).
- Skip if found.

---

## 7) Unit Test Plan (minimum viable)

Create a test data factory:
- Contact A: term active
- Contact B: term ended yesterday (grace)
- Contact C: term ended 45 days ago (lapsed)
- Contact D: two terms (pick latest end date)
- Contact E: unpaid, paid-required policy → pending

Assertions:
- Contact summary fields set correctly.
- Membership statuses computed and persisted (if you persist them).
- Daily job creates exactly one task per window and dedupes properly.

Coverage targets:
- `DigOps_MembershipService` core logic
- `DigOps_MembershipDailyJob` task creation + dedupe
- `DigOps_MembershipRules` defaults if CMDT missing

---

## 8) Rollout Checklist (safe migration off Flow)

1. **Inventory existing membership flows**
   - Identify what they do: summary fields, tasks, emails, etc.
2. **Disable only the parts you’re replacing**
   - Keep any UI pieces (screen flows) if they exist.
3. **Deploy Apex + CMDT + fields**
4. **Backfill Contact summary fields**
   - Run an anonymous apex script (or a one-time batch) to recompute all Contacts.
5. **Turn on scheduled job**
6. **Observe for 1–2 weeks**
   - Validate dashboard counts, renewal tasks volume, and edge cases
7. **Delete or retire flows**
   - When confident, remove Flow logic to prevent double-running.

---

## 9) CLI snippets (org alias: deafingov)

Authenticate (if not already):
```bash
sf org login web --alias deafingov
```

Deploy metadata (example manifest approach):
```bash
sf project deploy start --target-org deafingov --manifest manifest/membership-engine.xml
```

Run tests:
```bash
sf apex run test --target-org deafingov --test-level RunLocalTests --result-format human
```

---

## 10) Assumptions (safe defaults)

- Default membership duration: **12 months**
- Default grace: **30 days**
- Notice windows: **30 / 14 / 7 days**
- Member Since: earliest known non-cancelled start date; does not reset on rejoin

If any of these differ, tweak CMDT rather than logic.

---

## 11) Next “surprise me” enhancements (optional)

- **Business hours–aware due dates** (SLA) for membership issues
- **Email notifications** via Email Alerts or Messaging.SingleEmailMessage
- **Einstein / Agentforce hooks** (later) to summarize membership health
- **14ten-style evidence packs**: monthly export of membership transitions and notices

---

### Appendix A — Suggested naming conventions

- Apex classes: `DigOps_MembershipService`, `DigOps_MembershipRules`, `DigOps_MembershipDailyJob`, `DigOps_Emissions`
- CMDT records:
  - Levels: `INDIVIDUAL`, `STUDENT`, `SPONSOR`
  - Notice windows: `NOTICE_30`, `NOTICE_14`, `NOTICE_7`

---

**End of spec.**
