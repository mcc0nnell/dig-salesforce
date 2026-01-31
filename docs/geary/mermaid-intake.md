# Mermaid Intake Slice

## 1. Overview

The Mermaid Intake slice provides the core functionality for rendering Mermaid diagrams within the Geary platform. This slice is designed to be owned and bounded, separated from the comms-web slice to ensure clear architectural boundaries.

## 2. Ownership and Boundaries

- **Ownership**: Mermaid Intake metadata has been moved from `force-app/` to `dig-src/` (same relative paths) to avoid duplicates
- **Slice Alias**: `mermaid-intake`
- **Boundary Enforcement**: 
  - `mermaid-intake` is NOT included in `comms-web` or `comms-web-full` alias expansion
  - All Mermaid-related components are contained within this slice only

## 3. What's in the Slice

The Mermaid Intake slice is defined by these 4 manifests:

- `manifest/slice-apex-mermaid-intake.xml`
- `manifest/slice-lwc-mermaid-intake.xml`
- `manifest/slice-permissionsets-mermaid-intake.xml`
- `manifest/slice-csp-mermaid-intake.xml`

Optional convenience package manifest:
- `manifest/mermaid-intake-package.xml`

## 4. Security Model

The Mermaid Intake slice implements strict security boundaries to protect sensitive authentication keys:

### X-Geary-Key Usage
The `X-Geary-Key` header is used ONLY in:
- `dig-src/main/default/classes/MermaidHttpClient.cls`
- `dig-src/main/default/classes/MermaidSecrets.cls`
- `tools/geary/geary.py` (ONLY within the `mermaid` subcommand)
- `tools/geary/mermaid_client.py`

### Security Checklist
- [ ] No logging of `X-Geary-Key` or headers containing it
- [ ] No exposure of `X-Geary-Key` to Lightning Web Components
- [ ] All `X-Geary-Key` usage is limited to server-side callouts
- [ ] CLI flags `--key` and `--env-file` are scoped to the `geary mermaid` subcommand only

## 5. How to Deploy

### Preview per Manifest
```bash
sf project deploy preview --manifest manifest/slice-apex-mermaid-intake.xml --target-org <ORG_ALIAS>
sf project deploy preview --manifest manifest/slice-lwc-mermaid-intake.xml --target-org <ORG_ALIAS>
sf project deploy preview --manifest manifest/slice-permissionsets-mermaid-intake.xml --target-org <ORG_ALIAS>
sf project deploy preview --manifest manifest/slice-csp-mermaid-intake.xml --target-org <ORG_ALIAS>
```

### Validate and Run Specific Tests
```bash
sf project deploy validate --manifest manifest/mermaid-intake-package.xml --target-org <ORG_ALIAS> --test-level RunSpecifiedTests --tests MermaidRenderService_Test
```

## 6. How to Run Tests

### Run MermaidRenderService_Test Only
```bash
sf apex test run --tests MermaidRenderService_Test --target-org <ORG_ALIAS>
```

### Run All Local Tests (for verification)
```bash
sf apex test run --test-level RunLocalTests --target-org <ORG_ALIAS>
```

## 7. Troubleshooting

### Duplicate Metadata Symptoms
- **Issue**: Deployment fails with "named in package.xml but not found" errors
- **Fix**: Ensure only `dig-src/` contains Mermaid assets, remove duplicates from `force-app/`

### "Why Isn't My Deploy Picking Up Files?"
- Check that manifest paths are correct
- Verify the target org alias is correct
- Confirm `package.xml` references the appropriate manifests

### Named Credential / Endpoint Issues
- Ensure Named Credential `Geary_Mermaid_Worker` is properly configured
- Verify the endpoint URL is accessible from the target org

### X-Geary-Key Leak Prevention
- Never log headers or values containing `X-Geary-Key`
- Never expose `X-Geary-Key` to client-side components
- Only use `X-Geary-Key` in server-side Apex callouts

## 8. Change Log

### 2026-01-31
- Initial implementation of Mermaid Intake slice
- Moved Mermaid metadata from `force-app/` to `dig-src/`
- Created all 4 manifests for slice definition
- Configured `mermaid-intake` alias in `geary/slices.yml`
- Implemented security boundaries for `X-Geary-Key` usage
- Verified `comms-web` alias does not include Mermaid assets
