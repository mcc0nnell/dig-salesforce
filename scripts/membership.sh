#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/membership.sh <slice> <command>

Slices:
  mvp             manifest/membership-mvp-package.xml
  all             manifest/membership-all-package.xml
  update-status   manifest/membership-update-status-package.xml
  renewal-fields  manifest/membership-renewal-fields-package.xml

Commands:
  retrieve        Retrieve the slice
  deploy          Deploy the slice
  validate        Validate the slice (dry run)
USAGE
}

slice="${1:-}"
command="${2:-}"

if [ -z "$slice" ] || [ -z "$command" ]; then
  usage
  exit 1
fi

manifest=""
case "$slice" in
  mvp)
    manifest="manifest/membership-mvp-package.xml"
    ;;
  all)
    manifest="manifest/membership-all-package.xml"
    ;;
  update-status)
    manifest="manifest/membership-update-status-package.xml"
    ;;
  renewal-fields)
    manifest="manifest/membership-renewal-fields-package.xml"
    ;;
  *)
    echo "Unknown slice: $slice"
    usage
    exit 1
    ;;
esac

case "$command" in
  retrieve)
    sf project retrieve start --target-org deafingov --manifest "$manifest"
    ;;
  deploy)
    echo "Running make dig-validate (required before deploy)..."
    make dig-validate
    sf project deploy start --target-org deafingov --manifest "$manifest"
    ;;
  validate)
    sf project deploy start --target-org deafingov --manifest "$manifest" --dry-run
    ;;
  *)
    echo "Unknown command: $command"
    usage
    exit 1
    ;;
esac
