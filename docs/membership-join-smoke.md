# Membership Join Smoke Test

This document captures the post-deploy smoke check that keeps the Membership Join MVP deterministic and idempotent.

## What it covers
- Ensures the Apex REST endpoint `/services/apexrest/dig/membership/join` accepts JSON, returns `ok=true`, and provides `contactId`, `membershipTermId`, and `receiptId`.
- Verifies the service does not duplicate terms or receipts when the same email+term window is resubmitted.
- Confirms deterministic Contact behavior: `DIG_Organization__c` retains the first non-empty organization value, and `DIG_Email_Opt_In__c` is monotonic (true stays true).

## Running the check
Use the CLI wrapper added to `make dig-validate-smoke`:

```
make dig-validate-smoke ORG=deafingov
```

This runs `make dig-validate` followed by `dig-smoke-membership-join.sh`, which:

1. Acquires `HOST`/`TOKEN` via `sf org display`.
2. Posts once with `organization=Alpha`/`optInEmail=true` and again with the same email plus `organization=Beta` (no opt-in flag).
3. Asserts both responses share the same IDs and `ok=true`.
4. Queries the Contact, Membership_Term__c, and Receipt__c records to confirm the expected fields.

## Expected PASS criteria
- Both REST responses return HTTP 200 with `{ "ok": true, ... }` and identical IDs.
- The Contact record retains `DIG_Organization__c = 'Alpha'` and `DIG_Email_Opt_In__c = true`.
- Exactly one active `Membership_Term__c` exists for the contact covering today.
- Exactly one `Receipt__c` record matches the deterministic `receiptId` (by `External_Id__c`).

## Failure handling
- If the script exits non-zero, the last HTTP response body and SOQL output are printed to help debug.
- Inspect `/tmp/dig-join1.json`/`/tmp/dig-join2.json` for unexpected payloads.
- Look in Salesforce: the exposed field values on Contact, Membership_Term__c, and Receipt__c may show inconsistent data.

## Cleanup (optional)
To remove the smoke data, run (adjust `EMAIL` to match the script run):

```
EMAIL=smoke+YYYYMMDD-HHMMSS@example.com
CONTACT_ID=$(sf data query --query "SELECT Id FROM Contact WHERE Email='$EMAIL'" --result-format csv | tail -n +2)
sf data delete record --sobject Contact --target-org deafingov --record-id "$CONTACT_ID"
sf data delete bulk --sobject Membership_Term__c --target-org deafingov --where "Contact__r.Email='$EMAIL'"
sf data delete bulk --sobject Receipt__c --target-org deafingov --where "External_Id__c='RECEIPT_KEY'"
```

If necessary, adjust the `Receipt__c` delete by replacing `RECEIPT_KEY` with the `receiptId` returned from the smoke script.
