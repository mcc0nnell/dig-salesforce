# Integrating Salesforce with LimeSurvey for Governance Voting
_A governance-grade design that supports **secret ballots for elections** and **attributed ballots for board votes**._

---

## 1) Ballot modes (non-negotiable boundary)

### A. Elections — **Secret ballot**
Goal: **prove eligibility + participation + certified totals** without ever being able to answer “who voted for what.”

**Salesforce MAY store**
- Eligibility snapshot reference (criteria + hash + timestamp)
- Token issuance records (**token hashes**, not raw tokens)
- Participation receipts (token used, time received, verification status)
- Certified aggregate results (counts) + certification artifacts (hashes, sign-off)

**Salesforce MUST NOT store**
- Vote selections / answer payloads
- Response IDs or any joinable reference that can link identity to selections
- Raw response exports in a place admins can join to token mapping

**LimeSurvey configuration intent**
- Closed survey mode (token required)
- Single-use tokens (enforced via token table / uses left)
- Responses anonymized for elections

### B. Board votes — **Attributed ballot**
Goal: **recordkeeping and accountability** (identity linked to selections).

**Salesforce MAY store**
- Vote content (selections), linked to Contact/User
- Timestamps, revisions (if allowed), and audit artifacts

---

## 2) Salesforce data model (minimal + dispute-proof)

### Ballot__c
- **Type__c**: `ElectionSecret` | `BoardAttributed`
- **LsSurveyId__c**: LimeSurvey survey ID
- **Open__c / Close__c**
- **EligibilityRule__c**: text/JSON describing criteria
- **EligibilitySnapshotHash__c**
- **Status__c**: Draft / Open / Closed / Certified

### VoterAccess__c (one per voter per ballot)
For both modes, but **especially** elections.

- **Ballot__c** (lookup)
- **Contact__c** (lookup)
- **TokenHash__c** (e.g., SHA-256 hex)
- **TokenIssuedAt__c**
- **InviteSentAt__c**
- **VoteReceiptAt__c** (receipt timestamp)
- **ReceiptId__c** (correlation ID)
- **VerifiedEligibleAtCast__c** (+ timestamp)
- **Notes__c** (dispute notes)

> For secret ballots, this is your “who voted” ledger **without** vote content.

### Vote__c (**board votes only**)
Only create Vote__c when **Type__c = BoardAttributed**.

- **Ballot__c** (lookup)
- **Contact__c** (lookup)
- **Selection__c** (or child VoteChoice__c records)
- **CastAt__c**
- **Source__c** (LimeSurvey)
- **IntegrityHash__c** (hash of canonical vote payload)

### CertificationArtifact__c (both modes)
Store hashes and pointers to immutable artifacts (exports, computations, sign-off).

- **Ballot__c** (lookup)
- **ArtifactType__c**: EligibilitySnapshot / TokenBatch / FinalExport / ResultsComputation / Signoff
- **Hash__c**
- **StoragePointer__c** (where artifact is stored)
- **CreatedBy__c / CreatedAt__c**

---

## 3) Integration behavior by mode

### A. Elections (secret) — safest pattern
**Do NOT push response content to Salesforce in real time.**  
Only push a *participation receipt*.

#### Completion callback / webhook (receipt-only)
Payload should be limited to:
- surveyId
- token (or preferably token hash)
- completedAt
- minimal metadata (NO answers)

Salesforce action:
1. Look up **VoterAccess__c** by **TokenHash__c**
2. Set **VoteReceiptAt__c**
3. Set **VerifiedEligibleAtCast__c** based on eligibility snapshot (issuance-time or cast-time policy)

#### Results at close (certification)
1. Export responses from LimeSurvey to a controlled store (NOT Salesforce)
2. Compute aggregates (counts) from export
3. Write only aggregates into Salesforce (**Ballot__c** and **CertificationArtifact__c**)
4. Store **export hash** + **results hash** + signoff, then lock certification

### B. Board votes (attributed) — real-time OK
Webhook payload may include selections/answers.

Salesforce action:
1. Validate token/eligibility (per ballot rule)
2. Upsert **Vote__c** (Contact linked)
3. Store **IntegrityHash__c**
4. Optionally store LimeSurvey response id for traceability

---

## 4) Emissions engine as the audit spine (recommended)

Treat emissions as your tamper-evident “court transcript” and evidence pack generator.

### Common events (both modes)
- `BallotCreated`
- `EligibilitySnapshotTaken` (criteria + snapshot hash)
- `TokenIssued` (ballotRef, contactRef, tokenHash)
- `InviteSent`
- `BallotOpened`
- `BallotClosed`

### Elections-only (secret)
- `VoteReceiptRecorded` (**tokenHash only**, no selections)
- `FinalExportCaptured` (exportHash + storagePointer)
- `ResultsComputed` (resultsHash + totals)
- `CertificationLocked` (officer + timestamp)

### Board-only (attributed)
- `VoteCast` (contactRef + ballotRef + selection payload or selectionHash)
- `VoteAmended` (if allowed)
- `CertificationLocked`

---

## 5) Anti-deanonymization guardrails (must-have)

1. **Never store raw tokens in logs.**  
   Hash tokens at issuance and use the hash everywhere internally.

2. **Prevent correlation via timestamps.**  
   For high-scrutiny elections, round receipt timestamps (e.g., minute granularity) in Salesforce/emissions.

3. **Don’t persist joinable identifiers.**  
   In secret ballots, do not store LimeSurvey response IDs or anything that can reconnect token → response.

4. **Separate artifact storage.**  
   Keep raw exports in a restricted store; Salesforce stores only hashes + pointers + aggregates.

---

## 6) Operational workflow

### Phase 1 — Ballot provisioning
1. Create **Ballot__c** (Type decides behavior)
2. Capture eligibility rules into **EligibilityRule__c**
3. Create/activate survey and token table in LimeSurvey
4. Store LimeSurvey Survey ID in **LsSurveyId__c**

### Phase 2 — Eligibility snapshot + token issuance
1. Query eligible members in Salesforce
2. Produce eligibility snapshot → store hash in **EligibilitySnapshotHash__c** + **CertificationArtifact__c**
3. Issue tokens in LimeSurvey
4. Create **VoterAccess__c** rows with **TokenHash__c** (no raw token stored)
5. Send invite links containing raw token **only in the outbound message**

### Phase 3 — Voting
- Elections: receipt-only callback updates **VoterAccess__c**
- Board votes: full callback writes **Vote__c**

### Phase 4 — Close + certification
- Elections: export → compute aggregates → store hashes + counts → **Certified**
- Board: tally from **Vote__c** → store artifacts → **Certified**

---

## 7) Quick checklist

- [ ] Ballot__c.Type__c set correctly (ElectionSecret vs BoardAttributed)
- [ ] EligibilitySnapshotHash captured and stored
- [ ] Tokens hashed everywhere internally
- [ ] Secret ballots: webhook is **receipt-only**
- [ ] Raw exports stored outside Salesforce; Salesforce stores hashes + aggregates
- [ ] Certification locks records and emits `CertificationLocked`

---

_This document is designed so secret ballots remain secret even under admin access, while preserving auditability and dispute resolution._
