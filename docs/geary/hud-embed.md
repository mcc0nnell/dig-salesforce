# <!-- This file is deprecated. See docs/ui/hud-embed.md for the latest documentation -->
# HUD Embed (DIG Ops Catalog)

This slice documents the **HUD Embed** capability as an **owned + bounded** Salesforce slice (alias: `hud-embed`).

## Purpose
Embed the DIG Ops HUD (Heads-Up Display) within Salesforce Lightning pages to provide real-time operational insights and quick actions.

## Ownership + boundaries
- The slice alias `hud-embed` is **not** included in `comms-web` or `comms-web-full`.
- HUD components are designed to be lightweight and non-intrusive.
- All HUD embedding logic is contained within this slice only.

## Deployment (Salesforce CLI)
Preview each manifest (no deploy):

```bash
sf project deploy preview --manifest manifest/slice-apex-hud-embed.xml --target-org <ORG_ALIAS>
sf project deploy preview --manifest manifest/slice-lwc-hud-embed.xml --target-org <ORG_ALIAS>
sf project deploy preview --manifest manifest/slice-permissionsets-hud-embed.xml --target-org <ORG_ALIAS>
sf project deploy preview --manifest manifest/slice-csp-hud-embed.xml --target-org <ORG_ALIAS>
```

Validate + run only the intended unit test:

```bash
sf project deploy validate --manifest manifest/hud-embed-package.xml \
  --target-org <ORG_ALIAS> \
  --test-level RunSpecifiedTests \
  --tests HudEmbedService_Test
```

Run the test class directly:

```bash
sf apex run test --tests HudEmbedService_Test --target-org <ORG_ALIAS>
```

## Troubleshooting
- **HUD not appearing**: confirm the Lightning page includes the HUD embed component.
- **Deployment fails**: verify manifest paths are correct and target org alias resolves.
- **Performance issues**: check for excessive component re-renders or API calls.
