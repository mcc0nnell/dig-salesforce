# DIG Salesforce: the Deaf-in-Government Control Room 🛰️

Welcome to the **DIG Salesforce** project — a practical, opinionated Salesforce org + repo that turns “we should be tracking this” into **real objects, real workflows, and real dashboards**.

This repo is built like a *field kit*:
- sturdy enough for day-to-day ops,
- clear enough for board governance,
- flexible enough to grow into **Geary Muni** (the automation runner / metadata chef).

If you’ve ever thought *“I wish our nonprofit ran like a well-instrumented system”* — this is that.

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

- `dig-src/` — primary source for DIG-owned metadata (Apex, flows, permission sets, objects)
- `manifest/` — deployment packages for targeted deploys (Ops, Governance, Summit)
- `docs/` — human-readable runbooks and “why we did it” notes
- `force-app/` — legacy/noisy metadata; avoid unless explicitly requested

---

## Getting started (deafingov org)

### Prereqs
- Salesforce CLI (`sf`)
- Authenticated target org alias: **`deafingov`**

### Validate (dry run)
```bash
make dig-validate
```

### Validate + smoke check
```
make dig-validate-smoke ORG=deafingov
```
This runs `make dig-validate` and then executes `dig-smoke-membership-join.sh`, which posts two deterministic join requests and verifies the Contact/Membership_Term/Receipt state for the smoke email. Use it after deployments to prove idempotency.

### Deploy
```bash
sf project deploy start --target-org deafingov --manifest manifest/membership-mvp-package.xml
```

### Deploy a specific slice (example)
```bash
sf project deploy start --target-org deafingov --manifest manifest/governance-mvp-package.xml
```

### Retrieve a minimal slice (example)
```bash
make dig-retrieve
```

---

## Geary Muni (apt-get for metadata slices)
Geary Muni is the repo’s slice builder + deploy wrapper. It scans package directories (typically `dig-src`), generates deterministic slice manifests, resolves dashboard→report dependencies, and lets you deploy by friendly aliases. It also includes a Recipes compiler that turns Mermaid flowcharts into deterministic Flow XML with a lockfile.

Quick summary:
- Build slices/registry: `python tools/geary/geary.py update --root .`
- Compile recipes (if `recipes/` changed): `python tools/geary/geary.py recipe compile --root .`
- List slices/aliases: `python tools/geary/geary.py list`
- Health checks: `python tools/geary/geary.py doctor --root .`
- Install a slice: `python tools/geary/geary.py install flows --target-org deafingov`
- Recipes: `python tools/geary/geary.py recipe compile --root .`
- Recipes support LWC screen components via `type: lwc` (see `geary.md`).

See `geary.md` for the full CLI reference, alias rules, and Recipes syntax.
Catalog compiler + lint gate: `bash scripts/catalog_lint.sh` (details in `docs/geary/catalog.md`). Example YAML should reference tracked manifests (avoid gitignored `manifest/slice-*.xml` files).

## Catalog
Short, human-curated index of slices + dependencies.
- Slice Index: `docs/catalog/index.md`
- How the catalog works + how to add slices: `docs/geary/catalog.md`

Catalog entries may include an optional `deploy` map (manifests/packages under `manifest/`). The lint gate validates these paths and the Slice Index surfaces them.

### Adding a new slice (quick)
- Add a new entry under `catalog/examples/` with a unique `slice.id` + `slice.number`, and reference a tracked manifest.
- Run `bash scripts/catalog_lint.sh` to generate `catalog/build/catalog.yml` + `catalog/build/catalog_report.md` and refresh `docs/catalog/index.md`.
- If it’s a real slice, refresh the registry: `python tools/geary/geary.py update --root .`.

Solaris-structured slices:
- [Org Baseline](docs/ui/org-baseline.md)
- [Ops Envelope](docs/ui/ops-envelope.md)
- [Membership MVP](docs/ui/membership-mvp.md)
- [Membership Renewal Loop](docs/ui/membership-renewal-loop.md)
- [Emissions Console](docs/ui/emissions-console.md)
- [Email Comms Runner](docs/ui/email-comms-runner.md)

