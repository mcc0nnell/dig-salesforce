#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/events.sh <command>

Commands:
  retrieve   Retrieve Summit UI slice
  deploy     Deploy Summit UI slice
  validate   Validate Summit UI slice (dry run)
USAGE
}

command="${1:-}"
if [ -z "$command" ]; then
  usage
  exit 1
fi

case "$command" in
  retrieve)
    sf project retrieve start --target-org deafingov --manifest manifest/summit-ui.xml
    ;;
  deploy)
    echo "Running make dig-validate (required before deploy)..."
    make dig-validate
    sf project deploy start --target-org deafingov --manifest manifest/summit-ui.xml
    ;;
  validate)
    sf project deploy start --target-org deafingov --manifest manifest/summit-ui.xml --dry-run
    ;;
  *)
    echo "Unknown command: $command"
    usage
    exit 1
    ;;
esac
