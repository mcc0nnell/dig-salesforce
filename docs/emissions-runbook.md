# DIG Emissions runbook (deafingov)

## Known-good environment
- Org alias: `deafingov`
- Username: `robert.mcconnell@deafingov.org`

## Schema snapshot
- `Emission__c` fields: `Stream__c`, `Type__c`, `Sequence__c`, `OccurredAt__c`, `Stream_Seq__c`, `Idempotency_Key__c`, `Stream_Idem__c`.
- `Emission_Stream__c` fields: `Name`, `Next_Sequence__c`, `Last_Hash__c`.

## Schema proof
1. Describe command (JSON contains `Stream_Seq__c`):
   ```bash
   sf sobject describe --target-org deafingov --sobject Emission__c --json > /tmp/emission_describe.json
   python3 - <<'PY'
   import json
   d=json.load(open("/tmp/emission_describe.json"))
   fields=[f["name"] for f in d["result"]["fields"]]
   print("HAS Stream_Seq__c:", "Stream_Seq__c" in fields)
   PY
   ```
   *Expected output:* `HAS Stream_Seq__c: True`
2. Query to prove `Stream_Seq__c` is queryable:
   ```bash
   sf data query --target-org deafingov -q "SELECT Id, Stream_Seq__c FROM Emission__c LIMIT 1"
   ```

## Smoke append (stream allocator + emission)
1. Create `/tmp/seed-emission.apex`:
   ```apex
   String stream = 'smoke';
   String typ = 'smoke.test';
   String idem = 'smoke-' + String.valueOf(DateTime.now().getTime());

   Map<String,Object> payload = new Map<String,Object>{
     'ping' => 'pong',
     'ts' => DateTime.now().formatGmt('yyyy-MM-dd\'T\'HH:mm:ss\'Z\'')
   };

   EmissionService.appendOnce(stream, typ, payload, idem, null, null, null);
   System.debug('OK: appended emission');
   ```
2. Run it:
   ```bash
   sf apex run --target-org deafingov --file /tmp/seed-emission.apex
   ```
3. Verify allocator row:
   ```bash
   sf data query --target-org deafingov -q "SELECT Id, Name, Next_Sequence__c, Last_Hash__c, CreatedDate, LastModifiedDate FROM Emission_Stream__c WHERE Name='smoke' LIMIT 1"
   ```
   *Expected:* `Next_Sequence__c` increments (e.g., 2 after first append).
4. Verify emissions include `Stream_Seq__c`:
   ```bash
   sf data query --target-org deafingov -q "SELECT Id, Stream__c, Type__c, Sequence__c, Stream_Seq__c, OccurredAt__c, CreatedDate FROM Emission__c WHERE Stream__c='smoke' ORDER BY CreatedDate DESC LIMIT 10"
   ```
   *Expected:* `Stream_Seq__c` values like `smoke:1`, `smoke:2`.

## Idempotency proof (fixed idem key)
1. Create `/tmp/seed-idem.apex`:
   ```apex
   String stream = 'smoke';
   String typ = 'smoke.test';
   String idem = 'smoke-fixed-idem';

   Map<String,Object> payload = new Map<String,Object>{
     'ping' => 'pong',
     'ts' => DateTime.now().formatGmt('yyyy-MM-dd\'T\'HH:mm:ss\'Z\'')
   };

   EmissionService.appendOnce(stream, typ, payload, idem, null, null, null);
   System.debug('OK: appended emission with idem=' + idem);
   ```
2. Run it twice:
   ```bash
   sf apex run --target-org deafingov --file /tmp/seed-idem.apex
   sf apex run --target-org deafingov --file /tmp/seed-idem.apex
   ```
3. Reminder: field name is `Idempotency_Key__c` (not `IdempotencyKey__c`).
4. Query the idempotent emission:
   ```bash
   sf data query --target-org deafingov -q "SELECT Id, Stream__c, Type__c, Stream_Seq__c, Idempotency_Key__c, CreatedDate FROM Emission__c WHERE Stream__c='smoke' AND Type__c='smoke.test' AND Idempotency_Key__c='smoke-fixed-idem' ORDER BY CreatedDate DESC"
   ```
5. Dedupe check (should return 0 rows):
   ```bash
   sf data query --target-org deafingov -q "SELECT Stream__c, Type__c, Stream_Seq__c, COUNT(Id) c FROM Emission__c WHERE Stream__c='smoke' AND Type__c='smoke.test' GROUP BY Stream__c, Type__c, Stream_Seq__c HAVING COUNT(Id) > 1"
   ```

## Verifier
- Run `./dig-verify-emissions-idem.sh deafingov`.
- Expected: script chooses Stream_Seq__c mode and prints `PASS: No duplicate emission groups found.` when duplicates are absent.
- Name fallback exists but should not trigger because `Stream_Seq__c` is queryable.

## If it fails
- `No such column 'Stream_Seq__c'`: rerun the describe JSON check above to confirm the field exists before re-running verifier.
- `sf apex run --file -` errors: write the script to `/tmp/seed-*.apex` and run against that file instead of piping.
- `IdempotencyKey__c` errors: correct the filter to use `Idempotency_Key__c`.
