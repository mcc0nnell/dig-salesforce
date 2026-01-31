# Codex prompt — External runner: subscribe to Salesforce Mermaid requests + emit results + 14ten emissions
Implement a small **subscriber/worker** that listens for `Geary_Mermaid_Request__e` events and responds with
`Geary_Mermaid_Result__e`.

## Context
- Salesforce side publishes Mermaid requests.
- External side already has an execution environment (Cloudflare runner is OK).
- We want to write a durable, append-only log using the **14ten Emissions schema v0.1.0** (see the schema zip in this chat).
- The runner compiles Mermaid → some output artifact (initially: just echo/validate + store Mermaid; later: Mermaid → Flow XML/metadata zip).

## MVP behavior
On request event:
1) Validate Mermaid (non-empty, starts with `flowchart` or `sequenceDiagram` etc).
2) Emit an **emission-event** JSON per 14ten schema:
   - kind = "geary.mermaid.intake"
   - ts = now (UTC ISO8601)
   - run.id = correlation id (or a generated run id that embeds it)
   - target.system = "salesforce"
   - target.env = target org name/alias if provided
   - payload: include {correlationId, targetType, targetName, optionsJson, mermaidHash, byteLength}
3) Post back a `Geary_Mermaid_Result__e`:
   - Status__c = QUEUED then RUNNING then SUCCEEDED (or FAILED)
   - Message__c: human message
   - ArtifactUrl__c: optional (for now can be empty; later point to a zip in blob storage)
   - EmissionId__c: whatever ID you use (hash/uuid)

## Implementation notes
- **Do not** attempt to run Python inside Salesforce.
- Prefer a simple subscriber using Streaming API (CometD) OR Pub/Sub API.
- If using .NET, OK to host in Azure Container Apps or Functions.
- Store emissions locally first (e.g., append JSONL), then later wire to Azure Event Hubs / storage.

## Deliverables
- A small service with:
  - Config: SF login/auth, topic name, replay handling
  - Subscribe loop
  - A `publishResult(correlationId, status, message, artifactUrl, emissionId)` helper
  - Emissions writer using the schema (validate against schema if easy)
- A README showing how to run locally and how to deploy.

## Output
- Provide the file tree, key code snippets, and step-by-step run instructions.
