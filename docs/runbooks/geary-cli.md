# Geary CLI Golden Path

This runbook captures the CLI-only workflow for Geary in `dig-sf`. Follow these steps when adjusting flows or running validations so every run is repeatable, offline-friendly, and hard to misuse.

## Environment
Place the following variables in `.env.local` (do **not** commit this file):

- `GEARY_SF_CLIENT_ID`
- `GEARY_SF_USERNAME`
- `GEARY_SF_JWT_KEY_PATH` **or** `GEARY_SF_JWT_KEY_B64`
- `GEARY_SF_INSTANCE_URL` (defaults to https://login.salesforce.com)
- `GEARY_ORG_ALIAS` (defaults to `deafingov`)
- `GEARY_KEY` (Mermaid runner secret)
- `WORKER_URL` (Mermaid worker endpoint)
- Optional: `GEARY_RUNS_DIR` to relocate run artifacts (default `./runs`)

## Auth & Validate
1. `bash scripts/geary_lane` – loads `.env.local`, runs `scripts/geary auth`, and executes `make dig-validate`.
2. If validation succeeds, you may proceed with your slice work.
3. If validation fails, the lane prints the next command (`scripts/geary_repair_lane`) and exits non-zero.
4. `scripts/geary` also understands:
   - `scripts/geary governance:validate` and `governance:deploy`
   - `scripts/geary validate --manifest manifest/dig.xml` (preferred) or another manifest per policy
   - `scripts/geary deploy --manifest manifest/dig.xml --confirm`

## Golden Path
Stick to the wrapper script:

```
bash scripts/geary_lane
```

It guarantees env loading, auth, and validation. Do not skip this step before attempting to apply changes.

## Repair Path
When validation fails, run the scripted repair loop:

```
bash scripts/geary_repair_lane
```

This lane:
- Runs `make dig-validate 2>&1 | tee runs/validate.log`
- Builds a bundle via `python tools/geary/geary.py repair --from-validate-log runs/validate.log --out runs/repair-pack`
- Applies fixes with `python tools/geary/geary.py apply --bundle runs/repair-pack`
- Prints the paths to `runs/repair-pack/receipt.json`, `runs/repair-pack/emissions.ndjson`, and optional `orphan_report.md` / `resave_instructions.md`.
- Exits non-zero if validation failed or the final receipt status is not `ok` so you can inspect the generated artifacts.

## Invariants
- **Orphaned flows**: if a flow does not exist in the org, `repair` emits `orphaned_artifact` and creates `runs/repair-pack/orphan_report.md`. Remove the local file and references with:
  ```bash
  git rm dig-src/main/default/flows/<FlowApiName>.flow-meta.xml
  rg -n "<FlowApiName>" manifest docs scripts dig-src
  ```
  Then rerun `bash scripts/geary_lane`.

- **Flow order/schema drift**: if the flow exists but Flow Builder reports `resave_required`, open the flow in Setup → Flows, edit and **Save**, retrieve the updated metadata (`sf project retrieve start --metadata "Flow:<FlowApiName>" --target-org deafingov`), and re-run `bash scripts/geary_lane`.

## Tight manifest guidance
Always prefer `manifest/dig.xml` when retrieving or deploying. Do **not** deploy broad metadata slices unless explicitly requested.

## No new metadata
We are only updating configuration/scripts in this repo. Do not add or deploy new slices, flows, LWC bundles, objects, or permission sets—continue to treat `dig-src/` and `force-app/` as read-only for metadata.
