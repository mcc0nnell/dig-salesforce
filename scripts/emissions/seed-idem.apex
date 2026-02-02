String stream = 'smoke';
String type = 'smoke.test';
String idempotencyKey = 'smoke-fixed-idem';
Map<String, Object> payload = new Map<String, Object>{'ping' => 'pong', 'ts' => DateTime.now().getTime()};
String payloadJson = JSON.serialize(payload);
EmissionService.appendOnce(stream, idempotencyKey, type, payloadJson, null, null, null, null);
