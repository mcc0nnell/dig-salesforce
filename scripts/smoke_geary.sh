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
WORKER_HOST="-"
if [[ -n "${WORKER_URL}" ]]; then
  WORKER_HOST=$(python - <<'PY'
import os
from urllib.parse import urlparse
url = os.environ.get('WORKER_URL', '')
print(urlparse(url).netloc or url or '-')
PY
)
fi

KEY_PRESENT="no"
if [[ -n "${GEARY_KEY:-}" ]]; then
  KEY_PRESENT="yes"
fi

RUNS_DIR="${GEARY_RUNS_DIR:-./runs}"

printf 'worker host: %s\n' "$WORKER_HOST"
printf 'key present: %s\n' "$KEY_PRESENT"
printf 'runs dir: %s\n' "$RUNS_DIR"

if ! doctor_output=$(python tools/geary/geary.py doctor 2>&1); then
  echo "$doctor_output"
  echo "LIVE unavailable; running OFFLINE smoke"
  if ! offline_output=$(python tools/geary/geary.py doctor --no-network 2>&1); then
    echo "$offline_output"
    echo "OFFLINE doctor failed" >&2
    exit 1
  fi
  echo "$offline_output"
  run_mode="offline"
else
  echo "$doctor_output"
  run_mode="live"
fi

if [[ "$run_mode" == "offline" ]]; then
  run_args=(--offline)
else
  run_args=()
fi

tmp_artifact=$(mktemp 2>/dev/null || mktemp -t geary-smoke-artifact)
trap 'rm -f "$tmp_artifact"' EXIT

run_output=$(printf 'flowchart TD\n  A-->B\n' | python tools/geary/geary.py run --stdin --format svg "${run_args[@]}" --out "$tmp_artifact" 2>&1)
echo "$run_output"
run_id=$(printf '%s' "$run_output" | awk -F': ' '/^run id:/{print $2}' | tail -n1)
if [[ -z "$run_id" ]]; then
  echo "Failed to parse run id from runner output" >&2
  exit 1
fi

python tools/geary/geary.py replay "$run_id"
