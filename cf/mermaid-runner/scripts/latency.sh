#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

pushd "$RUNNER_ROOT" >/dev/null
source scripts/load-env.sh
popd >/dev/null

WORKER_URL="${WORKER_URL:-https://geary-mermaid-runner-v1.stokoe.workers.dev}"

payload='{"mermaid":"flowchart TD\nA-->B","format":"svg"}'

response=$(curl -s --retry 2 --retry-connrefused --retry-delay 1 \
  -w "\n%{http_code}\n%{time_total}" \
  -X POST "${WORKER_URL}/render" \
  -H 'Content-Type: application/json' \
  -H "X-Geary-Key: ${GEARY_KEY}" \
  -d "$payload")

time_total=$(echo "$response" | tail -n1)
status=$(echo "$response" | tail -n2 | head -n1)
body=$(echo "$response" | sed '$d' | sed '$d')

meta=$(python3 - <<'PY'
import json, sys
body = sys.stdin.read().strip()
try:
    data = json.loads(body) if body else {}
except Exception:
    data = {}

fields = []
for key in ("requestId", "stage", "attempt", "elapsedMs"):
    if key in data and data[key] is not None:
        fields.append(f"{key}={data[key]}")

print(" ".join(fields))
PY
<<< "$body")

if [[ -n "$meta" ]]; then
  echo "HTTP:${status} total:${time_total}s ${meta}"
else
  echo "HTTP:${status} total:${time_total}s"
fi
