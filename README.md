# dig-sf

Salesforce DX (SFDX) project for Deaf in Government (DIG). This repo keeps DIG-owned metadata in a clean source root and avoids pulling noisy org metadata unless explicitly needed.

## Quickstart

Prereqs
- Salesforce CLI (`sf`) installed
- Org alias `dig` authenticated

Verify org
```bash
sf org display --target-org dig
```

Common commands
```bash
make help
make whoami
make dig-retrieve
make dig-validate
make org

# Membership (combined slice)
sf project deploy start --target-org dig --manifest manifest/membership-all-package.xml
```

## Project structure

- `dig-src/` is the authoritative source root
  - `dig-src/main/default/flows/`
  - `dig-src/main/default/flowDefinitions/`
  - `dig-src/main/default/permissionsets/`
  - `dig-src/main/default/objects/`
- `manifest/dig.xml` is the canonical DIG slice (broader; use intentionally)
- Membership manifests (tight scope)
  - `manifest/membership-mvp-package.xml` (initial MVP slice)
  - `manifest/membership-update-status-package.xml` (update-status flow only)
  - `manifest/membership-all-package.xml` (object + fields + both flows + permsets)
  - `manifest/membership-listviews-package.xml` (Membership list views)
- `Makefile` provides standardized CLI targets
- `agents.md` contains AI agent instructions

## Project-local defaults

Set defaults for this repo (no global flags):
- Default org (direct): `sf config set target-org deafingov`
- Use alias as default: `sf config set target-org dig`
- Optional Dev Hub: `sf config set target-dev-hub deafingov`
- Verify: `sf config get target-org` and `sf config get target-dev-hub`

## Standard workflow

1) Retrieve only what you need
```bash
sf project retrieve start --target-org dig --manifest manifest/dig.xml
```

2) Edit metadata in `dig-src/`

3) Validate before any deploy
```bash
make dig-validate
```

4) Deploy
```bash
sf project deploy start --target-org dig --manifest manifest/dig.xml
```

## Membership slice

Retrieve (combined)
```bash
sf project retrieve start --target-org dig --manifest manifest/membership-all-package.xml
```

Deploy (combined)
```bash
sf project deploy start --target-org dig --manifest manifest/membership-all-package.xml
```

Renewal fields
```bash
sf project retrieve start --target-org dig --manifest manifest/membership-renewal-fields-package.xml
```

## Membership list views

List views live under:
- `dig-src/main/default/objects/Membership__c/listViews/`

Retrieve list views
```bash
sf project retrieve start --target-org dig --manifest manifest/membership-listviews-package.xml
```

## Guardrails

- Do not retrieve or deploy layouts/profiles unless explicitly requested.
- Do not paste access tokens or auth secrets into logs or commits.
- Keep commits small and focused.
