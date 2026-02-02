#!/usr/bin/env bash
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo 'jq is required but not installed.'
  exit 1
fi

echo '▶ Fetching credentials for deafingov org'
org_json=$(sf org display --target-org deafingov --json)
HOST=$(printf '%s' "$org_json" | jq -r '.result.instanceUrl')
TOKEN=$(printf '%s' "$org_json" | jq -r '.result.accessToken')

if [[ -z "$HOST" || -z "$TOKEN" ]]; then
  echo 'unable to extract host/token' >&2
  exit 1
fi

export HOST
export TOKEN

echo '▶ Verifying API reachability'
api_code=$(curl -sS -o /dev/null -w '%{http_code}' \
  -H "Authorization: Bearer $TOKEN" \
  "$HOST/services/data/v60.0/")
if [[ "$api_code" != '200' ]]; then
  echo "✗ Org API ping failed with HTTP $api_code"
  exit 1
fi

EMAIL="smoke+$(date -u +%Y%m%d-%H%M%S)@example.com"
export EMAIL

JOIN_URL="$HOST/services/apexrest/dig/membership/join"
TMP1=/tmp/dig-join1.json
TMP2=/tmp/dig-join2.json

function ensure_json_ok() {
  local file=$1
  local label=$2
  local ok
  ok=$(jq -r '.ok // "false"' "$file")
  if [[ "$ok" != 'true' ]]; then
    echo "✗ $label response ok!=true"
    cat "$file"
    exit 1
  fi
  for field in contactId membershipTermId receiptId; do
    if [[ -z $(jq -r --arg key "$field" '.[$key] // ""' "$file") ]]; then
      echo "✗ $label missing $field"
      cat "$file"
      exit 1
    fi
  done
}

function post_join() {
  local body=$1
  local dest=$2
  local label=$3
  echo "▶ Posting payload to $JOIN_URL ($label)"
  http_status=$(curl -sS -w '%{http_code}' -o "$dest" \
    -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    -d "$body" \
    "$JOIN_URL")
  if [[ "$http_status" != '200' ]]; then
    echo "✗ $label POST failed (HTTP $http_status)"
    cat "$dest"
    exit 1
  fi
  ensure_json_ok "$dest" "$label"
}

PAYLOAD1=$(jq -nc \
  --arg fn 'Smoke' --arg ln 'Test' --arg email "$EMAIL" --arg org 'Alpha' \
  --argjson optIn true --arg source 'smoke' \
  '{ firstName: $fn, lastName: $ln, email: $email, organization: $org, optInEmail: $optIn, source: $source }')
post_join "$PAYLOAD1" "$TMP1" 'join1'

PAYLOAD2=$(jq -nc \
  --arg fn 'Smoke' --arg ln 'Test' --arg email "$EMAIL" --arg org 'Beta' \
  --arg source 'smoke' \
  '{ firstName: $fn, lastName: $ln, email: $email, organization: $org, source: $source }')
post_join "$PAYLOAD2" "$TMP2" 'join2'

contactId1=$(jq -r '.contactId' "$TMP1")
contactId2=$(jq -r '.contactId' "$TMP2")
membershipTermId1=$(jq -r '.membershipTermId' "$TMP1")
membershipTermId2=$(jq -r '.membershipTermId' "$TMP2")
receiptId1=$(jq -r '.receiptId' "$TMP1")
receiptId2=$(jq -r '.receiptId' "$TMP2")

function assert_equal() {
  local name=$1
  local a=$2
  local b=$3
  if [[ "$a" != "$b" ]]; then
    echo "✗ $name mismatch ($a vs $b)"
    cat "$TMP1"
    cat "$TMP2"
    exit 1
  fi
}

assert_equal 'contactId' "$contactId1" "$contactId2"
assert_equal 'membershipTermId' "$membershipTermId1" "$membershipTermId2"
assert_equal 'receiptId' "$receiptId1" "$receiptId2"

function soql_query() {
  local query=$1
  echo "▶ Running SOQL: $query"
  sf data query --query "$query"
}

echo '▶ Validating Contact fields'
contact_query="SELECT Id,DIG_Organization__c,DIG_Email_Opt_In__c FROM Contact WHERE Id='${contactId1}'"
soql_query "$contact_query"

term_query="SELECT Id,Term_Start__c,Term_End__c,Status__c FROM Membership_Term__c WHERE Contact__c='${contactId1}' AND Status__c='Active' AND Term_Start__c <= TODAY AND Term_End__c >= TODAY ORDER BY Term_Start__c DESC"
soql_query "$term_query"

echo '▶ Verifying receipt record'
receipt_query="SELECT Id,External_Id__c,Type__c FROM Receipt__c WHERE External_Id__c='${receiptId1}'"
soql_query "$receipt_query"

cat <<-PASS
PASS: Idempotency validated
contactId=$contactId1
membershipTermId=$membershipTermId1
receiptId=$receiptId1
PASS

cat <<'NOTE'
Cleanup tip: delete the Contact, related Membership_Term__c, and Receipt__c created for $EMAIL if you no longer need the smoke data.
NOTE
