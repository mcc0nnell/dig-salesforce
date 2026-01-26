#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/email-comms.sh <command>

Commands:
  retrieve   Retrieve email/comms metadata
  deploy     Deploy email/comms metadata
  validate   Validate email/comms deployment (dry run)
USAGE
}

command="${1:-}"
if [ -z "$command" ]; then
  usage
  exit 1
fi

case "$command" in
  retrieve)
    sf project retrieve start --target-org deafingov --manifest manifest/email-comms.xml
    ;;
  deploy)
    echo "Running make dig-validate (required before deploy)..."
    make dig-validate
    sf project deploy start --target-org deafingov --manifest manifest/email-comms.xml
    ;;
  validate)
    sf project deploy start --target-org deafingov --manifest manifest/email-comms.xml --dry-run
    ;;
  *)
    echo "Unknown command: $command"
    usage
    exit 1
    ;;
esac
