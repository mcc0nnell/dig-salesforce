public with sharing class EmissionAppendAction {
    public class Input {
        @InvocableVariable public String stream;
        @InvocableVariable public String type;
        @InvocableVariable public String payloadJson;
        @InvocableVariable public String idempotencyKey;
        @InvocableVariable public Id contactId;
        @InvocableVariable public Id membershipTermId;
        @InvocableVariable public Id receiptId;
    }

    public class Output {
        @InvocableVariable public Id emissionId;
        @InvocableVariable public Long sequence;
    }

    @InvocableMethod
    public static List<Output> run(List<Input> reqs) {
        List<Output> outs = new List<Output>();
        if (reqs == null) return outs;

        for (Input r : reqs) {
            Output o = new Output();

            if (r == null || r.stream == null || r.stream == '' || r.type == null || r.type == '') {
                outs.add(o);
                continue;
            }

            Object payloadObj = null;
            if (r.payloadJson != null && r.payloadJson != '') {
                payloadObj = JSON.deserializeUntyped(r.payloadJson);
            }

            // Call EmissionService method that exists.
            // Preferred: EmissionService.appendOnce(stream, type, payloadObj, idempotencyKey, contactId, membershipTermId, receiptId)
            Emission__c e = EmissionService.appendOnce(
                r.stream, r.type, payloadObj, r.idempotencyKey, r.contactId, r.membershipTermId, r.receiptId
            );

            o.emissionId = e.Id;
            if (e.Sequence_Num__c != null) o.sequence = e.Sequence_Num__c.longValue();
            outs.add(o);
        }
        return outs;
    }
}
