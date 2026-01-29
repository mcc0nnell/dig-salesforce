#!/usr/bin/env bash
set -euo pipefail

load_env_file() {
  local env_file="$1"
  if [[ -f "$env_file" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "$env_file"
    set +a
  fi
}

load_env_file ".env.local"
load_env_file ".env"

WORKER_URL="${WORKER_URL:-https://geary-mermaid-runner-v1.stokoe.workers.dev}"
KEY="${GEARY_KEY:-}"

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

if [[ -z "$KEY" ]]; then
  echo "GEARY_KEY is not set. Export it or run scripts/gen_geary_key.sh and then: set -a; source .env.local; set +a" >&2
  exit 2
fi

# Test 2: Valid auth => 200 and ok:true
body=$(curl -s -w "\n%{http_code}" \
  -X POST "${WORKER_URL}/render" \
  -H 'Content-Type: application/json' \
  -H "X-Geary-Key: ${KEY}" \
  -d '{"mermaid":"flowchart TD\nA-->B"}')
status=$(echo "$body" | tail -n1)
resp=$(echo "$body" | sed '$d')
check_status "valid auth" 200 "$status"
if echo "$resp" | grep -Eq '"ok"[[:space:]]*:[[:space:]]*true'; then
  log_pass "response ok:true"
else
  log_fail "response missing ok:true"
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
  -H "X-Geary-Key: ${KEY}" \
  --data "$payload")
check_status "oversized payload" 413 "$status"

if [[ "$fail_count" -gt 0 ]]; then
  exit 1
fi
