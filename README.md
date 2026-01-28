# DIG Ops

DIG Ops is a Salesforce-based operational spine for Deaf in Government — covering membership, events, governance, and service intake, built with SFDX for durability, transparency, and automation. 

Built to be **reproducible**, **sliceable**, and **immune to metadata sprawl**.

The vibe:
- **Small blast radius.** Deploy slices, not the universe.
- **Noisy stuff stays out.** Profiles/layouts/managed package internals don’t get to ruin your diffs.
- **UI-only changes are real.** If we do it in Setup, we write it down here.

---

## What this is (in one sentence)

**A Salesforce-first operating system for Deaf in Government** — membership, programs, fundraising, Summit events, and board motions — designed to be auditable, deployable, and automation-friendly.

---

## The world inside the org (apps you’ll actually click)

### **DIG Ops**
The day-to-day cockpit:
- members + contacts (the spine)
- programs + sponsorships
- cases / work intake
- dashboards that answer “what’s blocked?” in 10 seconds

### **Summit Events**
Your events engine:
- instances, registrations, operational status
- the place where “we’re running everything from Summit” becomes literal

### **DIG Governance**
Board-grade governance:
- motions + votes
- (optional) results certification / quorum logic
- audit trail you can show to anyone with a badge and a clipboard

---

## Design principles (the “why it feels different” section)

### 1) **Bureaucrat-proof**
Everything important is:
- explicit,
- reproducible,
- and doesn’t depend on one person’s memory.

### 2) **Metadata as source code**
If it can be versioned, it belongs in git.

### 3) **Deterministic automation**
Flows are great — until you need:
- ordering,
- bypass,
- bulk-safety,
- or a paper trail.

That’s where Apex patterns + “golden keys” come in.

### 4) **Deaf-first**
Not as a slogan — as a constraint:
- accessibility is an operational requirement, not an afterthought.

---

## Repo layout (what’s where)

> Your exact folders may vary depending on how you’ve staged DIG Ops vs Governance vs Summit,
but the intent is consistent.

- `force-app/` — source-tracked Salesforce metadata (Apex, objects, fields, etc.)
- `manifest/` — deployment packages for targeted deploys (Ops, Governance, Summit)
- `docs/` — human-readable runbooks and “why we did it” notes
- `dig-src/` (if present) — additional metadata slices (older or staged work)

---

## Getting started (deafingov org)

### Prereqs
- Salesforce CLI (`sf`)
- Authenticated target org alias: **`deafingov`**

### Validate (dry run)
```bash
sf project deploy validate -o deafingov -p force-app
```

### Deploy
```bash
sf project deploy start -o deafingov -p force-app
```

### Deploy a specific slice (example)
```bash
sf project deploy start -o deafingov --manifest manifest/governance-mvp-package.xml
```

---

## Geary Muni (apt-get for metadata slices)
Geary Muni is the repo’s slice builder + deploy wrapper. It scans package directories (typically `dig-src`), generates deterministic slice manifests, resolves dashboard→report dependencies, and lets you deploy by friendly aliases. It also includes a Recipes compiler that turns Mermaid flowcharts into deterministic Flow XML with a lockfile.

Quick summary:
- Build slices/registry: `python tools/geary/geary.py update --root .`
- List slices/aliases: `python tools/geary/geary.py list`
- Health checks: `python tools/geary/geary.py doctor --root .`
- Install a slice: `python tools/geary/geary.py install flows --target-org deafingov`
- Recipes: `python tools/geary/geary.py recipe compile --root .`
- Recipes support LWC screen components via `type: lwc` (see `geary.md`).

See `geary.md` for the full CLI reference, alias rules, and Recipes syntax.

---

## Membership Engine (Apex-first, flowless core)

Deterministic Apex automation computes membership status from `Membership__c` terms and writes a Contact “membership spine” for fast reporting. Admins adjust behavior via Custom Metadata Types (levels, grace windows, renewal notices). No Flow metadata is required for the core engine.

### Deploy (target org: `deafingov`)
```bash
sf project deploy start --target-org deafingov --manifest manifest/membership-engine-mvp-package.xml
```

### Schedule daily renewal notices (9:05 AM org time)
```apex
System.schedule('DIG Membership Daily Job', '0 5 9 * * ?', new DigOps_MembershipDailyJob());
```