```yaml
version: 1
slice:
  id: digops-05-example-slice
  number: 5
  band: services
  title: Example Slice
policy:
  deployment:
    sf_manifests:
      - manifest/membership-mvp-package.xml
```

---

## Geary CLI plugin (sf-geary)
This repo includes a TypeScript sf CLI plugin that wraps the Python Geary CLI.

Quickstart:
```bash
cd sf-geary-plugin
npm i
npm run build
node bin/run.js geary update --root ..
node bin/run.js geary doctor --root ..
```

See `sf-geary-plugin/README.md` for install and usage details.

## Geary Runner (doctor/run/replay)

Environment variables:
- `GEARY_KEY` (required for live worker calls)
- `WORKER_URL` (required for live worker calls)
- `GEARY_RUNS_DIR` (optional, default `./runs`)

Doctor (healthcheck):
```bash
python tools/geary/geary.py doctor
python tools/geary/geary.py doctor --no-network
```

Run + receipts:
```bash
python tools/geary/geary.py run --in path/to/input.mmd --format svg --out /tmp/output.svg
python tools/geary/geary.py run --stdin --format json < path/to/input.mmd
```

Runs directory layout (per run):
```
runs/<run_id>/
  receipt.json
  emissions.ndjson
  artifacts/
    input.mmd
    output.svg or output.json
```

Replay + verification:
```bash
python tools/geary/geary.py replay <run_id>
```

## Mermaid Intake — owned + bounded slice
- [Mermaid Intake — owned + bounded slice](docs/geary/mermaid-intake.md)
- Complete implementation including Apex classes, LWC component, and supporting files for Mermaid diagram intake functionality
- Cloudflare Mermaid Runner integration for diagram rendering
- Permission sets and CSP configurations for secure access
- Documentation and runbooks for deployment and usage

---

## Runbooks
- Comms schema + perms + apex + LWC deployment runbook (production-safe). See `docs/runbooks/comms-stack-deploy.md`.
- Geary comms-web deterministic install change log. See `docs/notes/geary-comms-web-change-log.md`.
- Emissions runbook — schema verification, smoke append, idempotency proof, dedupe check: see `docs/emissions-runbook.md`.

## Docs
- Emissions: see [docs/emissions-runbook.md](docs/emissions-runbook.md)

## Emissions

The emissions spine is a Platform Event bus (`DIG_Emission__e`) with a durable sink (`DIG_Emission__c`) for evidence, audit, and replay. Each envelope is hash-chained and deterministic.

- Reference: [DIG Emissions spine](docs/dig/emissions.md)
- Runbook: [Emissions runbook](docs/emissions-runbook.md)
- Quick commands:
  ```bash
  sf apex run --target-org deafingov --file /tmp/dig-emissions-smoke.apex
  sf data query --target-org deafingov -q "SELECT RunId__c, Seq__c, Type__c, PrevHash__c, Hash__c, IdempotencyKey__c, Anomaly__c FROM DIG_Emission__c WHERE RunId__c LIKE 'smoke-%' ORDER BY CreatedDate DESC LIMIT 10"
  ```

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

## What's next (roadmap vibes)

- **Golden keys pipeline**: stable "seed" automations that can be generated and reused
- **Comms engine**: Email-to-Case → routing → SLA → (optional) Agentforce drafting
- **Governance results engine**: quorum/majority certification with immutable receipts
- **Summit hardening**: capacity + accessibility gates + operational checklists
- **Emissions Spine**: append-only, hash-chained event journal for deterministic auditing

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

## License / ownership

This repo represents operational infrastructure for **Deaf in Government (DIG)**.
If you reuse patterns, awesome — just don’t reuse branding or member data.

---

## One last thing

This project is intentionally built like a *control room*.
Not flashy — **reliable**.
Not theoretical — **used**.

If you’re reading this, you’re already in the room.
