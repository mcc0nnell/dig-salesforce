# Codex prompt — Salesforce: Mermaid Intake MVP (Platform Events + LWC)
You are working in repo `dig-sf` (Salesforce SFDX project). Implement a **Mermaid Intake** surface in Salesforce that:
1) Lets an admin paste Mermaid text in an LWC UI.
2) Publishes a Platform Event request for an external runner to process.
3) Streams back status updates (via a result Platform Event) and displays them in the LWC.

## Constraints / principles
- Keep it **MVP and production-safe**: no hard-coded org IDs; no org data dependencies in tests.
- Use **Platform Events** for request/response. Use the `lightning/empApi` client in LWC to subscribe to results.
- Store request state in a small custom object so the LWC can show history even after refresh.
- Everything must deploy cleanly via SFDX metadata.

## Metadata to add

### A) Platform Events
Create two Platform Events:

1) `Geary_Mermaid_Request__e`
Fields (API name → type):
- `CorrelationId__c` → Text(36) **Required**
- `Mermaid__c` → Long Text Area(32768) **Required**
- `TargetOrg__c` → Text(80) (store SF alias or org name; optional)
- `TargetType__c` → Text(80) (e.g., `Flow`, `Metadata`, `Apex`; optional)
- `TargetName__c` → Text(255) (e.g., `DIG_Membership_OnCreate`; optional)
- `OptionsJson__c` → Long Text Area(32768) (JSON; optional)
- `RequestedBy__c` → Text(80) (UserId; optional)
- `RequestedAt__c` → Date/Time (optional)

2) `Geary_Mermaid_Result__e`
Fields:
- `CorrelationId__c` → Text(36) **Required**
- `Status__c` → Text(40) (e.g., `QUEUED|RUNNING|SUCCEEDED|FAILED`) **Required**
- `Message__c` → Long Text Area(32768) (optional)
- `ArtifactUrl__c` → Url(255) (optional)  // link to zip/logs/PR
- `EmissionId__c` → Text(80) (optional)   // pointer to emissions log entry
- `CompletedAt__c` → Date/Time (optional)

### B) Custom object for history
Create `Geary_Request__c` with fields:
- `CorrelationId__c` Text(36) **External ID + Unique**
- `Status__c` Picklist (`QUEUED`,`RUNNING`,`SUCCEEDED`,`FAILED`)
- `Mermaid__c` Long Text Area(32768)
- `Message__c` Long Text Area(32768)
- `ArtifactUrl__c` Url(255)
- `EmissionId__c` Text(80)
- `RequestedBy__c` Lookup(User)
- `RequestedAt__c` Date/Time
- `CompletedAt__c` Date/Time

### C) Apex
1) `GearyMermaidService.cls`
- `@AuraEnabled` method `submit(String mermaid, String targetType, String targetName, String optionsJson)`:
  - Creates/Upserts `Geary_Request__c` with a new `CorrelationId__c` (UUID).
  - Publishes `Geary_Mermaid_Request__e` with the same correlation id and payload.
  - Returns the correlation id.

2) `GearyMermaidResultTrigger.trigger` on `Geary_Mermaid_Result__e`
- For each result event:
  - Find `Geary_Request__c` by `CorrelationId__c` (upsert if missing).
  - Update status/message/artifact/emission/completedAt.

3) **Tests**
- `GearyMermaidServiceTests.cls`:
  - Call `GearyMermaidService.submit(...)` and assert:
    - A `Geary_Request__c` record exists with `QUEUED` or initial status.
    - A Platform Event publish happened (you can assert `Database.SaveResult`).
  - Then simulate receiving a result event by directly inserting `Geary_Mermaid_Result__e` and assert `Geary_Request__c` updated.
- Keep tests org-data-free.

### D) LWC
Create `gearyMermaidIntake`:
- UI: textarea for Mermaid, inputs for target type/name, options JSON, submit button.
- On submit: call Apex `submit(...)`, show correlation id, status = QUEUED.
- Subscribe to `/event/Geary_Mermaid_Result__e` using `lightning/empApi`.
- When a result arrives for matching correlation id:
  - update local UI state and refresh the request record via Apex (or LDS).
- Also show a small history list (last 10 `Geary_Request__c`).

Expose as:
- A Lightning App Page tab (simple), or a Home Page component for DIG Ops admin.

### E) Permissions
Create a permission set `Geary_Mermaid_Admin`:
- CRUD on `Geary_Request__c`
- Read on both Platform Events, publish on request event.

## File placement
Put metadata under `dig-src/main/default/...` consistent with repo conventions.

## Acceptance
- `sf project deploy start --target-org deafingov --manifest manifest/slice-objects.xml` etc should succeed.
- `sf apex test run --target-org deafingov --test-level RunLocalTests --code-coverage` passes.

## Output
- Provide a concise list of created files.
- Include any required manifest updates (if the repo uses slice manifests).
