# DIG Governance Engine (Apex-first) — Spec + Build Plan

**Org alias:** `deafingov`  
**Date:** 2026-01-27  
**Goal:** Replace Flow-heavy governance automation with a deterministic, testable, accessible Apex + Custom Metadata governance “engine” that manages **Motions**, **Votes**, quorum/majority policies, time-based closes, and an auditable “decision emissions” trail.

---

## 0) Outcomes

- **Deterministic governance:** state transitions are enforced in code (no “mystery clicks”).
- **Admin knobs without Flow:** quorum + majority + eligibility policies live in **Custom Metadata Types**.
- **Bureaucrat-proof evidence:** every open/close/vote/result can emit an immutable log record.
- **Simple UI:** standard record pages + a small “Cast Vote” action (LWC preferred; Flow optional).
- **Deployable + testable:** service-based Apex with unit tests and scheduled closing jobs.

---

## 1) Canonical Object Model

> If you already have `Motion__c` and `Vote__c` installed, treat this as the normalization target. Adjust field API names to match your existing schema.

### 1.1 `Motion__c`

Required fields:
- `Title__c` *(Text)*
- `Body__c` *(Long Text Area)*
- `Status__c` *(Picklist: Draft, Open, Voting, Passed, Failed, Withdrawn, Archived)*
- `MotionType__c` *(Picklist: Bylaws, Budget, Resolution, Policy, Election, Other)*
- `OpenDateTime__c` *(DateTime, optional)*
- `CloseDateTime__c` *(DateTime, optional)*

Policy fields (stored per motion or derived from defaults):
- `EligibleVoterGroup__c` *(Picklist: Board, Members, Committee, Custom)*
- `MajorityRuleKey__c` *(Text 40: SIMPLE, TWO_THIRDS, UNANIMOUS, CUSTOM)*
- `CustomMajorityPct__c` *(Number 3,2; optional)*
- `QuorumMode__c` *(Picklist: None, FixedCount, PercentOfRoster, Custom)*
- `QuorumValue__c` *(Number 6,2; optional; count or percent depending on mode)*
- `AllowVoteChangeUntilClose__c` *(Checkbox; optional)*

Result fields (computed by Apex):
- `YesCount__c` *(Number 6,0)*
- `NoCount__c` *(Number 6,0)*
- `AbstainCount__c` *(Number 6,0)*
- `EligibleCount__c` *(Number 6,0; optional — if roster snapshot)*
- `QuorumMet__c` *(Checkbox)*
- `Result__c` *(Picklist: Passed, Failed, Incomplete)*
- `FinalizedAt__c` *(DateTime)*
- `VotingLocked__c` *(Checkbox)* — set true on close/finalize

### 1.2 `Vote__c`

Required fields:
- `Motion__c` *(Lookup → Motion__c, required)*
- `VoterContact__c` *(Lookup → Contact, required)*
- `Choice__c` *(Picklist: Yes, No, Abstain)*
- `CastAt__c` *(DateTime)*

Optional:
- `EligibilitySnapshot__c` *(Text 255)* — “Board”, “Current Member”, etc.
- `Source__c` *(Picklist: UI, Import, AdminOverride)*

**Uniqueness constraint:** one vote per motion per voter.
- Enforce with Apex and (optionally) a unique field:
  - `VoteKey__c` *(Text 100, Unique, External ID)* = `MotionId + ':' + ContactId`

### 1.3 Optional: `GovRoster__c` (eligibility snapshot)

Use this if you want “no disputes” when membership changes mid-vote.

- `Motion__c` *(Lookup)*
- `Contact__c` *(Lookup)*
- `Role__c` *(Text/Picklist)*
- `IsEligible__c` *(Checkbox)*
- `SnapshotAt__c` *(DateTime)*

### 1.4 Audit trail: `DIG_Emission__c` (append-only)

If you already created this for DIG Ops, reuse it.

Fields:
- `RecordId__c` *(Text 18)*
- `ObjectType__c` *(Text 40)*
- `Action__c` *(Text 60: MOTION_OPEN, VOTE_CAST, MOTION_CLOSE, RESULT_COMPUTED, etc.)*
- `RuleKey__c` *(Text 80)*
- `BeforeJson__c` *(Long Text Area)*
- `AfterJson__c` *(Long Text Area)*
- `Reason__c` *(Long Text Area)*
- `ActorUserId__c` *(Text 18, optional)*
- `Version__c` *(Text 40; git SHA or package version)*

---

## 2) Admin-configurable rules (Custom Metadata Types)

### 2.1 Policy defaults
**CMDT:** `DIG_GovPolicy__mdt` (single record)

Fields:
- `DefaultEligibleVoterGroup__c` *(Picklist)*
- `DefaultMajorityRuleKey__c` *(Text 40; SIMPLE)*
- `DefaultQuorumMode__c` *(Picklist; None)*
- `DefaultQuorumValue__c` *(Number 6,2; optional)*
- `DefaultAllowVoteChangeUntilClose__c` *(Checkbox; default false)*
- `AbstainCountsInDenominator__c` *(Checkbox; default false)*
- `TieBreakMode__c` *(Picklist: Fail, ChairDecides, ExtendVote; default Fail)*
- `CloseJobFrequency__c` *(Picklist: Hourly, Daily; default Hourly)*

