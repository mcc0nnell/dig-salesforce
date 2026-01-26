#!/usr/bin/env bash
set -euo pipefail

sf project retrieve start --target-org deafingov --manifest manifest/email-comms.xml
