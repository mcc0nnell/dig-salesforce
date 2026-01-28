# Deaf‑First Meeting Intelligence + Compliance Ledger (ACA + Moltbot + Geary + Stokoe + 14ten)

**Purpose:** Convert live meetings into **verifiable, searchable, Salesforce‑native decision records** with **accessibility and governance checks**.

This document is a practical use case blueprint you can implement incrementally (starting with a single meeting stream and a minimal Salesforce object slice).

---

## 1) Problem statement

Organizations routinely lose decision provenance:

- Verbal approvals happen in meetings, but the *record* is informal (email recollections, ad hoc notes).
- Accessibility is assumed rather than measured (captions may be missing, late, or inaccurate).
- When escalations happen, leadership asks: **who approved what, when, with what authority, and was the process accessible?**

**Goal:** Produce an authoritative, evidence-backed timeline of meeting decisions that survives:
- staff turnover  
- leadership changes  
- “rewritten history”  
- audits and accessibility inquiries  

---

## 2) Scope

### In scope
- Meeting capture (audio + timing + segments)
- Near‑real‑time transcript and speaker segmentation
- Normalized “emissions” (events) with evidentiary links
- Salesforce record creation (Decisions / Actions / Motions as needed)
- 14ten evaluation of accessibility + procedural validity
- Dashboarding (risk and status)

### Out of scope (initial)
- Full diarization perfection (speaker ID can start as “Speaker A/B”)
- Long-term raw audio retention policy decisions (can start with short retention)
- Automated enforcement actions (start with warnings/flags)

---

## 3) Actors and roles

- **Meeting participants:** people speaking / signing / chatting.
- **Facilitator:** starts/ends meeting; identifies agenda items.
- **Ops lead (you):** owns the canonical timeline, exports, and escalation responses.
- **System components:**
  - **Moltbot gateway** (sensor capture & ingestion)
  - **Stokoe** (captioning + segmentation + semantic event framing)
  - **Geary Muni** (normalizer/bridge to Salesforce objects + metadata)
  - **14ten** (policy + compliance evaluation, evidence packaging)
  - **Salesforce** (system of record + dashboard + governance objects)

---

## 4) Data flow (end‑to‑end)

1. **Capture**
   - Moltbot captures meeting audio stream + timestamps (optionally chat events).
2. **Transcription / segmentation**
   - Stokoe produces transcript segments with timestamps and speaker labels.
3. **Normalization**
   - Geary converts segments into a canonical event model (“emissions”).
4. **Persistence**
   - Emissions are written to an append‑only store (log) and to Salesforce objects.
5. **Evaluation**
   - 14ten runs checks on accessibility and process integrity.
6. **Surface**
   - Salesforce dashboards show decisions, action items, and compliance status.

---

## 5) Canonical event (“emission”) model

A minimal event schema (illustrative):

```json
{
  "event_type": "decision.approval",
  "occurred_at": "2026-01-27T20:13:07-05:00",
  "meeting_id": "mtg_2026_01_27_ops",
  "speaker": "E",
  "text": "Approved temporary bridge until May while vendor solution implemented.",
  "confidence": 0.91,
  "evidence": {
    "audio_segment_uri": "blob://meetings/mtg_.../seg_392.wav",
    "transcript_segment_id": "seg_392"
  },
  "jurisdiction": "US",
  "accessibility_context": {
    "captions_active": true,
    "caption_latency_ms": 450
  }
}
```

**Design note:** keep the emission append‑only and immutable; create derived records (Salesforce objects) as projections.

---

## 6) Salesforce projection (minimal object map)

Start with three record types. You can grow later.

### A) Decision__c (or Case Comment / Custom Object)
Fields (suggested):
- **Title**
- **Decision_Type** (Approval, Rejection, Deferral, Scope Change, Funding, etc.)
- **Owner/Approver** (lookup to User/Contact)
- **Effective_Date**
- **Effective_Until**
- **Status** (Draft, Verified, Disputed, Superseded)
- **Source_Meeting_Id**
- **Evidence_Link** (URL / File / External object)
- **Transcript_Excerpt** (short text)
- **Confidence**
- **14ten_Result** (pass/fail + reason)

