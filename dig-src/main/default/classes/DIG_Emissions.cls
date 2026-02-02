public class DIG_Emissions {
    public class EmitException extends Exception {}

    public class EmitRequest {
        public String runId;
        public Long seq;
        public String type;
        public String level;
        public String source;
        public String payloadJson;
        public String prevHash;
        public String idempotencyKey;
        public Datetime at;
    }

    public static Database.SaveResult emit(String runId, Long seq, String type, String level, String source, String payloadJson, String prevHash, String idempotencyKey) {
        EmitRequest req = new EmitRequest();
        req.runId = runId;
        req.seq = seq;
        req.type = type;
        req.level = level;
        req.source = source;
        req.payloadJson = payloadJson;
        req.prevHash = prevHash;
        req.idempotencyKey = idempotencyKey;
        return emit(req);
    }

    public static Database.SaveResult emit(DIG_Emissions.EmitRequest req) {
        if (req == null) {
            throw new EmitException('EmitRequest is required');
        }
        if (String.isBlank(req.runId)) {
            throw new EmitException('runId is required');
        }
        if (req.seq == null || req.seq < 1) {
            throw new EmitException('seq must be >= 1');
        }
        if (String.isBlank(req.type) || !req.type.startsWith('dig.')) {
            throw new EmitException('type must start with "dig."');
        }
        if (String.isBlank(req.level)) {
            throw new EmitException('level must be one of DEBUG/INFO/WARN/ERROR');
        }
        String level = req.level.trim().toUpperCase();
        Set<String> allowedLevels = new Set<String>{'DEBUG', 'INFO', 'WARN', 'ERROR'};
        if (!allowedLevels.contains(level)) {
            throw new EmitException('level must be one of DEBUG/INFO/WARN/ERROR');
        }
        if (String.isBlank(req.idempotencyKey)) {
            throw new EmitException('idempotencyKey is required');
        }
        if (String.isBlank(req.payloadJson)) {
            throw new EmitException('payloadJson is required');
        }

        String canonicalPayload = canonicalizePayload(req.payloadJson);
        Datetime atValue = req.at == null ? System.now() : req.at;
        String atIso = atValue.formatGMT('yyyy-MM-dd\'T\'HH:mm:ss.SSS\'Z\'');
        String prevHash = String.isBlank(req.prevHash) ? '' : req.prevHash;

        String envelope = req.runId
            + '|' + String.valueOf(req.seq)
            + '|' + req.type
            + '|' + level
            + '|' + (req.source == null ? '' : req.source)
            + '|' + atIso
            + '|' + prevHash
            + '|' + req.idempotencyKey
            + '|' + canonicalPayload;

        String hash = EncodingUtil.convertToHex(Crypto.generateDigest('SHA-256', Blob.valueOf(envelope))).toLowerCase();
        Datetime ingestedAt = System.now();

        DIG_Emission__e evt = new DIG_Emission__e(
            RunId__c = req.runId,
            Seq__c = Decimal.valueOf(req.seq),
            Type__c = req.type,
            Level__c = level,
            Source__c = req.source,
            At__c = atValue,
            IngestedAt__c = ingestedAt,
            PrevHash__c = prevHash,
            Hash__c = hash,
            IdempotencyKey__c = req.idempotencyKey,
            Payload__c = canonicalPayload
        );

        Database.SaveResult result = EventBus.publish(evt);
        if (!result.isSuccess()) {
            List<String> messages = new List<String>();
            for (Database.Error err : result.getErrors()) {
                messages.add(err.getStatusCode() + ': ' + err.getMessage());
            }
            throw new EmitException('Event publish failed: ' + String.join(messages, '; '));
        }
        return result;
    }

    private static String canonicalizePayload(String payloadJson) {
        Object parsed;
        try {
            parsed = JSON.deserializeUntyped(payloadJson);
        } catch (Exception e) {
            throw new EmitException('payloadJson must be valid JSON: ' + e.getMessage());
        }
        return toCanonicalJson(parsed);
    }

    private static String toCanonicalJson(Object value) {
        if (value == null) {
            return 'null';
        }

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
                String key = keys[i];
                if (i > 0) {
                    out += ',';
                }
                out += JSON.serialize(key) + ':' + toCanonicalJson(mapValue.get(key));
            }
            out += '}';
            return out;
        }

        if (value instanceof List<Object>) {
            List<Object> listValue = (List<Object>) value;
            String out = '[';
            for (Integer i = 0; i < listValue.size(); i++) {
                if (i > 0) {
                    out += ',';
                }
                out += toCanonicalJson(listValue[i]);
            }
            out += ']';
            return out;
        }

        return JSON.serialize(value);
    }
}