### How it works (summary)
- `Membership__c` holds term history; “current term” is the non-cancelled term with the latest end date.
- Status derivation is deterministic (Active/Grace/Lapsed/Pending/Cancelled).
- Contact summary fields (`Is_Current_Member__c`, `Membership_Status_Summary__c`, etc.) are computed in Apex.
- `Is_Current_Member__c` is true only for **Active** (Grace is tracked separately).
- A daily job creates deduped renewal Tasks based on CMDT notice windows.

### Smoke test checklist
- Create a Contact.
- Create a `Membership__c` term with `StartDate__c <= today`, `EndDate__c` in the future, `Level__c = INDIVIDUAL`, and `PaidDate__c` set.
- Verify Contact summary fields update: `Membership_Status_Summary__c`, `Membership_End_Date__c`, `Current_Membership_Level__c`, `Member_Since__c`, `Membership_Last_Paid_Date__c`, `Is_Current_Member__c`.
- Change the term `EndDate__c` to yesterday and verify **Grace** (or **Lapsed** after grace window) and `Is_Current_Member__c = false`.
- Run the daily job again → Tasks are created once per notice window and do not duplicate on rerun.

---

## Membership Panel (LWC)

Staff-facing Lightning Web Component for searching Contacts, viewing membership summary, and creating renewal terms using Apex (no Flows).
Deploy uses RunSpecifiedTests due to org-wide coverage constraints; validated set: ControllerTest + ServiceTest + DailyJobTest.

### Membership Panel runbook (copy/paste)
```bash
# validate
sf project deploy validate --target-org deafingov \
  --manifest manifest/membership-panel-mvp-package.xml \
  --test-level RunSpecifiedTests \
  --tests DigOps_MembershipControllerTest \
  --tests DigOps_MembershipServiceTest \
  --tests DigOps_MembershipDailyJobTest \
  --verbose

# deploy
sf project deploy start --target-org deafingov \
  --manifest manifest/membership-panel-mvp-package.xml \
  --test-level RunSpecifiedTests \
  --tests DigOps_MembershipControllerTest \
  --tests DigOps_MembershipServiceTest \
  --tests DigOps_MembershipDailyJobTest \
  --verbose

# setup: assign permission set
sf org assign permset --target-org deafingov --name DIG_Ops_Membership
```

Setup (UI)
1) Open Lightning App Builder for the Contact Record Page.
2) Drag **digMembershipPanel** onto the page.
3) Save and activate for the desired apps/profiles.

Smoke test
- Search for a Contact and select it.
- Create a renewal term (Level + dates) and submit.
- Confirm Contact summary fields refresh and the new term appears in the table.

## The “Geary Muni” direction (why this repo has rocket fuel)

This repo is also a proving ground for **Geary Muni**:

A runner / normalizer that can:
- take “broken metadata” (or inconsistent XML),
- canonicalize it,
- and reliably deploy it through a repeatable pipeline.

Think: *CI for Salesforce metadata that behaves like grown-up software.*

If Salesforce is the city, **Geary is the street crew**:
- runners move the payload,
- cooks prep it so it won’t explode on deploy.

---

## What’s next (roadmap vibes)

- **Golden keys pipeline**: stable “seed” automations that can be generated and reused
- **Comms engine**: Email-to-Case → routing → SLA → (optional) Agentforce drafting
- **Governance results engine**: quorum/majority certification with immutable receipts
- **Summit hardening**: capacity + accessibility gates + operational checklists

---

## Contributing (even if you’re solo)

**Rules of the road:**
1) Small, named slices (manifests) beat “deploy everything” chaos
2) Add docs when you add power
3) Tests aren’t optional once automation touches money/governance/compliance

---

## Troubleshooting

### Flow deploy failures
If a Flow deploy fails with structure/metadata errors:
1) Rebuild or re-save the Flow in Flow Builder (UI)
2) Re-retrieve just the Flow + FlowDefinition
3) Validate and deploy again

### “Why isn’t X in git?”
If it’s app nav, list views, pinned items, org homepage tweaks, or managed-package behavior: it’s probably **intentionally UI-only**. Document it in this README.