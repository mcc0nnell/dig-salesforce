#!/usr/bin/env bash
set -euo pipefail

sf project deploy start --target-org deafingov --manifest manifest/email-comms.xml
