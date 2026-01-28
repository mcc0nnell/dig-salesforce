# DIG Governance Slice (Board + Member)

> Purpose: a durable, version-controlled governance system inside Salesforce for **board motions** and **member motions**, with clear eligibility rules, auditability, and reproducible automation.

## Principles

- **Primitives over “apps”**: Motions + Votes are the core.
- **Approvals for gates, not ballots**: Approval Processes can authorize opening/closing/certifying, but **member voting** is implemented with `Vote__c` records.
- **Eligibility is deterministic**: only *eligible, active* voters can vote; one vote per voter per motion.
- **Everything is auditable**: who proposed, who approved to open, who voted, and the computed outcome.

---

## Data Model

### Object: `Motion__c`

Represents a proposal (board lane or member lane) that can be opened for voting and closed with an outcome.

**Key fields (MVP):**
- `Name` (Motion Title) — Text (standard)
- `Description__c` — Long Text Area
- `Motion_Type__c` — Picklist: `Board`, `Member`
- `Status__c` — Picklist: `Draft`, `Submitted`, `Open`, `Closed`, `Certified`, `Withdrawn`
- `Sponsor_Contact__c` — Lookup(Contact)
- `Open_Date__c` — Date/Time
- `Close_Date__c` — Date/Time
- `Result__c` — Picklist: `Passed`, `Failed`, `No Quorum`, `Pending` (optional)
- `Quorum_Type__c` — Picklist: `Board`, `Members`
- `Quorum_Number__c` — Number (integer)
- `Pass_Threshold__c` — Picklist: `Simple Majority`, `Two-Thirds`, `Custom Percent` (optional MVP: just Simple Majority)
- **Tally fields (optional but recommended for ops)**:
  - `Yes_Count__c` — Number
  - `No_Count__c` — Number
  - `Abstain_Count__c` — Number
  - `Total_Votes__c` — Number
  - `Eligible_Voter_Count__c` — Number (optional; can be derived later)

**Notes**
- `Motion_Type__c` drives lane behavior:
  - **Board** motions: voters must be board-eligible.
  - **Member** motions: voters must be membership-eligible.

---

### Object: `Vote__c`

A single ballot cast by one voter for one motion.

**Key fields (MVP):**
- `Motion__c` — Lookup(Motion__c) **(required)**
- `Voter_Membership__c` — Lookup(Membership__c) **(required)**  
  - Use this as the voter identity so eligibility is based on membership status/tier.
- `Vote__c` — Picklist: `Yes`, `No`, `Abstain` **(required)**
- `Cast_At__c` — Date/Time (set automatically)

**Uniqueness rule (required):**
- One vote per voter per motion.
  - Enforce via **before-save flow** (fast field updates) or validation + unique key strategy.

---

## Voter Eligibility (Board + Member)

### Membership prerequisites
Assume `Membership__c` exists and already has:
- `Status__c` (Active/Lapsed)
- `StartDate__c`, `EndDate__c`

Add (or reuse) eligibility flags:
- `Voting_Eligible__c` (Checkbox) — for member lane (optional if “Active = eligible”)
- `Is_Board__c` (Checkbox) or `Role__c` (Picklist) — for board lane

**Eligibility rules (MVP default):**
- **Member motion** voter is eligible if:
  - `Membership__c.Status__c = "Active"` AND (optional) `Voting_Eligible__c = TRUE`
- **Board motion** voter is eligible if:
  - `Membership__c.Status__c = "Active"` AND `Is_Board__c = TRUE`

---

## Automation (Flows)

### 1) `DIG_Vote_OnCreate` (Record-Triggered, before-save) — **critical guardrails**

**Object:** `Vote__c`  
**Trigger:** “A record is created”  
**Optimize:** Fast Field Updates (before-save)

**Responsibilities**
- Set `Cast_At__c = $Flow.CurrentDateTime` if blank
- Block invalid votes by adding errors:
  - Motion must be `Status__c = "Open"`
  - Voter membership must be Active
  - Voter must be eligible for the motion type
  - No existing vote for the same `(Motion__c, Voter_Membership__c)`

**Implementation hints**
- Use a **Get Records** to find existing votes for same Motion + Voter. If found → add error.
- Add error messages that are user-friendly (“Voting is closed for this motion.”, “You have already voted.”).

---

