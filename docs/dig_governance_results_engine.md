# DIG Governance Results Engine (Apex)

**Goal:** Make board governance deterministic and bureaucrat-proof:
- majority/quorum computed in code
- votes locked at close
- immutable “official result” record produced (audit trail)
- repeatable + testable

This scaffold assumes you already have `Motion__c` and `Vote__c` objects (from your Governance MVP).
It introduces `Motion_Result__c` for immutable results.

---

## 1) Objects

### Motion__c (existing)
Required fields (expected):
- `Status__c` (Draft, Open, Closed, Canceled)
- `Open_At__c` (Datetime)
- `Close_At__c` (Datetime)
- `Eligible_Voters__c` (Number) — or derive from board roster
- `Quorum__c` (Percent or Number) — config-driven
- `Result_Status__c` (None, Pending, Certified)

Optional:
- `Allow_Abstain__c` (Checkbox)

### Vote__c (existing)
Required fields:
- `Motion__c` (Lookup)
- `Voter__c` (Lookup to Contact/User)
- `Choice__c` (Yes/No/Abstain)
- `Cast_At__c` (Datetime)
- `Is_Locked__c` (Checkbox)

### Motion_Result__c (new)
Fields:
- `Motion__c` (Lookup, unique)
- `Certified_At__c` (Datetime)
- `Certified_By__c` (Lookup User)
- `Yes_Count__c`, `No_Count__c`, `Abstain_Count__c`
- `Total_Cast__c`
- `Eligible_Voters__c`
- `Quorum_Required__c`
- `Quorum_Met__c` (Checkbox)
- `Majority_Required__c` (Text / e.g., "Simple")
- `Passed__c` (Checkbox)
- `Decision__c` (Text: Passed/Failed/No Quorum)
- `Result_Digest__c` (Text 64) — SHA-256 digest of canonical result payload
- `Canonical_Payload__c` (Long Text) — JSON string used to compute digest

Immutability approach:
- After insert, block updates/deletes via trigger (except by System/Admin if you allow).

---

## 2) Deterministic rules

### Quorum
Default: quorum is met if `Total_Cast >= ceil(Eligible_Voters * quorumPct)`.

### Majority (simple)
If quorum met:
- `Passed = Yes_Count > No_Count` (abstain excluded from majority)
Else:
- `Decision = "No Quorum"`

You can extend to:
- supermajority
- veto roles
- weighted votes

---

## 3) Engine flow

1) Motion is Open with a Close_At
2) Votes are cast (create Vote__c)
3) When motion closes (Close_At passed or status set Closed):
   - lock all votes (Is_Locked__c = true)
   - compute result
   - insert Motion_Result__c with digest
   - set Motion.Result_Status__c = Certified

---

## 4) Scheduling

`DigMotionCloseScheduler` runs hourly:
- finds Open motions whose Close_At <= now
- sets status Closed
- triggers certification

---

## 5) Included Apex

- `DigGovernanceSchema` (API names)
- `DigMotionResultService` (tally + digest + certification)
- `DigMotionCloseScheduler` (auto-close)
- Triggers:
  - `Motion__c` after update: on transition to Closed → certify
  - `Vote__c` before update: prevent edits when locked
  - `Motion_Result__c` before update/delete: prevent tampering

---

## 6) Deploy / validate

```bash
sf project deploy validate -o deafingov -p force-app
sf project deploy start    -o deafingov -p force-app
```

---

## 7) Next hardening steps
- derive Eligible_Voters from DIG board roster object/permission set
- add “one vote per voter per motion” constraint (unique external id)
- add UI: Motion record page shows live tally and certified result
