#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

pushd "$RUNNER_ROOT" >/dev/null
source scripts/load-env.sh
popd >/dev/null

WORKER_URL="${WORKER_URL:-https://geary-mermaid-runner-v1.stokoe.workers.dev}"

echo "Smoke tests: hitting ${WORKER_URL}/render with GEARY_KEY length=${#GEARY_KEY}"

fail_count=0

log_pass() {
  echo "PASS: $1"
}

log_fail() {
  echo "FAIL: $1" >&2
  fail_count=$((fail_count + 1))
}

check_status() {
  local name="$1"
  local expected="$2"
  local status="$3"
  if [[ "$status" == "$expected" ]]; then
    log_pass "$name (status $status)"
  else
    log_fail "$name (expected $expected, got $status)"
  fi
}

# Test 1: Missing auth => 401
status=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "${WORKER_URL}/render" \
  -H 'Content-Type: application/json' \
  -d '{"mermaid":"flowchart TD\nA-->B"}')
check_status "missing auth" 401 "$status"

## Test 2: Valid auth => 200 and ok:true
body=$(curl -s -w "\n%{http_code}" \
  -X POST "${WORKER_URL}/render" \
  -H 'Content-Type: application/json' \
  -H "X-Geary-Key: ${GEARY_KEY}" \
  -d '{"mermaid":"flowchart TD\nA-->B"}')
status=$(echo "$body" | tail -n1)
resp=$(echo "$body" | sed '$d')
check_status "valid auth" 200 "$status"
if echo "$resp" | grep -Eq '"ok"[[:space:]]*:[[:space:]]*true'; then
  log_pass "response ok:true"
else
  log_fail "response missing ok:true"
fi

# Test 2b: SVG render via runner
svg_body=$(curl -s -w "\n%{http_code}" \
  -X POST "${WORKER_URL}/render" \
  -H 'Content-Type: application/json' \
  -H "X-Geary-Key: ${GEARY_KEY}" \
-d '{"mermaid":"graph TD\nA-->B","format":"svg"}')
svg_status=$(echo "$svg_body" | tail -n1)
svg_resp=$(echo "$svg_body" | sed '$d')
check_status "svg render" 200 "$svg_status"
if echo "$svg_resp" | grep -Eq '"ok"[[:space:]]*:[[:space:]]*true'; then
  log_pass "svg response ok:true"
else
  log_fail "svg response missing ok:true"
fi
if echo "$svg_resp" | grep -Eq '"svg"[[:space:]]*:'; then
  log_pass "svg response contains svg field"
else
  log_fail "svg response missing svg field"
fi
if echo "$svg_resp" | grep -Eq '<svg'; then
  log_pass "svg payload contains <svg"
else
  log_fail "svg payload missing <svg"
fi

# Test 3: Oversized payload => 413
payload=$(python3 - <<'PY'
import json
size = 200 * 1024 + 10
print(json.dumps({"mermaid": "A" * size}))
PY
)
status=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "${WORKER_URL}/render" \
  -H 'Content-Type: application/json' \
  -H "X-Geary-Key: ${GEARY_KEY}" \
  --data "$payload")
check_status "oversized payload" 413 "$status"

if [[ "$fail_count" -gt 0 ]]; then
  exit 1
fi
