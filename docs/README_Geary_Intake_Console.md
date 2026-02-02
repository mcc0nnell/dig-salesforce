# Geary Intake Console (Phase 1)

## Overview
The Geary Intake Console is a Lightning Web Component that lets DIG Ops paste or upload Mermaid text, preview the SVG, generate a bounded Blueprint (schema v0.1), validate it, and export a bundle for offline execution.

This Phase 1 build is intentionally bounded and offline-first:
- No direct metadata edits from Salesforce.
- Export a deterministic bundle for `scripts/geary validate/deploy`.
- Store receipts/emissions in Salesforce later (Phase 2) or attach pointers.

## Blueprint schema v0.1 (tiny, bounded)

```json
{
  "schema_version": "0.1",
  "input": {
    "mermaid": {
      "format": "text",
      "text": "<mermaid source>",
      "hash": "sha256:<hex>"
    }
  },
  "bounds": {
    "max_custom_objects": 2,
    "max_permission_sets": 1,
    "allow_lwc": false
  },
  "operations": [
    {
      "kind": "custom_object",
      "action": "create_or_update",
      "api_name": "Example__c"
    },
    {
      "kind": "permission_set",
      "action": "create_or_update",
      "api_name": "DIG_Ops_Example"
    }
  ],
  "notes": ""
}
```

Validation rules (Phase 1):
- `schema_version` must be `0.1`.
- `bounds.max_custom_objects <= 2` and `bounds.max_permission_sets <= 1`.
- `bounds.allow_lwc` must be `false`.
- Operations are optional; if present they must be `create_or_update` and `kind` must be `custom_object` or `permission_set`.

## How to use the console
1) Add the **Geary Intake Console** LWC to a Lightning App/Home page.
2) Paste Mermaid text or upload a `.mmd` file.
3) Click **Render Preview** to see the SVG.
4) Click **Generate Blueprint** then **Validate Blueprint**.
5) Click **Export Bundle** to download:
   - `blueprint.json`
   - `input.mmd`
   - `receipt.json`
   - `emissions.ndjson`

## Mapping to `scripts/geary validate/deploy`
Use the exported bundle as the input to your local Geary workflow:

```bash
scripts/geary validate --manifest manifest/dig.xml --bundle /path/to/bundle
scripts/geary deploy --manifest manifest/dig.xml --bundle /path/to/bundle
```

Notes:
- Run `make dig-validate` before any deploy.
- Prefer tight manifests (e.g., `manifest/dig.xml`).
- Treat `deafingov` as the default org alias.

## Receipts and emissions storage
Phase 1 is offline-first. If you want in-org evidence, publish emissions via the Platform Event spine:
- `DIG_Emission__e` (bus) + `DIG_Emission__c` (durable sink) using `DIG_Emissions.emit(...)`.
You can still store artifacts and receipts separately using:
- `Geary_Run__c`: run_id, status, mode, input_hash, output_hash, started/finished timestamps, error fields.
- `Geary_Artifact__c`: pointers for `blueprint.json`, `input.mmd`, `receipt.json`, `emissions.ndjson`.

## Repo invariant
Workflow file updates under `.github/workflows/*.yml` may require the GitHub UI or a token with `workflow` scope. Avoid modifying these without the required scope.
