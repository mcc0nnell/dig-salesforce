#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
BUNDLE_DIR="${1:-"$ROOT/runs/repair-pack-smoke-$STAMP"}"

python3 "$ROOT/tools/geary/geary.py" repair \
  --root "$ROOT" \
  --from-validate-log "$ROOT/tests/fixtures/validate.log" \
  --out "$BUNDLE_DIR"

python3 "$ROOT/tools/geary/geary.py" apply \
  --root "$ROOT" \
  --bundle "$BUNDLE_DIR"

echo "Repair pack smoke run complete: $BUNDLE_DIR"
