# Geary Golden Keys on Salesforce Scratch Orgs (Automated Pipeline)

**Goal:** Fully automate a “golden key” library for Salesforce Flows using **scratch orgs**:
- create scratch org
- deploy minimal golden Flow templates
- retrieve them back into the repo
- canonicalize + lock (hash + API version)
- seed any target org idempotently

This avoids hand-authoring Flow XML while keeping artifacts deterministic and auditable.

---

## 1) Core idea: keys are *retrieved*, not invented

Flow XML is sensitive to org features and API version. The safest automation is:

1) **Deploy** minimal templates into a clean scratch org  
2) **Retrieve** the Salesforce-generated metadata  
3) Treat that retrieved metadata as the **canonical golden key**

---

## 2) Repository layout (recommended)

```
geary-golden/
  config/
    project-scratch-def.json
  golden/
    flows/                      # locked golden Flow XML lives here
  manifest/
    golden-keys.xml             # deploy manifest (Flow members)
  scripts/
    golden-init.sh              # creates scratch org and prepares it
    golden-refresh.sh           # deploys keys → retrieves → locks hashes
    geary-seed.sh               # deploys keys into any target org (idempotent)
    geary-doctor.sh             # checks whether keys exist in an org
  golden.lock.json              # hashes + version stamp
  Makefile
```

**Note:** This repo can be standalone, or you can embed it inside your main DIG repo as `tools/geary-golden/`.

---

## 3) Scratch org definition (minimal)

`config/project-scratch-def.json`:

```json
{
  "orgName": "Geary Golden Keys",
  "edition": "Developer",
  "features": [],
  "settings": {
    "orgPreferenceSettings": {
      "s1DesktopEnabled": true
    }
  }
}
```

---

## 4) The golden key set (baseline)

Start with **three** minimal Flows (same names across orgs):

- `Golden_RTF_Min` (Record-Triggered Flow)
- `Golden_Screen_Min` (Screen Flow)
- `Golden_Sched_Min` (Scheduled flow or scheduled-path pattern)

You can add more later, but these three cover most “Flow-class” shapes.

---

## 5) Automation scripts (what each does)

### A) `golden-init` (create scratch org)
- creates scratch org with a stable alias
- sets it as default for subsequent commands
- (optional) installs packages or applies org settings you need for templates

### B) `golden-refresh` (regenerate the keys)
- deploys *your* key package (or key scaffolding) into scratch org
- retrieves Flow metadata back into `golden/flows/`
- writes `golden.lock.json` with:
  - API version used
  - SHA256 hashes for each key file
  - timestamp

### C) `geary-doctor` (check keys in an org)
- checks that FlowDefinitions exist by DeveloperName

### D) `geary-seed` (idempotently seed a target org)
- runs doctor
- deploys keys if missing
- re-checks doctor

---

## 6) Make targets

Typical usage:

```bash
make golden-init
make golden-refresh
make geary-doctor ORG=deafingov
make geary-seed ORG=deafingov
```

---

## 7) Important operational notes

### “Deploy then retrieve” is intentional
Your repo should treat `golden/flows/*.flow-meta.xml` as the **source of truth** for seeding other orgs.

### Use hashes as the audit primitive
`golden.lock.json` makes it easy to prove:
- which “key” version produced which generated Flow
- whether a key changed unexpectedly

### Keep the keys tiny
Minimal keys reduce drift and future breakage.

---

## 8) Suggested next step: Geary wrapper commands

Once this pipeline exists, Geary can assume keys exist and do:

- `geary flow patch --template Golden_RTF_Min --spec myflow.mmd --out MyFlow`
- `geary validate --org deafingov`
- `geary deploy --org deafingov`

The keys turn “Flow XML” into “deterministic patching.”

---

## Appendix: Example lock file format

`golden.lock.json`:

```json
{
  "generated_at": "2026-01-27T22:00:00-05:00",
  "api_version": "60.0",
  "keys": {
    "Golden_RTF_Min.flow-meta.xml": "sha256:....",
    "Golden_Screen_Min.flow-meta.xml": "sha256:....",
    "Golden_Sched_Min.flow-meta.xml": "sha256:...."
  }
}
```
