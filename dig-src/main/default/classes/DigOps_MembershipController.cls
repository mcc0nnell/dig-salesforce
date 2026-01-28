public with sharing class DigOps_MembershipController {
    public class ContactPick {
        @AuraEnabled public Id id;
        @AuraEnabled public String name;
        @AuraEnabled public String email;
        @AuraEnabled public String membershipStatus;
        @AuraEnabled public Date membershipEndDate;
    }

    public class ContactSummaryDTO {
        @AuraEnabled public Id id;
        @AuraEnabled public String name;
        @AuraEnabled public Boolean isCurrentMember;
        @AuraEnabled public String membershipStatus;
        @AuraEnabled public Date membershipEndDate;
        @AuraEnabled public String currentLevel;
        @AuraEnabled public Date memberSince;
        @AuraEnabled public Date lastPaidDate;
    }

    public class MembershipTermDTO {
        @AuraEnabled public Id id;
        @AuraEnabled public Date startDate;
        @AuraEnabled public Date endDate;
        @AuraEnabled public String status;
        @AuraEnabled public String level;
        @AuraEnabled public Date paidDate;
        @AuraEnabled public String paymentRef;
        @AuraEnabled public String source;
        @AuraEnabled public String notes;
        @AuraEnabled public Decimal amount;
    }

    public class MembershipPanelData {
        @AuraEnabled public ContactSummaryDTO contact;
        @AuraEnabled public List<MembershipTermDTO> terms;
    }

    public class CreateRenewalRequest {
        @AuraEnabled public Id contactId;
        @AuraEnabled public String level;
        @AuraEnabled public Date startDate;
        @AuraEnabled public Date endDate;
        @AuraEnabled public String source;
        @AuraEnabled public Date paidDate;
        @AuraEnabled public String paymentRef;
        @AuraEnabled public String notes;
        @AuraEnabled public Decimal amount;
    }

    @AuraEnabled(cacheable=true)
    public static List<ContactPick> searchContacts(String q, Integer limitSize) {
        String query = q == null ? '' : q.trim();
        if (query.length() < 2) {
            return new List<ContactPick>();
        }

        Integer limitVal = (limitSize == null ? 10 : limitSize);
        if (limitVal > 25) limitVal = 25;
        if (limitVal < 1) limitVal = 10;

        List<Contact> contacts = new List<Contact>();

        // Try SOSL first (fast / flexible in real org usage)
        try {
            String soslTerm = String.escapeSingleQuotes(query);
            List<List<SObject>> results = Search.query(
                'FIND {' + soslTerm + '*} IN NAME FIELDS RETURNING Contact(' +
                'Id, Name, Email, Membership_Status_Summary__c, Membership_End_Date__c ' +
                'LIMIT ' + limitVal + ')'
            );
            if (!results.isEmpty() && !results[0].isEmpty()) {
                for (SObject record : results[0]) {
                    contacts.add((Contact)record);
                }
            }
        } catch (Exception ex) {
            // Ignore and fall back to SOQL below.
        }

        // Fallback to SOQL if SOSL returned nothing OR threw
        if (contacts.isEmpty()) {
            String likeQuery = '%' + query + '%';
            contacts = [
                SELECT Id, Name, Email, Membership_Status_Summary__c, Membership_End_Date__c
                FROM Contact
                WHERE Name LIKE :likeQuery
                   OR Email LIKE :likeQuery
                ORDER BY LastName, FirstName, Id
                LIMIT :limitVal
            ];
        }

        contacts = (List<Contact>) Security.stripInaccessible(
            AccessType.READABLE,
            contacts
        ).getRecords();

        Map<String, Schema.SObjectField> contactFields = Schema.SObjectType.Contact.fields.getMap();
        Boolean canReadEmail = contactFields.get('Email').getDescribe().isAccessible();
        Boolean canReadStatus = contactFields.get('Membership_Status_Summary__c').getDescribe().isAccessible();
        Boolean canReadEndDate = contactFields.get('Membership_End_Date__c').getDescribe().isAccessible();

        List<ContactPick> picks = new List<ContactPick>();
        for (Contact contact : contacts) {
            ContactPick pick = new ContactPick();
            pick.id = contact.Id;
            pick.name = contact.Name;
            pick.email = canReadEmail ? contact.Email : null;
            pick.membershipStatus = canReadStatus ? contact.Membership_Status_Summary__c : null;
            pick.membershipEndDate = canReadEndDate ? contact.Membership_End_Date__c : null;
            picks.add(pick);
        }
        return picks;
    }

    @AuraEnabled(cacheable=true)
    public static MembershipPanelData loadPanel(Id contactId) {
        if (contactId == null) {
            throw new AuraHandledException('ContactId required');
        }
        List<Contact> contactList = [
            SELECT Id, Name, Is_Current_Member__c, Membership_Status_Summary__c,
                Membership_End_Date__c, Current_Membership_Level__c, Member_Since__c,
                Membership_Last_Paid_Date__c
            FROM Contact
            WHERE Id = :contactId
            LIMIT 1
        ];
        if (contactList.isEmpty()) {
            throw new AuraHandledException('Contact not found');
        }
        contactList = (List<Contact>)Security.stripInaccessible(
            AccessType.READABLE,
            contactList
        ).getRecords();
        Contact contact = contactList[0];

        Boolean hasAmount = Schema.SObjectType.Membership__c.fields.getMap().containsKey('Amount__c');
        String soql = 'SELECT Id, StartDate__c, EndDate__c, Status__c, Level__c, PaidDate__c,' +
            ' PaymentRef__c, Source__c, Notes__c';
        if (hasAmount) {
            soql += ', Amount__c';
        }
        soql += ' FROM Membership__c WHERE Contact__c = :contactId ' +
            'ORDER BY EndDate__c DESC NULLS LAST, CreatedDate DESC LIMIT 5';

        List<Membership__c> terms = Database.query(soql);
        terms = (List<Membership__c>)Security.stripInaccessible(
            AccessType.READABLE,
            terms
        ).getRecords();

        MembershipPanelData data = new MembershipPanelData();
        Map<String, Schema.SObjectField> contactFieldsForSummary = Schema.SObjectType.Contact.fields.getMap();
        Boolean canReadIsCurrent = contactFieldsForSummary.get('Is_Current_Member__c').getDescribe().isAccessible();
        Boolean canReadSummaryStatus = contactFieldsForSummary.get('Membership_Status_Summary__c').getDescribe().isAccessible();
        Boolean canReadSummaryEnd = contactFieldsForSummary.get('Membership_End_Date__c').getDescribe().isAccessible();
        Boolean canReadLevel = contactFieldsForSummary.get('Current_Membership_Level__c').getDescribe().isAccessible();
        Boolean canReadMemberSince = contactFieldsForSummary.get('Member_Since__c').getDescribe().isAccessible();
        Boolean canReadLastPaid = contactFieldsForSummary.get('Membership_Last_Paid_Date__c').getDescribe().isAccessible();

        ContactSummaryDTO summary = new ContactSummaryDTO();
        summary.id = contact.Id;
        summary.name = contact.Name;
        summary.isCurrentMember = canReadIsCurrent ? contact.Is_Current_Member__c : null;
        summary.membershipStatus = canReadSummaryStatus ? contact.Membership_Status_Summary__c : null;
        summary.membershipEndDate = canReadSummaryEnd ? contact.Membership_End_Date__c : null;
        summary.currentLevel = canReadLevel ? contact.Current_Membership_Level__c : null;
        summary.memberSince = canReadMemberSince ? contact.Member_Since__c : null;
        summary.lastPaidDate = canReadLastPaid ? contact.Membership_Last_Paid_Date__c : null;
        data.contact = summary;

        List<MembershipTermDTO> termDtos = new List<MembershipTermDTO>();
        for (Membership__c term : terms) {
            MembershipTermDTO dto = new MembershipTermDTO();
            dto.id = term.Id;
            dto.startDate = safeDate(term, 'StartDate__c');
            dto.endDate = safeDate(term, 'EndDate__c');
            dto.status = safeString(term, 'Status__c');
            dto.level = safeString(term, 'Level__c');
            dto.paidDate = safeDate(term, 'PaidDate__c');
            dto.paymentRef = safeString(term, 'PaymentRef__c');
            dto.source = safeString(term, 'Source__c');
            dto.notes = safeString(term, 'Notes__c');
            if (hasAmount) {
                dto.amount = safeDecimal(term, 'Amount__c');
            }
            termDtos.add(dto);
        }
        data.terms = termDtos;
        return data;
    }

    @AuraEnabled
    public static Id createRenewal(CreateRenewalRequest req) {
        if (req == null || req.contactId == null) {
            throw new AuraHandledException('ContactId required');
        }
        String levelKey = req.level == null ? '' : req.level.trim();
        if (levelKey == '') {
            throw new AuraHandledException('Level is required');
        }

        List<Contact> contacts = [SELECT Id FROM Contact WHERE Id = :req.contactId LIMIT 1];
        if (contacts.isEmpty()) {
            throw new AuraHandledException('Contact not found');
        }

        Date startDate = req.startDate != null ? req.startDate : Date.today();
        Date endDate = req.endDate;
        if (endDate == null) {
            DigOps_MembershipRules.LevelConfig config = DigOps_MembershipRules.getLevelConfig(levelKey);
            Integer durationMonths = config != null ? config.durationMonths : 12;
            endDate = startDate.addMonths(durationMonths != null ? durationMonths : 12);
        }
        if (endDate < startDate) {
            throw new AuraHandledException('End date must be on or after start date');
        }

        String source = String.isBlank(req.source) ? 'Manual' : req.source;
        Boolean hasAmount = Schema.SObjectType.Membership__c.fields.getMap().containsKey('Amount__c');

        Membership__c membership = new Membership__c(
            Contact__c = req.contactId,
            StartDate__c = startDate,
            EndDate__c = endDate,
            Level__c = levelKey,
            Source__c = source,
            PaidDate__c = req.paidDate,
            PaymentRef__c = req.paymentRef,
            Notes__c = req.notes
        );
        if (hasAmount && req.amount != null) {
            membership.put('Amount__c', req.amount);
        }

        List<SObject> insertable = Security.stripInaccessible(
            AccessType.CREATABLE,
            new List<SObject>{membership}
        ).getRecords();
        insert insertable;
        Id membershipId = ((Membership__c)insertable[0]).Id;

        DigOps_MembershipService.recompute(new Set<Id>{req.contactId});
        return membershipId;
    }

    @AuraEnabled
    public static void recompute(Id contactId) {
        if (contactId == null) {
            throw new AuraHandledException('ContactId required');
        }
        DigOps_MembershipService.recompute(new Set<Id>{contactId});
    }

    private static String safeString(SObject record, String fieldName) {
        try {
            return (String)record.get(fieldName);
        } catch (Exception ex) {
            return null;
        }
    }

    private static Date safeDate(SObject record, String fieldName) {
        try {
            return (Date)record.get(fieldName);
        } catch (Exception ex) {
            return null;
        }
    }

    private static Decimal safeDecimal(SObject record, String fieldName) {
        try {
            return (Decimal)record.get(fieldName);
        } catch (Exception ex) {
            return null;
        }
    }
}
