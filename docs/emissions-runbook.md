# DIG Emissions runbook (deafingov)

## Known-good environment
- Org alias: `deafingov`
- Username: `robert.mcconnell@deafingov.org`

## Schema snapshot
- Platform Event: `DIG_Emission__e` (event bus)
- Durable sink: `DIG_Emission__c` (evidence/audit)

## Schema proof
1) Describe `DIG_Emission__e` (check fields exist):
   ```bash
   sf sobject describe --target-org deafingov --sobject DIG_Emission__e --json > /tmp/dig_emission_event_describe.json
   python3 - <<'PY'
   import json
   d=json.load(open('/tmp/dig_emission_event_describe.json'))
   fields=[f['name'] for f in d['result']['fields']]
   required=['RunId__c','Seq__c','Type__c','Level__c','Source__c','At__c','IngestedAt__c','PrevHash__c','Hash__c','IdempotencyKey__c','Payload__c']
   print('MISSING:', [f for f in required if f not in fields])
   PY
   ```
2) Describe `DIG_Emission__c` (check anomaly fields):
   ```bash
   sf sobject describe --target-org deafingov --sobject DIG_Emission__c --json > /tmp/dig_emission_sink_describe.json
   python3 - <<'PY'
   import json
   d=json.load(open('/tmp/dig_emission_sink_describe.json'))
   fields=[f['name'] for f in d['result']['fields']]
   required=['RunId__c','Seq__c','Type__c','Level__c','Source__c','At__c','IngestedAt__c','PrevHash__c','Hash__c','IdempotencyKey__c','Payload__c','Anomaly__c','AnomalyReason__c']
   print('MISSING:', [f for f in required if f not in fields])
   PY
   ```

## Smoke publish (Platform Event + sink)
1) Create `/tmp/dig-emissions-smoke.apex`:
   ```apex
   public class DigEmissionSmoke {
       private static String canonicalize(Object value) {
           if (value == null) return 'null';
           if (value instanceof String || value instanceof Boolean || value instanceof Integer || value instanceof Long
               || value instanceof Decimal || value instanceof Double || value instanceof Date || value instanceof Datetime) {
               return JSON.serialize(value);
           }
           if (value instanceof Map<String, Object>) {
               Map<String, Object> mapValue = (Map<String, Object>) value;
               List<String> keys = new List<String>(mapValue.keySet());
               keys.sort();
               String out = '{';
               for (Integer i = 0; i < keys.size(); i++) {
                   if (i > 0) out += ',';
                   String key = keys[i];
                   out += JSON.serialize(key) + ':' + canonicalize(mapValue.get(key));
               }
               return out + '}';
           }
           if (value instanceof List<Object>) {
               List<Object> listValue = (List<Object>) value;
               String out = '[';
               for (Integer i = 0; i < listValue.size(); i++) {
                   if (i > 0) out += ',';
                   out += canonicalize(listValue[i]);
               }
               return out + ']';
           }
           return JSON.serialize(value);
       }

       private static String hashEnvelope(String runId, Long seq, String type, String level, String source,
           Datetime atValue, String prevHash, String idemKey, String payloadJson) {
           String canonicalPayload = canonicalize(JSON.deserializeUntyped(payloadJson));
           String atIso = atValue.formatGMT('yyyy-MM-dd\'T\'HH:mm:ss.SSS\'Z\'');
           String envelope = runId + '|' + String.valueOf(seq) + '|' + type + '|' + level + '|' + source
               + '|' + atIso + '|' + (String.isBlank(prevHash) ? '' : prevHash) + '|' + idemKey + '|' + canonicalPayload;
           return EncodingUtil.convertToHex(Crypto.generateDigest('SHA-256', Blob.valueOf(envelope))).toLowerCase();
       }
   }

   String runId = 'smoke-' + String.valueOf(DateTime.now().getTime());
   String source = 'dig.sf.geary';
   String level = 'INFO';
   Datetime atValue = System.now();

   String payload1 = '{"action":"heartbeat","n":1}';
   String hash1 = DigEmissionSmoke.hashEnvelope(runId, 1L, 'dig.system.heartbeat', level, source, atValue, '', 'idem-001', payload1);
   DIG_Emissions.emit(runId, 1L, 'dig.system.heartbeat', level, source, payload1, '', 'idem-001');

   String payload2 = '{"action":"heartbeat","n":2}';
   String hash2 = DigEmissionSmoke.hashEnvelope(runId, 2L, 'dig.system.heartbeat', level, source, atValue, hash1, 'idem-002', payload2);
   DIG_Emissions.emit(runId, 2L, 'dig.system.heartbeat', level, source, payload2, hash1, 'idem-002');
   ```
2) Run it:
   ```bash
   sf apex run --target-org deafingov --file /tmp/dig-emissions-smoke.apex
   ```
3) Verify sink:
   ```bash
   sf data query --target-org deafingov -q "SELECT RunId__c, Seq__c, Type__c, PrevHash__c, Hash__c, IdempotencyKey__c, Anomaly__c FROM DIG_Emission__c WHERE RunId__c LIKE 'smoke-%' ORDER BY CreatedDate DESC LIMIT 10"
   ```
   *Expected:* `Anomaly__c = false` and proper PrevHash/Hash chaining.

## Idempotency proof (fixed idempotency key)
1) Run the same script twice:
   ```bash
   sf apex run --target-org deafingov --file /tmp/dig-emissions-smoke.apex
   sf apex run --target-org deafingov --file /tmp/dig-emissions-smoke.apex
   ```
2) Confirm only one sink record per key:
   ```bash
   sf data query --target-org deafingov -q "SELECT IdempotencyKey__c, COUNT(Id) c FROM DIG_Emission__c WHERE IdempotencyKey__c IN ('idem-001','idem-002') GROUP BY IdempotencyKey__c"
   ```

## LWC console
- Add `digEmissionsConsole` to an App Page or Home Page.
- Assign `DIG_Emissions_Perms` to the user.
- The console subscribes to `/event/DIG_Emission__e` and shows the last 500 events.

## If it fails
- `No such column`: re-run the describe checks above.
- `Event publish failed`: ensure permission set includes Create on `DIG_Emission__e`.
- `Anomaly__c = true`: check PrevHash rules and ensure seq=1 uses blank PrevHash.
