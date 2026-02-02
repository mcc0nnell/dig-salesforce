# DIG Emissions smoke proof

## Schema snapshot (spine)
- Platform Event: `DIG_Emission__e`
  - `RunId__c`, `Seq__c`, `Type__c`, `Level__c`, `Source__c`, `At__c`, `IngestedAt__c`, `PrevHash__c`, `Hash__c`, `IdempotencyKey__c`, `Payload__c`
- Durable sink: `DIG_Emission__c`
  - Same envelope fields plus `Anomaly__c`, `AnomalyReason__c`, `ReplayHint__c`

## Smoke test proof
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

   String payload1 = '{"ping":"pong","n":1}';
   String hash1 = DigEmissionSmoke.hashEnvelope(runId, 1L, 'dig.system.heartbeat', level, source, atValue, '', 'idem-001', payload1);
   DIG_Emissions.emit(runId, 1L, 'dig.system.heartbeat', level, source, payload1, '', 'idem-001');

   String payload2 = '{"ping":"pong","n":2}';
   String hash2 = DigEmissionSmoke.hashEnvelope(runId, 2L, 'dig.system.heartbeat', level, source, atValue, hash1, 'idem-002', payload2);
   DIG_Emissions.emit(runId, 2L, 'dig.system.heartbeat', level, source, payload2, hash1, 'idem-002');
   ```
2) Run it:
   ```bash
   sf apex run --target-org deafingov --file /tmp/dig-emissions-smoke.apex
   ```
3) Query sink:
   ```bash
   sf data query --target-org deafingov -q "SELECT RunId__c, Seq__c, Type__c, PrevHash__c, Hash__c, IdempotencyKey__c, Anomaly__c FROM DIG_Emission__c WHERE RunId__c LIKE 'smoke-%' ORDER BY CreatedDate DESC LIMIT 10"
   ```

## Idempotency proof
1) Run the same script twice (fixed idempotency key) and confirm one sink record:
   ```bash
   sf apex run --target-org deafingov --file /tmp/dig-emissions-smoke.apex
   sf apex run --target-org deafingov --file /tmp/dig-emissions-smoke.apex
   sf data query --target-org deafingov -q "SELECT IdempotencyKey__c, COUNT(Id) c FROM DIG_Emission__c WHERE IdempotencyKey__c='idem-001' GROUP BY IdempotencyKey__c"
   ```

## Commands (copy/paste ready)
```
sf apex run --target-org deafingov --file /tmp/dig-emissions-smoke.apex
sf data query --target-org deafingov -q "SELECT RunId__c, Seq__c, Type__c, PrevHash__c, Hash__c, IdempotencyKey__c, Anomaly__c FROM DIG_Emission__c WHERE RunId__c LIKE 'smoke-%' ORDER BY CreatedDate DESC LIMIT 10"
```
