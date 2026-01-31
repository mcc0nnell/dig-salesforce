#!/usr/bin/env bash
set -euo pipefail

if [ -z "${ZSH_VERSION:-}" ]; then
  echo "This helper must run inside zsh because it edits ~/.zshrc." >&2
  exit 1
fi

HOME_CONFIG_DIR="$HOME/.config/geary"
HOME_ENV_FILE="$HOME_CONFIG_DIR/.env"
ZSHRC_FILE="$HOME/.zshrc"

mkdir -p "$HOME_CONFIG_DIR"

if [ ! -f "$HOME_ENV_FILE" ]; then
  cat <<'EOF' > "$HOME_ENV_FILE"
# GEARY_KEY is required for mermaid-runner; paste your generated key after the equals sign.
GEARY_KEY=
# Optional WORKER_URL override (leave empty for the default).
WORKER_URL=
EOF
  echo "Created $HOME_ENV_FILE. Edit it to paste your GEARY_KEY and optional WORKER_URL."
fi

SNIPPET_START='### geary-mermaid-runner env start'
SNIPPET_END='### geary-mermaid-runner env end'

touch "$ZSHRC_FILE"
if ! grep -Fq "$SNIPPET_START" "$ZSHRC_FILE"; then
  cat <<EOF >> "$ZSHRC_FILE"

$SNIPPET_START
if [ -f "$HOME/.config/geary/.env" ]; then
  set -a
  source "$HOME/.config/geary/.env"
  set +a
fi
$SNIPPET_END
EOF
  echo "Appended geary-mermaid-runner env snippet to $ZSHRC_FILE."
else
  echo "Geary snippet already present in $ZSHRC_FILE."
fi