### B) ActionItem__c (or Task)
Fields:
- **Assigned_To**
- **Due_Date**
- **Source_Decision**
- **Source_Meeting_Id**
- **Evidence_Link**
- **Status** (Open, In Progress, Done, Blocked)

### C) Meeting__c (or Event)
Fields:
- **Start/End**
- **Participants**
- **Captions_Enabled** (boolean)
- **Caption_Quality_Score** (numeric)
- **Transcript_Link**
- **14ten_Accessibility_Status**

---

## 7) 14ten checks (initial rule set)

### Accessibility checks
- Captions enabled for the full meeting duration (or within a defined threshold).
- Caption latency within acceptable bounds (configurable).
- Transcript availability persisted for required retention window.

### Process integrity checks
- Decision record must link to evidence.
- If governance applies: quorum present, notice met, vote recorded (when applicable).
- If policy requires: confirm “approved by” is a recognized role.

Output:
- **PASS** with metrics
- **FAIL** with specific missing evidence or procedural issue
- **WARN** for low confidence / speaker ambiguity

---

## 8) ACA deployment shape

### Components
- **moltbot-gateway** (HTTP ingress, exposes port 18789 by default)
- Optional: **worker** (background processing) if you split transcription/evaluation

### Configuration
- Use **ACA environment variables** for tokens and config (stateless containers).
- Store secrets in **Key Vault** when ready.
- For persistence:
  - keep raw audio retention minimal at first, or
  - mount **Azure Files** if you need durable storage.

### Networking
- Start with **external ingress** for testing.
- Move to internal + fronted by an API gateway once stabilized.

---

## 9) Minimal rollout plan (2 weeks)

### Phase 0 (Day 1–2): Proof
- One meeting stream
- Transcript segments + timestamps
- Write a single “Decision__c” record manually from an emission

### Phase 1 (Day 3–7): Projection
- Automate creation of:
  - Meeting__c
  - Decision__c
  - ActionItem__c (optional)
- Link evidence (transcript segment ID + short excerpt)

### Phase 2 (Day 8–14): 14ten evaluation
- Add accessibility checks (captions present + latency)
- Add dashboards:
  - “Meetings missing captions”
  - “Decisions without evidence”
  - “Unverified approvals”

---

## 10) Acceptance criteria (MVP)

A meeting produces, within 5 minutes of occurrence:
- Meeting__c record in Salesforce
- Transcript link and timestamps
- At least one Decision__c record with:
  - evidence link
  - transcript excerpt
  - 14ten accessibility result (pass/warn/fail)

And you can answer, from Salesforce alone:
- **who** approved the temporary bridge  
- **when** it was approved  
- **where** the evidence lives  
- **whether** accessibility requirements were met  

---

## 11) Risks and mitigations

- **Speaker identity ambiguity**
  - Mitigation: start with “Speaker A/B”; add speaker mapping later.
- **Retention/privacy**
  - Mitigation: short retention; store only derived text + hashes initially.
- **False positives on “decision detection”**
  - Mitigation: require a facilitator keyword or “decision marker” workflow at first.
- **Tooling drift**
  - Mitigation: freeze emission schema; version it (v1, v2).

---

## 12) Next expansions (after MVP)

- Automated Motion/Vote drafting for DIG Governance objects
- SLA dashboards for accessibility compliance (per meeting, per organizer, per program)
- Export packs for audits (evidence bundle + timeline)
- Integration into your emissions engine (append-only log + replayable projections)

---

## Appendix A: “Decision markers” (practical hack)

To reduce misclassification, have the facilitator say:
- “Decision:” (then statement)
- “Action item:” (then assignment)

Stokoe/Geary can treat those as deterministic triggers in early iterations.

