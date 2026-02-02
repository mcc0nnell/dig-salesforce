# Slice: dig.emissions — DIG Emissions

Status: active  
Kind: spine  
Owner: DIG Ops  
Namespace: `dig.*`

## Purpose
Provide a realtime “journal bus” for DIG operations using Salesforce Platform Events, with a durable evidence sink for replay, audit packets, and deterministic verification.

This slice is **not** a logging feature. It is an emissions spine:
- append-only semantics
- idempotent ingestion
- deterministic envelope hashing
- chain integrity (PrevHash → Hash)
- replay capability (via durable sink)

## Contracts

### Event type convention
All events MUST use `Type__c` under the `dig.*` namespace.

Examples:
- `dig.system.heartbeat`
- `dig.membership.renewal.planned`
- `dig.comms.touch.sent`
- `dig.governance.motion.recorded`

### Idempotency
Publishers MUST set `IdempotencyKey__c`.
Consumers/sink MUST treat `IdempotencyKey__c` as the dedupe key.

### Hash chain
Each event carries:
- `PrevHash__c` (empty allowed only for `Seq__c = 1`)
- `Hash__c` = SHA-256 hex of canonical envelope string

## Artifacts

### Salesforce metadata
Platform Event:
- `DIG_Emission__e`

Durable sink object:
- `DIG_Emission__c`

Permissions:
- `DIG_Emissions_Perms`

### Apex
Publisher:
- `DIG_Emissions.cls` (+ meta)

Sink:
- `DIG_EmissionSinkTrigger.trigger`
- (optional handler class if you separate concerns)

### UI
Console:
- LWC `digEmissionsConsole` (SLDS) subscribing to `/event/DIG_Emission__e`

### Docs
- `docs/dig/emissions.md` (authoritative slice doc)

## Deploy / Smoke test
See `docs/dig/emissions.md` for the step-by-step smoke test:
1) deploy metadata + Apex + LWC + permset
2) emit 3 chained events via anonymous Apex
3) confirm realtime console sees them
4) confirm `DIG_Emission__c` persists them
5) verify PrevHash/Hash chain integrity
