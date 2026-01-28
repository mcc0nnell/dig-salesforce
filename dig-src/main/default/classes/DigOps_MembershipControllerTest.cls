@IsTest
public class DigOps_MembershipControllerTest {
    @IsTest
    static void testSearchContacts() {
        String token = 'ZzSoslToken_' + String.valueOf(Math.abs(Crypto.getRandomInteger()));

        Contact contact = new Contact(
            LastName = token,
            Email = token.toLowerCase() + '@example.org',
            Membership_Status_Summary__c = 'Active',
            Membership_End_Date__c = Date.today().addMonths(1)
        );
        insert contact;

        List<DigOps_MembershipController.ContactPick> results =
            DigOps_MembershipController.searchContacts(token, 10);

        System.assertEquals(1, results.size(), 'Expected exactly one search result');
        System.assertEquals(contact.Id, results[0].id, 'Expected the inserted contact');
    }

    @IsTest
    static void testSearchContactsShortQueryReturnsEmpty() {
        System.assertEquals(0, DigOps_MembershipController.searchContacts('A', 10).size());
        System.assertEquals(0, DigOps_MembershipController.searchContacts(' ', 10).size());
        System.assertEquals(0, DigOps_MembershipController.searchContacts(null, 10).size());
    }

    @IsTest
    static void testLoadPanelAndCreateRenewal() {
        Contact contact = DigOps_MembershipTestFactory.createContact('Panel');
        Membership__c term = DigOps_MembershipTestFactory.createMembership(
            contact.Id,
            Date.today().addMonths(-1),
            Date.today().addMonths(1),
            'INDIVIDUAL',
            Date.today().addMonths(-1),
            null,
            null
        );
        DigOps_MembershipService.recompute(new Set<Id>{contact.Id});

        DigOps_MembershipController.MembershipPanelData data =
            DigOps_MembershipController.loadPanel(contact.Id);
        System.assertEquals(contact.Id, data.contact.id, 'Contact summary loaded');
        System.assertEquals(1, data.terms.size(), 'Expected one membership term');
        System.assertEquals(term.Id, data.terms[0].id, 'Expected term id in panel');

        DigOps_MembershipController.CreateRenewalRequest req =
            new DigOps_MembershipController.CreateRenewalRequest();
        req.contactId = contact.Id;
        req.level = 'INDIVIDUAL';
        req.startDate = Date.today();
        req.endDate = Date.today().addMonths(12);
        req.source = 'Manual';
        req.paidDate = Date.today();
        req.paymentRef = 'TEST-REF';
        req.notes = 'Test notes';

        Id createdId = DigOps_MembershipController.createRenewal(req);
        System.assertNotEquals(null, createdId, 'Expected new membership id');
    }

    @IsTest
    static void testLoadPanelRequiresContactId() {
        try {
            DigOps_MembershipController.loadPanel(null);
            System.assert(false, 'Expected exception for null contactId');
        } catch (AuraHandledException ex) {
            System.assertNotEquals(null, ex, 'Expected AuraHandledException');
        }
    }

    @IsTest
    static void testRecomputeRequiresContactId() {
        try {
            DigOps_MembershipController.recompute(null);
            System.assert(false, 'Expected exception for null contactId');
        } catch (AuraHandledException ex) {
            System.assertNotEquals(null, ex, 'Expected AuraHandledException');
        }
    }

    @IsTest
    static void testCreateRenewalDefaultsAndValidation() {
        Contact contact = DigOps_MembershipTestFactory.createContact('Defaults');

        DigOps_MembershipController.CreateRenewalRequest req =
            new DigOps_MembershipController.CreateRenewalRequest();
        req.contactId = contact.Id;
        req.level = 'INDIVIDUAL';

        Id createdId = DigOps_MembershipController.createRenewal(req);
        System.assertNotEquals(null, createdId, 'Expected new membership id');

        Membership__c created = [
            SELECT StartDate__c, EndDate__c, Level__c, Source__c
            FROM Membership__c
            WHERE Id = :createdId
        ];
        if (Schema.SObjectType.Membership__c.fields.getMap().get('Level__c').getDescribe().isAccessible()) {
            System.assertEquals('INDIVIDUAL', created.Level__c, 'Expected level set');
        }
        System.assertEquals('Manual', created.Source__c, 'Expected default source');
        System.assertNotEquals(null, created.EndDate__c, 'Expected default end date');

        DigOps_MembershipController.CreateRenewalRequest badReq =
            new DigOps_MembershipController.CreateRenewalRequest();
        badReq.contactId = contact.Id;
        badReq.level = 'INDIVIDUAL';
        badReq.startDate = Date.today();
        badReq.endDate = Date.today().addDays(-1);

        try {
            DigOps_MembershipController.createRenewal(badReq);
            System.assert(false, 'Expected end date validation error');
        } catch (AuraHandledException ex) {
            System.assertNotEquals(null, ex, 'Expected AuraHandledException');
        }
    }
}
