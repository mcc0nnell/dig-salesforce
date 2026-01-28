public with sharing class CommsInvocable {
    public class Request {
        @InvocableVariable(required=true) public Id recordId;
        @InvocableVariable public Id contactId;
        @InvocableVariable(required=true) public String toAddress;
        @InvocableVariable(required=true) public String subject;
        @InvocableVariable public String bodyText;
    }

    public class Result {
        @InvocableVariable public Id commsMessageId;
        @InvocableVariable public String status;
        @InvocableVariable public String error;
    }

    @InvocableMethod(label='Send Comms Email' description='Queues an email send and logs a Comms Message record.')
    public static List<Result> sendEmail(List<Request> requests) {
        List<Result> results = new List<Result>();
        for (Request r : requests) {
            Result res = new Result();
            try {
                CommsService.SendRequest sr = new CommsService.SendRequest();
                sr.recordId = r.recordId;
                sr.contactId = r.contactId;
                sr.toAddress = r.toAddress;
                sr.subject = r.subject;
                sr.bodyText = r.bodyText;
                res.commsMessageId = CommsService.sendEmail(sr);
                res.status = 'Queued';
            } catch (Exception e) {
                res.status = 'Failed';
                res.error = e.getMessage();
            }
            results.add(res);
        }
        return results;
    }
}
