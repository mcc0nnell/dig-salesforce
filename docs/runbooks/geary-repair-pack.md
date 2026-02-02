# Geary Repair Pack v0.1.1

## Purpose
Bounded repair automation for known `make dig-validate` failures:
- Flow `nextLabel` invalid in FlowScreen for:
  - `Summit_Sample_Recipe`
- Apex class compile errors for `DigSlaScheduler`.

## Bounds (Enforced)
- `schema_version` must be `0.1.1`.
- `bounds.max_apex_classes <= 1`
- `bounds.max_flows <= 2`
- `bounds.allow_lwc` must be `false`.
- Operations (if present):
  - `op` must be `create_or_update`.
  - `kind` must be `apex_class` or `flow`.
  - `target` must be one of:
    - `DigSlaScheduler`
    - `Summit_Sample_Recipe`

If any rule fails, the blueprint is rejected and no patching occurs.

## CLI
Generate a repair bundle:

```bash
python3 tools/geary/geary.py repair \
  --root . \
  --from-validate-log path/to/validate.log \
  --out runs/repair-pack/my-run
```

Apply a repair bundle (includes re-running `make dig-validate`):

```bash
python3 tools/geary/geary.py apply \
  --root . \
  --bundle runs/repair-pack/my-run
```

## Bundle Contents
- `blueprint.json`
- `validate.log`
- `receipt.json`
- `emissions.ndjson`
- `plan.json` (human-readable patch plan)

## Patch Strategy
- Flow XML: remove only `<nextLabel>` under `<screens>` (FlowScreen). No other changes.
- Apex `DigSlaScheduler`:
  - If validate log shows `Unexpected token 'by'` or `Expression cannot be assigned`, rename variable `by` to `byDt`.
  - Otherwise, replace with a minimal stub that compiles.

## Receipts and Emissions
- Receipt format (JSON):
  - `schema_version`, `run_id`, `mode`, `status`, `targets`, `patches`, `validate`, timestamps.
- Emissions are append-only NDJSON. Minimum events:
  - `run.started`
  - `validate_log.parsed`
  - `blueprint.generated`
  - `blueprint.validated`
  - `patch.planned`
  - `patch.applied`
  - `validate.reran`
  - `run.completed` / `run.failed`

## Idempotency
Applying the same bundle twice results in no further changes. Actions will be `skipped` when no modifications are required.

## Repo Hygiene Note
If validation fails on a Flow that does not exist in the org, treat it as an orphan artifact and delete/move it out of `force-app/`.
Geary Repair Pack should not attempt a Flow Builder resave for missing flows; instead it should emit an `orphaned_artifact` receipt entry with the recommended `git rm` command.

Geary will never instruct a Flow Builder resave unless the Flow exists in the target org. If the Flow is missing, it emits `orphan_report.md` and marks the file as `orphaned_artifact`.

## Smoke Test
Use the fixture validate log:

```bash
scripts/smoke_geary_repair.sh
```

This will generate a bundle under `runs/repair-pack-smoke-<timestamp>` and apply it (including `make dig-validate`).
