# DIG Emissions (Platform Event Spine)

## Definition
"Emissions" are append-only, deterministic, evidence-grade event envelopes produced by DIG systems. Each emission is a canonicalized JSON payload wrapped in a hash-chained envelope for auditability, replay, and integrity checks.

## Why Platform Events + Durable Sink
- Platform Events provide low-latency, decoupled delivery to internal subscribers.
- The durable sink object (DIG_Emission__c) is the source of truth for audit, evidence, and replay because Platform Event retention is temporary.

## Envelope format
Each event is published with a canonical envelope used to compute Hash__c:

envelope =
  runId + "|" + seq + "|" + type + "|" + level + "|" + source + "|" + atIso + "|" + prevHashOrEmpty + "|" + idempotencyKey + "|" + canonicalPayload

- atIso is UTC ISO8601 with milliseconds (e.g., 2026-02-01T05:12:34.567Z).
- Hash__c is SHA-256 hex (lowercase) of the envelope bytes (UTF-8).
- PrevHash__c is blank only for seq=1; otherwise it chains to the previous Hash__c in the same RunId.

### Fields
Platform Event: DIG_Emission__e
- RunId__c (Text 64)
- Seq__c (Number 18,0)
- Type__c (Text 128) in the dig.* namespace
- Level__c (Picklist: DEBUG, INFO, WARN, ERROR)
- Source__c (Text 80)
- At__c (Date/Time)
- IngestedAt__c (Date/Time)
- PrevHash__c (Text 64)
- Hash__c (Text 64)
- IdempotencyKey__c (Text 80)
- Payload__c (Long Text Area 131072)

Durable Sink: DIG_Emission__c
- Same envelope fields as DIG_Emission__e
- Anomaly__c (Checkbox)
- AnomalyReason__c (Text Area 32768)
- ReplayHint__c (Text 80)

## Idempotency rules
- Primary dedupe is IdempotencyKey__c (unique on DIG_Emission__c).
- Secondary sanity: (RunId__c, Seq__c) should be unique; duplicates are stored but flagged as anomalies.

## Event type namespace
All Type__c values must start with "dig.".
Examples:
- dig.system.heartbeat
- dig.membership.renewal.planned
- dig.membership.renewal.completed

## How to publish (anonymous Apex example)
This example emits three chained events by computing the hashes in the same way as DIG_Emissions.

```apex
public class DigEmissionDemo {
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

String runId = 'run-2026-02-02-001';
String source = 'dig.sf.geary';
String level = 'INFO';
Datetime atValue = System.now();

String payload1 = '{"action":"heartbeat","n":1}';
String hash1 = DigEmissionDemo.hashEnvelope(runId, 1L, 'dig.system.heartbeat', level, source, atValue, '', 'idem-001', payload1);
DIG_Emissions.emit(runId, 1L, 'dig.system.heartbeat', level, source, payload1, '', 'idem-001');

String payload2 = '{"action":"heartbeat","n":2}';
String hash2 = DigEmissionDemo.hashEnvelope(runId, 2L, 'dig.system.heartbeat', level, source, atValue, hash1, 'idem-002', payload2);
DIG_Emissions.emit(runId, 2L, 'dig.system.heartbeat', level, source, payload2, hash1, 'idem-002');

String payload3 = '{"action":"heartbeat","n":3}';
String hash3 = DigEmissionDemo.hashEnvelope(runId, 3L, 'dig.system.heartbeat', level, source, atValue, hash2, 'idem-003', payload3);
DIG_Emissions.emit(runId, 3L, 'dig.system.heartbeat', level, source, payload3, hash2, 'idem-003');
```

## How to view
- Add the LWC `digEmissionsConsole` to an App Page or Home Page.
- Assign the `DIG_Emissions_Perms` permission set to the viewing user.
- The console subscribes to `/event/DIG_Emission__e` and displays the last 500 events client-side.

## Retention note
Platform Events are not permanent. The durable sink `DIG_Emission__c` is the system of record for audit, evidence, and replay.

## Smoke test checklist
1) Assign permission set: DIG_Emissions_Perms to your user.
2) Open the App Page containing the DIG Emissions console.
3) In Dev Console > Anonymous Apex, run the publish example above.
4) Confirm new rows appear in the console with correct RunId/Seq/Type/Level.
5) Open a DIG_Emission__c record and verify Hash__c and PrevHash__c chain correctly.
6) Verify Anomaly__c is false for the emitted records.
7) Toggle Pause/Resume and confirm no new events arrive while paused.
