public with sharing class CommsSendQueueable implements Queueable {
    private Id msgId;

    public CommsSendQueueable(Id commsMessageId) {
        this.msgId = commsMessageId;
    }

    public void execute(QueueableContext context) {
        Comms_Message__c msg = [
            SELECT Id, To__c, Subject__c, Body_Text__c, Status__c, Error__c
            FROM Comms_Message__c
            WHERE Id = :msgId
            LIMIT 1
        ];

        try {
            Messaging.SingleEmailMessage sem = new Messaging.SingleEmailMessage();
            sem.setToAddresses(new String[] { msg.To__c });
            sem.setSubject(msg.Subject__c);
            sem.setPlainTextBody(msg.Body_Text__c);

            // NOTE: If you want an Org-Wide Email Address, set it here:
            // sem.setOrgWideEmailAddressId('<ORG_WIDE_EMAIL_ADDRESS_ID>');

            Messaging.SendEmailResult[] results = Messaging.sendEmail(new Messaging.SingleEmailMessage[] { sem }, false);

            if (results != null && results.size() > 0 && results[0].isSuccess()) {
                msg.Status__c = 'Sent';
                msg.Sent_At__c = System.now();
                msg.Error__c = null;
            } else {
                msg.Status__c = 'Failed';
                msg.Error__c = (results != null && results.size() > 0 && results[0].getErrors().size() > 0)
                    ? results[0].getErrors()[0].getMessage()
                    : 'Unknown send failure.';
            }
        } catch (Exception e) {
            msg.Status__c = 'Failed';
            msg.Error__c = e.getMessage();
        }

        update msg;
    }
}
