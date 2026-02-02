#!/usr/bin/env bash
set -euo pipefail

# Acceptance tests:
# 1. ./dig-verify-emissions-idem.sh deafingov → PASS when no duplicates.
# 2. Introduce dupes → script exits 1 and prints duplicate groups.
# 3. Script never fails with JSONDecodeError; it always parses --json output.

usage() {
  cat <<'USAGE'
Usage:
  ./dig-verify-emissions-idem.sh [orgAlias]

Examples:
  ./dig-verify-emissions-idem.sh deafingov
  ./dig-verify-emissions-idem.sh  # defaults to deafingov
USAGE
  exit 2
}

if [[ $# -gt 1 ]]; then
  usage
fi

ORG="${1:-deafingov}"

extract_json() {
  python3 <<'PY'
import json
import sys
raw = sys.stdin.read()
idx = raw.find('{')
if idx == -1:
    sys.stderr.write('FAIL: No JSON object found in sf output\n')
    sys.stderr.write(raw)
    sys.exit(1)
try:
    parsed = json.loads(raw[idx:])
except json.JSONDecodeError as exc:
    sys.stderr.write(f'FAIL: Could not parse JSON: {exc}\n')
    sys.stderr.write(raw)
    sys.exit(1)
print(json.dumps(parsed))
PY
}

run_query() {
  local soql="$1"
  local output
  output=$(sf data query --target-org "${ORG}" --json -q "${soql}" 2>&1)
  local rc=$?
  printf '%s' "${output}"
  return ${rc}
}

PROBE_QUERY="SELECT Stream_Seq__c FROM Emission__c LIMIT 1"
PROBE_OUT="$(run_query "${PROBE_QUERY}")"
PROBE_RC=$?

MODE=stream_seq
KEY_FIELD=Stream_Seq__c
MODE_DESC="Stream_Seq__c"
QUERY="SELECT Stream__c, Type__c, Stream_Seq__c, COUNT(Id) c\nFROM Emission__c\nGROUP BY Stream__c, Type__c, Stream_Seq__c\nHAVING COUNT(Id) > 1"

if [[ ${PROBE_RC} -ne 0 ]]; then
  MODE=name
  KEY_FIELD=Name
  MODE_DESC="Name fallback"
  QUERY="SELECT Stream__c, Type__c, Name, COUNT(Id) c\nFROM Emission__c\nGROUP BY Stream__c, Type__c, Name\nHAVING COUNT(Id) > 1"
  echo "WARN: Stream_Seq__c probe failed (exit ${PROBE_RC}); falling back to Name mode." >&2
fi

printf 'Checking Emission__c dedupe via %s for org %s...\n' "${MODE_DESC}" "${ORG}"

DEDUP_OUT="$(run_query "${QUERY}")"
DEDUP_RC=$?
if [[ ${DEDUP_RC} -ne 0 ]]; then
  echo "FAIL: sf data query failed (exit ${DEDUP_RC})." >&2
  printf '%s\n' "${DEDUP_OUT}" >&2
  exit 1
fi

JSON_OUT="$(extract_json <<< "${DEDUP_OUT}")"
TOTAL="$(printf '%s' "${JSON_OUT}" | python3 <<'PY'
import json
import sys
obj = json.loads(sys.stdin.read())
print(obj.get('result', {}).get('totalSize', 0))
PY
)"

echo "Using key ${KEY_FIELD}."
if [[ "${TOTAL}" -eq 0 ]]; then
  echo "PASS: No duplicate emission groups found."
  exit 0
fi

echo "FAIL: Duplicate emission groups found (${TOTAL} rows)."
echo "Duplicate groups (Stream, Type, ${KEY_FIELD}, Count):"
printf '%s\n' "${JSON_OUT}" | python3 - "${KEY_FIELD}" <<'PY'
import json
import sys
key_field = sys.argv[1]
obj = json.loads(sys.stdin.read())
for record in obj.get('result', {}).get('records', []):
    stream = record.get('Stream__c', '')
    typ = record.get('Type__c', '')
    key = record.get(key_field, '')
    count = record.get('c', '')
    print(f"{stream}\t{typ}\t{key}\t{count}")
PY
exit 1
