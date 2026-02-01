# Slice Index

Generated from `catalog/build/catalog.yml`.

| id | name | band | owner | docs | bounded | requires | deploy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| digops-10-org-baseline | Org Baseline | boot | DIG Ops / Platform | [Org Baseline](../ui/org-baseline.md) | yes | - | - |
| digops-12-ops-envelope | Ops Envelope | services | DIG Ops / Platform | [Ops Envelope](../ui/ops-envelope.md) | yes | - | - |
| digops-21-membership-mvp | Membership MVP | domain | DIG Ops / Membership | [Membership Mvp](../ui/membership-mvp.md) | yes | - | - |
| digops-22-membership-renewal-loop | Membership Renewal Loop | domain | DIG Ops / Membership | [Membership Renewal Loop](../ui/membership-renewal-loop.md) | yes | digops-21-membership-mvp | - |
| digops-41-mermaid-intake | Mermaid Intake | ui | DIG Ops / Geary | - | unknown | digops-32-policy-enforcement, digops-30-core-services | manifests:4 packages:1<br>[slice-apex-mermaid-intake.xml](../../manifest/slice-apex-mermaid-intake.xml)<br>[slice-csp-mermaid-intake.xml](../../manifest/slice-csp-mermaid-intake.xml)<br>[slice-lwc-mermaid-intake.xml](../../manifest/slice-lwc-mermaid-intake.xml)<br>[slice-permissionsets-mermaid-intake.xml](../../manifest/slice-permissionsets-mermaid-intake.xml)<br>[mermaid-intake-package.xml](../../manifest/mermaid-intake-package.xml) |
| digops-44-ui-hud-embed | HUD Embed Pattern | ui | DIG Ops / Web | [Hud Embed](../ui/hud-embed.md) | unknown | digops-12-portal-google-sites, digops-21-dig-emissions-journal-runtime | - |
| digops-45-ui-emissions-console | Emissions Console | ui | DIG Ops / Ops UI | [Emissions Console](../ui/emissions-console.md) | yes | - | - |
| digops-61-email-comms-runner | Email Comms Runner | comms+integrations | DIG Ops / Comms | [Email Comms Runner](../ui/email-comms-runner.md) | yes | - | - |

## Deploy Map

| id | manifests | packages |
| --- | --- | --- |
| digops-41-mermaid-intake | [slice-apex-mermaid-intake.xml](../../manifest/slice-apex-mermaid-intake.xml)<br>[slice-csp-mermaid-intake.xml](../../manifest/slice-csp-mermaid-intake.xml)<br>[slice-lwc-mermaid-intake.xml](../../manifest/slice-lwc-mermaid-intake.xml)<br>[slice-permissionsets-mermaid-intake.xml](../../manifest/slice-permissionsets-mermaid-intake.xml) | [mermaid-intake-package.xml](../../manifest/mermaid-intake-package.xml) |
