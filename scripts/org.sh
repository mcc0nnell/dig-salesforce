#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/org.sh <command>

Commands:
  display   Show org details for deafingov
  list      List authorized orgs
USAGE
}

command="${1:-}"
if [ -z "$command" ]; then
  usage
  exit 1
fi

case "$command" in
  display)
    sf org display --target-org deafingov
    ;;
  list)
    sf org list
    ;;
  *)
    echo "Unknown command: $command"
    usage
    exit 1
    ;;
esac
