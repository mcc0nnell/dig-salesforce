trigger DIG_EmissionSinkTrigger on DIG_Emission__e (after insert) {
    if (Trigger.new == null || Trigger.new.isEmpty()) {
        return;
    }

    Set<String> idempotencyKeys = new Set<String>();
    Set<String> runIds = new Set<String>();
    Set<Decimal> seqs = new Set<Decimal>();

    for (DIG_Emission__e evt : Trigger.new) {
        if (!String.isBlank(evt.IdempotencyKey__c)) {
            idempotencyKeys.add(evt.IdempotencyKey__c);
        }
        if (!String.isBlank(evt.RunId__c)) {
            runIds.add(evt.RunId__c);
        }
        if (evt.Seq__c != null) {
            seqs.add(evt.Seq__c);
        }
    }

    Map<String, DIG_Emission__c> existingByIdem = new Map<String, DIG_Emission__c>();
    if (!idempotencyKeys.isEmpty()) {
        for (DIG_Emission__c rec : [
            SELECT Id, IdempotencyKey__c
            FROM DIG_Emission__c
            WHERE IdempotencyKey__c IN :idempotencyKeys
        ]) {
            existingByIdem.put(rec.IdempotencyKey__c, rec);
        }
    }

    Set<String> existingRunSeq = new Set<String>();
    if (!runIds.isEmpty() && !seqs.isEmpty()) {
        for (DIG_Emission__c rec : [
            SELECT Id, RunId__c, Seq__c
            FROM DIG_Emission__c
            WHERE RunId__c IN :runIds
            AND Seq__c IN :seqs
        ]) {
            if (rec.RunId__c != null && rec.Seq__c != null) {
                existingRunSeq.add(rec.RunId__c + '|' + String.valueOf(rec.Seq__c));
            }
        }
    }

    List<DIG_Emission__c> toInsert = new List<DIG_Emission__c>();
    Set<String> seenIdem = new Set<String>();

    for (DIG_Emission__e evt : Trigger.new) {
        String idem = String.isBlank(evt.IdempotencyKey__c) ? null : evt.IdempotencyKey__c;
        if (idem != null && (existingByIdem.containsKey(idem) || seenIdem.contains(idem))) {
            continue;
        }
        if (idem != null) {
            seenIdem.add(idem);
        }

        DIG_Emission__c sink = new DIG_Emission__c();
        sink.RunId__c = evt.RunId__c;
        sink.Seq__c = evt.Seq__c;
        sink.Type__c = evt.Type__c;
        sink.Level__c = evt.Level__c;
        sink.Source__c = evt.Source__c;
        sink.At__c = evt.At__c;
        sink.IngestedAt__c = evt.IngestedAt__c;
        sink.PrevHash__c = evt.PrevHash__c;
        sink.Hash__c = evt.Hash__c;
        sink.IdempotencyKey__c = evt.IdempotencyKey__c;
        sink.Payload__c = evt.Payload__c;

        List<String> reasons = new List<String>();
        if (evt.Seq__c != null && evt.Seq__c > 1 && String.isBlank(evt.PrevHash__c)) {
            reasons.add('PrevHash missing for seq > 1');
        }
        if (evt.Seq__c != null && evt.Seq__c == 1 && !String.isBlank(evt.PrevHash__c)) {
            reasons.add('PrevHash present for seq = 1');
        }
        if (!String.isBlank(evt.RunId__c) && evt.Seq__c != null) {
            String runSeqKey = evt.RunId__c + '|' + String.valueOf(evt.Seq__c);
            if (existingRunSeq.contains(runSeqKey)) {
                reasons.add('Duplicate RunId/Seq detected');
            }
        }

        if (!reasons.isEmpty()) {
            sink.Anomaly__c = true;
            sink.AnomalyReason__c = String.join(reasons, '; ');
        }

        toInsert.add(sink);
    }

    if (!toInsert.isEmpty()) {
        insert toInsert;
    }
}
