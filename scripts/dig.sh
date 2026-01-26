#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/dig.sh <command>

Commands:
  retrieve   Retrieve canonical DIG slice
  deploy     Deploy canonical DIG slice
  validate   Validate canonical DIG slice (dry run)
USAGE
}

command="${1:-}"
if [ -z "$command" ]; then
  usage
  exit 1
fi

case "$command" in
  retrieve)
    sf project retrieve start --target-org deafingov --manifest manifest/dig.xml
    ;;
  deploy)
    echo "Running make dig-validate (required before deploy)..."
    make dig-validate
    sf project deploy start --target-org deafingov --manifest manifest/dig.xml
    ;;
  validate)
    sf project deploy start --target-org deafingov --manifest manifest/dig.xml --dry-run
    ;;
  *)
    echo "Unknown command: $command"
    usage
    exit 1
    ;;
esac
