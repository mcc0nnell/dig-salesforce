#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

if [[ -z "${GEARY_KEY:-}" ]]; then
  echo "GEARY_KEY is not set. Export it (e.g., source scripts/load-env.sh)." >&2
  exit 1
fi

TMP_JSON=$(mktemp)
TMP_SVG=$(mktemp)
cleanup() {
  rm -f "$TMP_JSON" "$TMP_SVG"
}
trap cleanup EXIT

python tools/geary/geary.py mermaid --format json --quiet --out "$TMP_JSON"
if ! grep -q '"ok"[[:space:]]*:[[:space:]]*true' "$TMP_JSON"; then
  echo "JSON output missing ok:true" >&2
  exit 1
fi

python tools/geary/geary.py mermaid --format svg --quiet --out "$TMP_SVG"
if ! grep -q '<svg' "$TMP_SVG"; then
  echo "SVG output missing <svg" >&2
  exit 1
fi
