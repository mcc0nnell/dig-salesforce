public with sharing class CommsService {
    public class ConsentCheck {
        public Boolean allowed;
        public String reason;
    }

    public class ConsentException extends Exception {}

    public class DefaultsDTO {
        @AuraEnabled public Id contactId;
        @AuraEnabled public String toEmail;
    }

    public class MessageDTO {
        @AuraEnabled public Id id;
        @AuraEnabled public String direction;
        @AuraEnabled public String channel;
        @AuraEnabled public String status;
        @AuraEnabled public Datetime sentAt;
        @AuraEnabled public String subject;
        @AuraEnabled public String toAddr;
    }

    public class SendRequest {
        @AuraEnabled public Id recordId;
        @AuraEnabled public Id contactId;
        @AuraEnabled public String toAddress;
        @AuraEnabled public String subject;
        @AuraEnabled public String bodyText;
    }

    @AuraEnabled(cacheable=true)
    public static DefaultsDTO getDefaults(Id recordId) {
        DefaultsDTO dto = new DefaultsDTO();

        if (recordId == null) return dto;

        Schema.SObjectType t = recordId.getSObjectType();

        if (t == Contact.SObjectType) {
            Contact c = [SELECT Id, Email FROM Contact WHERE Id = :recordId LIMIT 1];
            dto.contactId = c.Id;
            dto.toEmail = c.Email;
            return dto;
        }

        if (t == Case.SObjectType) {
            Case cs = [SELECT Id, ContactId, Contact.Email FROM Case WHERE Id = :recordId LIMIT 1];
            dto.contactId = cs.ContactId;
            dto.toEmail = (cs.Contact != null) ? cs.Contact.Email : null;
            return dto;
        }

        // Unknown record type: return empty defaults
        return dto;
    }

    @AuraEnabled(cacheable=true)
    public static List<MessageDTO> listMessages(Id recordId) {
        List<MessageDTO> out = new List<MessageDTO>();
        if (recordId == null) return out;

        // MVP supports Case + Contact as anchors
        Schema.SObjectType t = recordId.getSObjectType();

        List<Comms_Message__c> msgs;
        if (t == Contact.SObjectType) {
            msgs = [
                SELECT Id, Direction__c, Channel__c, Status__c, Sent_At__c, Subject__c, To__c
                FROM Comms_Message__c
                WHERE Contact__c = :recordId
                ORDER BY CreatedDate DESC
                LIMIT 25
            ];
        } else if (t == Case.SObjectType) {
            msgs = [
                SELECT Id, Direction__c, Channel__c, Status__c, Sent_At__c, Subject__c, To__c
                FROM Comms_Message__c
                WHERE Case__c = :recordId
                ORDER BY CreatedDate DESC
                LIMIT 25
            ];
        } else {
            return out;
        }

        for (Comms_Message__c m : msgs) {
            MessageDTO dto = new MessageDTO();
            dto.id = m.Id;
            dto.direction = m.Direction__c;
            dto.channel = m.Channel__c;
            dto.status = m.Status__c;
            dto.sentAt = m.Sent_At__c;
            dto.subject = m.Subject__c;
            dto.toAddr = m.To__c;
            out.add(dto);
        }
        return out;
    }

    @AuraEnabled
    public static Id sendEmail(SendRequest req) {
        if (req == null) throw new AuraHandledException('Missing request.');
        if (String.isBlank(req.toAddress)) throw new AuraHandledException('To address is required.');
        if (String.isBlank(req.subject)) req.subject = '(no subject)';
        if (req.bodyText == null) req.bodyText = '';

        // Consent gate (best-effort; if no preference record exists, allow)
        if (req.contactId != null) {
            try {
                enforceConsent(req.contactId, 'Email');
            } catch (ConsentException e) {
                throw new AuraHandledException(e.getMessage());
            }
        }

        // Create log record as Queued
        Comms_Message__c msg = new Comms_Message__c();
        msg.Direction__c = 'Outbound';
        msg.Channel__c = 'Email';
        msg.Status__c = 'Queued';
        msg.To__c = req.toAddress;
        msg.Subject__c = req.subject;
        msg.Body_Text__c = req.bodyText;
        msg.Contact__c = req.contactId;

        if (req.recordId != null) {
            Schema.SObjectType t = req.recordId.getSObjectType();
            if (t == Case.SObjectType) msg.Case__c = req.recordId;
            if (t == Contact.SObjectType) msg.Contact__c = req.recordId;
        }

        insert msg;

        System.enqueueJob(new CommsSendQueueable(msg.Id));
        return msg.Id;
    }

    public static void enforceConsent(Id contactId, String channel) {
        ConsentCheck check = checkConsent(contactId, channel);
        if (!check.allowed) throw new ConsentException(check.reason);
    }

    public static ConsentCheck checkConsent(Id contactId, String channel) {
        ConsentCheck check = new ConsentCheck();
        check.allowed = true;
        check.reason = null;

        if (contactId == null) return check;

        // If no pref exists, we allow (MVP). If Do Not Contact, we block.
        List<Comms_Preference__c> prefs = [
            SELECT Id, Do_Not_Contact__c, Email_Allowed__c, SMS_Allowed__c, Phone_Allowed__c
            FROM Comms_Preference__c
            WHERE Contact__c = :contactId
            ORDER BY CreatedDate DESC
            LIMIT 1
        ];

        if (prefs.isEmpty()) return check;

        Comms_Preference__c p = prefs[0];
        if (p.Do_Not_Contact__c) {
            check.allowed = false;
            check.reason = 'This contact is marked Do Not Contact.';
            return check;
        }
        if (channel == 'Email' && p.Email_Allowed__c == false) {
            check.allowed = false;
            check.reason = 'Email is not allowed for this contact.';
            return check;
        }
        if (channel == 'SMS' && p.SMS_Allowed__c == false) {
            check.allowed = false;
            check.reason = 'SMS is not allowed for this contact.';
            return check;
        }
        if (channel == 'Phone' && p.Phone_Allowed__c == false) {
            check.allowed = false;
            check.reason = 'Phone is not allowed for this contact.';
            return check;
        }

        return check;
    }
}
