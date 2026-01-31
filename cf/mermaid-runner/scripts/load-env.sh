#!/usr/bin/env bash
set -euo pipefail

set -a
[ -f .env ] && source .env
[ -f .env.local ] && source .env.local
set +a

if [ -z "${GEARY_KEY:-}" ]; then
  echo "error: GEARY_KEY is not set. Populate .env.local (gitignored) or ~/.config/geary/.env before running." >&2
  exit 1
fi

printf 'GEARY_KEY length=%s\n' "${#GEARY_KEY}"
printf 'WORKER_URL=%s\n' "${WORKER_URL:-}"
