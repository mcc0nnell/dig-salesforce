# Mermaid Intake (DIG Ops Catalog)

This slice documents the **Mermaid Intake** capability as an **owned + bounded** Salesforce slice (alias: `mermaid-intake`).

## Purpose
Convert Mermaid diagrams into:
- renderable SVG previews
- structured “app blueprint” JSON for follow-on generation work

## Ownership + boundaries
- **Source of truth** for Mermaid metadata lives under `dig-src/` (not `force-app/`).
- The slice alias `mermaid-intake` is **not** included in `comms-web` or `comms-web-full`.
- `X-Geary-Key` is used **server-side only**, and must never be logged or surfaced to LWC.

### Key usage allowlist
`X-Geary-Key` may appear only in:
- `dig-src/main/default/classes/MermaidHttpClient.cls`
- `dig-src/main/default/classes/MermaidSecrets.cls`
- `tools/geary/geary.py` (**mermaid** subcommand only)
- `tools/geary/mermaid_client.py`

## Deployment (Salesforce CLI)
Preview each manifest (no deploy):

```bash
sf project deploy preview --manifest manifest/slice-apex-mermaid-intake.xml --target-org <ORG_ALIAS>
sf project deploy preview --manifest manifest/slice-lwc-mermaid-intake.xml --target-org <ORG_ALIAS>
sf project deploy preview --manifest manifest/slice-permissionsets-mermaid-intake.xml --target-org <ORG_ALIAS>
sf project deploy preview --manifest manifest/slice-csp-mermaid-intake.xml --target-org <ORG_ALIAS>
```

Validate + run only the intended unit test:

```bash
sf project deploy validate --manifest manifest/mermaid-intake-package.xml \
  --target-org <ORG_ALIAS> \
  --test-level RunSpecifiedTests \
  --tests MermaidRenderService_Test
```

Run the test class directly:

```bash
sf apex run test --tests MermaidRenderService_Test --target-org <ORG_ALIAS>
```

## Prerequisites
- Named Credential required: `Geary_Mermaid_Worker`
- CSP Trusted Site required: `Geary_Mermaid_Worker` (CspTrustedSite)
- Permission set does NOT enforce named credential access because org metadata schema may not support `namedCredentialAccess`.

## Troubleshooting
- **Duplicate metadata errors**: confirm Mermaid assets exist only under `dig-src/` (remove any old copies under `force-app/`).
- **Deploy doesn't include files**: verify the `--manifest` path is correct and your `--target-org` alias resolves.
- **Callout failures**: confirm the Named Credential / endpoint configuration is present and points to the Mermaid worker.
