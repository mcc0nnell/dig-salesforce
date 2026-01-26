#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/governance.sh <command>

Commands:
  retrieve   Retrieve governance MVP metadata
  deploy     Deploy governance MVP metadata
  validate   Validate governance MVP deployment (dry run)
USAGE
}

command="${1:-}"
if [ -z "$command" ]; then
  usage
  exit 1
fi

case "$command" in
  retrieve)
    sf project retrieve start --target-org deafingov --manifest manifest/governance-mvp-package.xml
    ;;
  deploy)
    echo "Running make dig-validate (required before deploy)..."
    make dig-validate
    sf project deploy start --target-org deafingov --manifest manifest/governance-mvp-package.xml
    ;;
  validate)
    sf project deploy start --target-org deafingov --manifest manifest/governance-mvp-package.xml --dry-run
    ;;
  *)
    echo "Unknown command: $command"
    usage
    exit 1
    ;;
esac