### 2.2 Majority rule library
**CMDT:** `DIG_GovMajorityRule__mdt`

Fields:
- `RuleKey__c` *(Text 40: SIMPLE, TWO_THIRDS, UNANIMOUS)*
- `Pct__c` *(Number 4,3; e.g., 0.500, 0.667, 1.000)*
- `Description__c` *(Text 255)*

### 2.3 Notice windows (optional)
**CMDT:** `DIG_GovNoticeWindow__mdt`

Fields:
- `EventKey__c` *(Text 40: OPEN, CLOSE_24H, CLOSE_1H, CLOSED, RESULT)*
- `CreateTask__c` *(Checkbox)*
- `SendEmail__c` *(Checkbox)*
- `TemplateKey__c` *(Text 80)*

---

## 3) State Machine (enforced in Apex)

### 3.1 Allowed transitions
- `Draft` → `Open` (or `Voting`)
- `Open` → `Voting` (optional)
- `Open/Voting` → `Passed/Failed` (on close + compute)
- `Draft/Open/Voting` → `Withdrawn` (creator/admin)
- `Passed/Failed/Withdrawn` → `Archived`

### 3.2 Voting rules
- Voting allowed only when `Status__c in (Open, Voting)` and `VotingLocked__c = false`.
- Eligibility enforced in code (Board/Members/etc.).
- Uniqueness enforced (one vote per motion per voter).
- If policy allows changes: update existing vote; else reject.

### 3.3 Result computation
On close:
1. Determine **eligible roster size** (prefer roster snapshot).
2. Determine **quorum met**:
   - None → true
   - FixedCount → votes_cast >= quorum_count
   - PercentOfRoster → votes_cast >= roster * pct
3. Compute **majority**:
   - Default denominator: `Yes + No` (Abstain excluded)
   - If policy includes abstain: `Yes + No + Abstain`
4. Passed if quorum met AND yes_pct >= required_pct.

Tie handling controlled by `TieBreakMode__c`.

---

## 4) Apex Architecture

### 4.1 Triggers
- `MotionTrigger` → calls `DigGov_MotionService`
- `VoteTrigger` → calls `DigGov_VoteService`

### 4.2 Services
**`DigGov_MotionService`**
- `openMotion(Id motionId)`
- `closeMotion(Id motionId)` (locks, computes, finalizes)

**`DigGov_VoteService`**
- `castVote(Id motionId, Id voterContactId, String choice)`
  - eligibility, uniqueness, allow-change policy

**`DigGov_RosterService`** (optional)
- `snapshotRoster(Id motionId)` — freeze eligible voters at open

**`DigGov_Rules`**
- reads CMDT policy + majority rules + notice windows.

### 4.3 Scheduled close job
**`DigGov_CloseJob implements Schedulable`**
- finds motions where `CloseDateTime__c <= NOW` and `Status__c in (Open,Voting)` and not locked
- closes them via `closeMotion()`

---

## 5) Security & Permissions

Permission sets:
- `DIG_Gov_Admin`: full CRUD + overrides
- `DIG_Board_Gov`: read motions + create/update own votes
- `DIG_Member_Gov` (if members vote): read motions + create/update own votes (eligibility enforced in Apex)

Apex must enforce:
- eligibility
- one-vote rule
- open/locked status checks
- (optional) “vote only for self” guardrails

---

## 6) UI Plan (Flow-minimal)

- Standard Motion record page: status, dates, policy, vote counts, result
- Related list: Votes
- “Cast Vote” Quick Action:
  - **Preferred:** LWC buttons Yes/No/Abstain calling Apex
  - **Fallback:** tiny Screen Flow wrapper calling invocable Apex

Reports/Dashboards:
- Motions open for vote
- Motions closed this month + results
- Votes by board member

---

## 7) Unit Test Plan

Test data:
- Board contacts: 2
- Non-board contact: 1
- Motion: board-only, closes in 1 hour

Tests:
- non-board cannot vote
- board can vote
- duplicate vote rejected or updated based on policy
- close computes result correctly (simple majority)
- scheduled job closes overdue motions
- emissions logged for open/vote/close (if enabled)

---

## 8) Rollout Checklist

1. Inventory existing governance flows (if any)
2. Deploy Apex + CMDT + UI action
3. Normalize existing motions (recompute counts/results)
4. Turn on scheduled close job
5. Disable redundant flows to prevent double-processing
6. Validate audit trail + dashboards

---

## 9) CLI snippets (org alias: deafingov)

Deploy:
```bash
sf project deploy start --target-org deafingov --manifest manifest/governance-engine.xml
```

Run tests:
```bash
sf apex run test --target-org deafingov --test-level RunLocalTests --result-format human
```

Schedule close job (hourly at minute 5), run once as Anonymous Apex:
```apex
System.schedule('DIG Gov Close Job', '0 5 * * * ?', new DigGov_CloseJob());
```

---

## 10) Safe defaults

- Eligible voters: **Board**
- Majority: **Simple** (Yes/(Yes+No) >= 0.5)
- Abstain excluded from denominator
- No vote changes after cast (toggle via policy)
- Quorum off by default (enable via CMDT)

---

**End of spec.**
