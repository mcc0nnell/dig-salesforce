#!/usr/bin/env bash
set -euo pipefail

if command -v openssl >/dev/null 2>&1; then
  key=$(openssl rand -hex 32)
else
  key=$(python - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)
fi

printf 'GEARY_KEY=%s\n' "$key" > .env.local
printf 'export GEARY_KEY="%s"\n' "$key"
