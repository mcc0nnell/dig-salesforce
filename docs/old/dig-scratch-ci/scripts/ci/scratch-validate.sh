#!/usr/bin/env bash
set -euo pipefail

# Local helper for CI parity (optional):
# Creates scratch org, runs make dig-validate, then deletes.
# Requires you to already be authenticated to the Dev Hub locally.

SCRATCH_ALIAS="${1:-dig-ci-local}"

sf org create scratch \
  --definition-file config/project-scratch-def.json \
  --alias "$SCRATCH_ALIAS" \
  --duration-days 1 \
  --set-default \
  --wait 20

if make help >/dev/null 2>&1; then
  make dig-validate
else
  sf project deploy start --manifest manifest/dig.xml --dry-run --wait 30
fi

sf org delete scratch --target-org "$SCRATCH_ALIAS" --no-prompt