### 2) `DIG_Motion_OnOpenClose` (Record-Triggered, after-save)

**Object:** `Motion__c`  
**Trigger:** “A record is updated”  
**When to run:** Only when `Status__c` changes OR `Close_Date__c` changes (reduce noise)

**Responsibilities**
- When Status becomes `Open`:
  - set `Open_Date__c` if blank
  - ensure `Close_Date__c` is set (admin requirement; or default window)
- When Status becomes `Closed`:
  - compute outcome (MVP: Simple Majority + Quorum)
  - set `Result__c`
- Add a **Scheduled Path** at `Close_Date__c`:
  - automatically set Status to `Closed` (and then compute outcome)

**Outcome logic (MVP)**
- Tally votes (Yes/No/Abstain) for this motion
- `Total_Votes = Yes + No + Abstain`
- If `Total_Votes < Quorum_Number__c` → `Result__c = "No Quorum"`
- Else if `Yes > No` → `Result__c = "Passed"`
- Else → `Result__c = "Failed"`

> Later: add thresholds (2/3, custom percent) without changing the model.

---

## Approvals (Salesforce Approval Process)

Use Approval Processes as **gates** (who is allowed to open/close/certify), not for mass voting.

### Board lane (recommended)
Approval Process on `Motion__c`:
- Entry criteria: `Motion_Type__c = "Board"` AND `Status__c = "Draft"`
- Steps: route to Board approvers (or role/group)
- Outcomes:
  - Approved: set `Status__c = "Open"` (or "Submitted" then manual Open)
  - Rejected: set `Status__c = "Withdrawn"` or keep Draft with feedback

### Member lane (optional gate)
Approval Process on `Motion__c`:
- Entry criteria: `Motion_Type__c = "Member"` AND `Status__c = "Draft"`
- Purpose: board/admin certifies ballot language before opening member voting

---

## Security & Access (Permission Sets)

### Permission Sets
- `DIG_Gov_Admin`
  - Full access to Motion/Vote
  - Can open/close/certify motions
- `DIG_Board_Gov`
  - Create board motions
  - Submit for approval / open (depending on process)
  - View all votes for board motions
- `DIG_Member_Gov`
  - Read member motions
  - Create Vote__c
  - Read own votes (optional) / Read all votes (usually **no**)

### Sharing model (MVP)
- Motion__c:
  - Member motions readable by members (org-wide read or criteria-based sharing)
  - Board motions restricted to board/admin
- Vote__c:
  - Private by default; members can read only their own (optional)
  - Board/admin can read for certification/audit

> Exact sharing approach depends on your org’s OWD and licensing; start conservative.

---

## Reports (Versionable “Ops Views”)

Because list views can be UI-only, use **Reports/Dashboards** for versioned governance views.

Suggested reports (folder: `DIG Governance`)
- Open Motions (Board)
- Open Motions (Member)
- Motions Closed Last 30 Days
- Votes by Motion (for certification)

Suggested dashboard
- Active Board Motions
- Active Member Motions
- Pass/Fail counts (30/90 days)
- Upcoming close dates

---

## Deployment Slice (SFDX)

Create a dedicated manifest:

`manifest/governance-mvp-package.xml` should include:
- `CustomObject`: `Motion__c`, `Vote__c`
- `CustomField`: included fields
- `Flow` / `FlowDefinition`: governance flows
- `PermissionSet`: governance permsets
- (Optional) `ApprovalProcess`, `Report`, `Dashboard`

---

## Build Order (Practical)

1) Create `Motion__c` + fields
2) Create `Vote__c` + fields
3) Add Membership voter flags (`Voting_Eligible__c`, `Is_Board__c` / `Role__c`)
4) Build `DIG_Vote_OnCreate` guardrail flow
5) Build `DIG_Motion_OnOpenClose` with scheduled close
6) Add Approval Process for Board lane
7) Create 2–4 reports and (optional) dashboard
8) Retrieve into `dig-src`, commit with tight manifests

---

## MVP Definition of Done

- A board motion can be drafted → approved to open → voted → closed → outcome computed.
- A member motion can be drafted → opened → voted by active eligible members → auto-closed on schedule → outcome computed.
- No duplicate votes; ineligible voters are blocked with clear error messages.
- Governance metadata is version-controlled (objects/fields/flows/permsets + manifests).
