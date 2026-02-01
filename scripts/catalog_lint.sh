#!/usr/bin/env bash
set -euo pipefail

if python scripts/catalog_compile.py; then
  echo "CATALOG LINT: PASS"
else
  echo "CATALOG LINT: FAIL"
  exit 1
fi
