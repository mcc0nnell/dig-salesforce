# Mermaid intake: Salesforce → Runner → Geary → 14ten Emissions (MVP)
_Date: 2026-01-28_

This is the **most immediate** bridge to make Geary feel “native” inside Salesforce without trying to run Geary-in-Python on-platform.

## Why this is the right next step
- Salesforce **can’t run Python** (and Apex is not a good fit for parsing Mermaid or generating Flow XML).
- Salesforce **is great at orchestration + UX** (LWC + Platform Events + approvals/workflows).
- External runners (Cloudflare/Azure) are great for **heavy transforms** (Mermaid → metadata, linting, packaging).
- The 14ten **Emissions schema** gives you a stable contract so DIG (and others) can build compatible components later.

## Architecture (MVP)
1. **LWC**: user pastes Mermaid + options, hits “Submit”.
2. **Apex**: publishes `Geary_Mermaid_Request__e` with a `CorrelationId`.
3. **External subscriber**: listens for request events, does validation/compile, writes an **emission-event**, uploads artifact if any.
4. **External publisher**: publishes `Geary_Mermaid_Result__e` with status + (optional) artifact URL + emission pointer.
5. **Apex trigger**: updates `Geary_Request__c` for history.
6. **LWC**: subscribes to results and updates live.

## Minimal Salesforce metadata
- Platform Events:
  - `Geary_Mermaid_Request__e` (request)
  - `Geary_Mermaid_Result__e` (status/result)
- Custom object:
  - `Geary_Request__c` (history + UI state)
- Apex:
  - `GearyMermaidService` (submit/publish)
  - Trigger on `Geary_Mermaid_Result__e` (update history)
- LWC:
  - `gearyMermaidIntake` (textarea + subscribe)

## Emissions mapping (suggested)
Use `emission-event.schema.json` fields:

- `kind`: `"geary.mermaid.intake"` (and later `"geary.mermaid.compile"`, `"geary.sf.deploy"`)
- `ts`: now UTC
- `run.id`: correlationId (or a derived run id)
- `regime.id`: `"geary"` (or `"14ten.geary"`)
- `target.system`: `"salesforce"`
- `target.env`: org alias (e.g., `deafingov`)
- `payload`: freeform JSON with:
  - correlationId, targetType, targetName
  - mermaidHash, byteLength
  - compile result, artifact pointers, errors

## Immediate next two “done” outcomes
1) **Salesforce UI publishes + displays results** (even if runner just validates and echoes back).
2) **Runner writes emissions** for every request and result.

Once that’s solid, the next increment is: Mermaid → Flow XML → metadata zip → deploy (via Geary CLI or a deploy service).

## Hard rule (keep it clean)
- Salesforce stays the **control plane + UX**
- External runner stays the **compiler/packager**
- Emissions are the **contract**, so future DIG contributors can swap parts without breaking anything.
