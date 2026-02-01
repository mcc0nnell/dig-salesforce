# geary lint:slices (Geary 4) — rule list

This document describes the validation gates that enforce the "DIG Ops OS" slice architecture.

## Gate A — Band law
- `slice.number` must be within the declared band's allowed range (see `catalog/rules/band-rules.yml`).
- A slice may depend only on same-or-lower band priority, except:
  - `wrapper` may depend on `domain` and `ui`
  - `exec` may depend on all

## Gate B — Dependency completeness
If `policy.comms.require_receipts: true`, slice must depend on:
- `digops-20-emissions-engine`
and one of:
- `digops-22-activity-emissions` (activity-path receipts), or
- `digops-90-comms-core` (dispatcher-path receipts)

## Gate C — Comms separation (spine contract)
If `spine.name` is present:
- Must match an entry in `muni/contracts/spines.yml`
- `owns_mailbox`, `sender_address`, and `template_prefixes` must exactly match contract
- Any template keys referenced must match allowed prefixes
- Cross-spine template prefixes are forbidden

## Gate D — Mailbox ownership
- A slice declares at most one `spine.name`
- Shared subsystems (e.g., `digops-90-comms-core`) must set `spine: null`

## Gate E — Idempotency requirement
If slice sends planned comms (touches/notices):
- Must define a comms ledger (`spine.comms_ledger` or equivalent)
- Must document idempotency key strategy (recommended: `(target, envelope, touch_type, planned_date)`)

## Gate F — Install-order sanity
- Domain slices that send comms must depend on `digops-90-comms-core`
  unless they explicitly declare "activity-only comms" mode.
- `exec` rollup should install last.
