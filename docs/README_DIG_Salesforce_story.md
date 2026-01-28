# DIG Salesforce: the Deaf-in-Government Control Room 🛰️

Welcome to the **DIG Salesforce** project — a practical, opinionated Salesforce org + repo that turns “we should be tracking this” into **real objects, real workflows, and real dashboards**.

This repo is built like a *field kit*:
- sturdy enough for day-to-day ops,
- clear enough for board governance,
- flexible enough to grow into **Geary Muni** (the automation runner / metadata chef).

If you’ve ever thought *“I wish our nonprofit ran like a well-instrumented system”* — this is that.

---

## What this is (in one sentence)

**A Salesforce-first operating system for Deaf in Government** — membership, programs, Summit events, and board motions — designed to be auditable, deployable, and automation-friendly.

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

## License / ownership

This repo represents operational infrastructure for **Deaf in Government (DIG)**.
If you reuse patterns, awesome — just don’t reuse branding or member data.

---

## One last thing

This project is intentionally built like a *control room*.
Not flashy — **reliable**.
Not theoretical — **used**.

If you’re reading this, you’re already in the room.
