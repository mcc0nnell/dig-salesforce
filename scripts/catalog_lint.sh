#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f "scripts/catalog_compile.py" ]]; then
  echo "CATALOG LINT: FAIL"
  echo "Reason: scripts/catalog_compile.py not found"
  exit 127
fi

PYTHON_BIN="python3"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "CATALOG LINT: FAIL"
  echo "Reason: python3/python not found"
  exit 127
fi

mkdir -p catalog/build

set +e
"$PYTHON_BIN" scripts/catalog_compile.py
RC=$?
set -e

if [[ $RC -eq 0 ]]; then
  if [[ -f "scripts/catalog_index.py" ]]; then
    "$PYTHON_BIN" scripts/catalog_index.py
    RC=$?
  else
    echo "CATALOG LINT: FAIL"
    echo "Reason: scripts/catalog_index.py not found"
    exit 127
  fi
fi

if [[ $RC -eq 0 ]]; then
  echo "CATALOG LINT: PASS"
  exit 0
fi

echo "CATALOG LINT: FAIL"
if [[ -f catalog/build/catalog_report.md ]]; then
  echo "See: catalog/build/catalog_report.md"
fi
exit "$RC"
