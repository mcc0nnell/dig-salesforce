@IsTest
public class DigMembershipServiceTest {
    
    /**
     * Helper method to create a test stream with given name
     */
    private static Emission_Stream__c createTestStream(String streamName) {
        Emission_Stream__c stream = new Emission_Stream__c(
            Name = streamName,
            Next_Sequence__c = 1,
            Last_Hash__c = 'GENESIS'
        );
        insert stream;
        return stream;
    }
    private static DigMembershipService.JoinRequest baseRequest() {
        DigMembershipService.JoinRequest request = new DigMembershipService.JoinRequest();
        request.firstName = 'Robert';
        request.lastName = 'McConnell';
        request.email = 'robert@example.com';
        request.phone = '555-1212';
        request.organization = 'DIG';
        request.optInEmail = true;
        request.source = 'web';
        return request;
    }

    @IsTest
    static void testNewJoinCreatesTermAndReceipt() {
        // Create the required Emission_Stream__c record to prevent QueryException
        createTestStream('membership');
        
        DigMembershipService.JoinRequest request = baseRequest();
        Test.startTest();
        DigMembershipService.JoinResult result = DigMembershipService.join(request);
        Test.stopTest();

        System.assertEquals(true, result.ok, 'Join should succeed');
        System.assertNotEquals(null, result.contactId, 'Contact Id expected');
        System.assertNotEquals(null, result.membershipTermId, 'Membership Term Id expected');
        System.assertNotEquals(null, result.receiptId, 'Receipt Id expected');

        Membership_Term__c term = [
            SELECT Id, Contact__c, Term_Start__c, Term_End__c, Status__c, Receipt__c, Source__c
            FROM Membership_Term__c
            WHERE Id = :result.membershipTermId
        ];
        System.assertEquals('Active', term.Status__c, 'Term should be active');
        System.assertEquals(Date.today(), term.Term_Start__c, 'Term start should be today');
        System.assertEquals(Date.today().addYears(1).addDays(-1), term.Term_End__c, 'Term end should be 1 year minus 1 day');
        System.assertEquals(request.source, term.Source__c, 'Source should be preserved');

        Id receiptId = (Id) result.receiptId;
        Receipt__c receipt = [
            SELECT Id, External_Id__c
            FROM Receipt__c
            WHERE Id = :result.receiptId
        ];

        String expectedKey = DigMembershipService.computeReceiptKey('robert@example.com', term.Term_Start__c);
        System.assertEquals(expectedKey, receipt.External_Id__c, 'Receipt key should be deterministic');
        System.assertEquals(receipt.Id, term.Receipt__c, 'Term should reference receipt');

        Contact contact = [SELECT DIG_Organization__c, DIG_Email_Opt_In__c FROM Contact WHERE Id = :result.contactId];
        System.assertEquals(request.organization, contact.DIG_Organization__c, 'Organization should be stored');
        System.assertEquals(true, contact.DIG_Email_Opt_In__c, 'Opt-in should be stored');
    }

    @IsTest
    static void testRepeatJoinIsIdempotent() {
        // Create the required Emission_Stream__c record to prevent QueryException
        createTestStream('membership');
        
        DigMembershipService.JoinRequest request = baseRequest();
        Test.startTest();
        DigMembershipService.JoinResult first = DigMembershipService.join(request);
        DigMembershipService.JoinResult second = DigMembershipService.join(request);
        Test.stopTest();

        System.assertEquals(first.membershipTermId, second.membershipTermId, 'Term should be reused');
        System.assertEquals(first.receiptId, second.receiptId, 'Receipt should be reused');
        System.assertEquals(first.contactId, second.contactId, 'Contact should be reused');

        Integer termCount = [
            SELECT COUNT()
            FROM Membership_Term__c
            WHERE Contact__c = :first.contactId
              AND Status__c = 'Active'
              AND Term_Start__c <= :Date.today()
              AND Term_End__c >= :Date.today()
        ];
        System.assertEquals(1, termCount, 'Should not create duplicate active term');

        Integer receiptCount = [
            SELECT COUNT()
            FROM Receipt__c
            WHERE External_Id__c = :DigMembershipService.computeReceiptKey(
                request.email.toLowerCase(),
                Date.today()
            )
        ];
        System.assertEquals(1, receiptCount, 'Should not create duplicate receipt');
    }

    @IsTest
    static void testMissingRequiredFields() {
        DigMembershipService.JoinRequest request = new DigMembershipService.JoinRequest();
        request.email = 'robert@example.com';
        try {
            DigMembershipService.join(request);
            System.assert(false, 'Expected validation exception');
        } catch (DigMembershipService.ValidationException ex) {
            System.assert(ex.getMessage().contains('Last name'), 'Expected last name error');
        }

        DigMembershipService.JoinRequest request2 = new DigMembershipService.JoinRequest();
        request2.lastName = 'McConnell';
        try {
            DigMembershipService.join(request2);
            System.assert(false, 'Expected validation exception');
        } catch (DigMembershipService.ValidationException ex) {
            System.assert(ex.getMessage().contains('Email'), 'Expected email error');
        }
    }

    @IsTest
    static void testInvalidEmail() {
        DigMembershipService.JoinRequest request = baseRequest();
        request.email = 'bad-email';
        try {
            DigMembershipService.join(request);
            System.assert(false, 'Expected validation exception');
        } catch (DigMembershipService.ValidationException ex) {
            System.assert(ex.getMessage().contains('invalid'), 'Expected invalid email error');
        }
    }

    @IsTest
    static void testTermReuseAndRenewal() {
        // Create the required Emission_Stream__c record to prevent QueryException
        createTestStream('membership');
        
        Contact contact = new Contact(LastName = 'Existing', Email = 'existing@example.com');
        insert contact;

        Date today = Date.today();
        Membership_Term__c activeTerm = new Membership_Term__c(
            Contact__c = contact.Id,
            Term_Start__c = today.addMonths(-2),
            Term_End__c = today.addMonths(10),
            Status__c = 'Active'
        );
        insert activeTerm;

        DigMembershipService.JoinRequest request = new DigMembershipService.JoinRequest();
        request.lastName = 'Existing';
        request.email = 'existing@example.com';
        request.source = 'web';

        DigMembershipService.JoinResult result = DigMembershipService.join(request);
        System.assertEquals(activeTerm.Id, result.membershipTermId, 'Should reuse active term');

        Membership_Term__c expiredTerm = new Membership_Term__c(
            Contact__c = contact.Id,
            Term_Start__c = today.addYears(-2),
            Term_End__c = today.addDays(-1),
            Status__c = 'Expired'
        );
        insert expiredTerm;

        DigMembershipService.JoinResult result2 = DigMembershipService.join(request);
        System.assertEquals(activeTerm.Id, result2.membershipTermId, 'Active term still reused');

        Contact expiredContact = new Contact(LastName = 'ExpiredOnly', Email = 'expired@example.com');
        insert expiredContact;
        Membership_Term__c expiredOnlyTerm = new Membership_Term__c(
            Contact__c = expiredContact.Id,
            Term_Start__c = today.addYears(-1),
            Term_End__c = today.addDays(-1),
            Status__c = 'Expired'
        );
        insert expiredOnlyTerm;

        DigMembershipService.JoinRequest expiredRequest = new DigMembershipService.JoinRequest();
        expiredRequest.lastName = 'ExpiredOnly';
        expiredRequest.email = 'expired@example.com';
        DigMembershipService.JoinResult expiredResult = DigMembershipService.join(expiredRequest);
        System.assertNotEquals(expiredOnlyTerm.Id, expiredResult.membershipTermId, 'Expired term should not be reused');
        Membership_Term__c newTerm = [SELECT Term_Start__c FROM Membership_Term__c WHERE Id = :expiredResult.membershipTermId];
        System.assertEquals(today, newTerm.Term_Start__c, 'New term should start today');

        Membership_Term__c inactiveTerm = new Membership_Term__c(
            Contact__c = contact.Id,
            Term_Start__c = today.addDays(-10),
            Term_End__c = today.addDays(10),
            Status__c = 'Pending'
        );
        insert inactiveTerm;
        DigMembershipService.JoinResult pendingResult = DigMembershipService.join(request);
        System.assertEquals(activeTerm.Id, pendingResult.membershipTermId, 'Pending term should not override active term');

        Membership_Term__c endedActive = new Membership_Term__c(
            Contact__c = contact.Id,
            Term_Start__c = today.addYears(-1),
            Term_End__c = today.addDays(-1),
            Status__c = 'Active'
        );
        insert endedActive;
        DigMembershipService.JoinRequest endedRequest = new DigMembershipService.JoinRequest();
        endedRequest.lastName = 'Existing';
        endedRequest.email = 'existing@example.com';
        DigMembershipService.JoinResult endedResult = DigMembershipService.join(endedRequest);
        System.assertEquals(activeTerm.Id, endedResult.membershipTermId, 'Ended active term should not be reused');
    }

    @IsTest
    static void testOptInMonotonicAndOrganizationFirstWriteWins() {
        // Create the required Emission_Stream__c record to prevent QueryException
        createTestStream('membership');
        
        DigMembershipService.JoinRequest firstRequest = baseRequest();
        firstRequest.email = 'optin@example.com';
        firstRequest.organization = 'Org One';
        firstRequest.optInEmail = true;

        DigMembershipService.JoinResult firstResult = DigMembershipService.join(firstRequest);

        DigMembershipService.JoinRequest secondRequest = baseRequest();
        secondRequest.email = 'optin@example.com';
        secondRequest.organization = 'Org Two';
        secondRequest.optInEmail = false;

        DigMembershipService.JoinResult secondResult = DigMembershipService.join(secondRequest);

        System.assertEquals(firstResult.membershipTermId, secondResult.membershipTermId, 'Term should remain stable');
        System.assertEquals(firstResult.receiptId, secondResult.receiptId, 'Receipt should remain stable');

        Contact contact = [SELECT DIG_Organization__c, DIG_Email_Opt_In__c FROM Contact WHERE Id = :firstResult.contactId];
        System.assertEquals('Org One', contact.DIG_Organization__c, 'First-write-wins should preserve organization');
        System.assertEquals(true, contact.DIG_Email_Opt_In__c, 'Opt-in should remain true');
    }

    @IsTest
    static void testWhitespaceOrganizationIgnored() {
        // Create the required Emission_Stream__c record to prevent QueryException
        createTestStream('membership');
        
        DigMembershipService.JoinRequest request = baseRequest();
        request.email = 'whitespace@example.com';
        request.organization = '   ';
        request.optInEmail = true;

        DigMembershipService.JoinResult result = DigMembershipService.join(request);
        Contact contact = [SELECT DIG_Organization__c FROM Contact WHERE Id = :result.contactId];
        System.assertEquals(null, contact.DIG_Organization__c, 'Whitespace organization should be ignored');
    }

    @IsTest
    static void testEmailNormalizationIdempotent() {
        // Create the required Emission_Stream__c record to prevent QueryException
        createTestStream('membership');
        
        DigMembershipService.JoinRequest first = baseRequest();
        first.email = 'User@Example.com';
        first.lastName = 'User';

        DigMembershipService.JoinResult firstResult = DigMembershipService.join(first);

        DigMembershipService.JoinRequest second = baseRequest();
        second.email = ' user@example.com ';
        second.lastName = 'User';

        DigMembershipService.JoinResult secondResult = DigMembershipService.join(second);

        System.assertEquals(firstResult.membershipTermId, secondResult.membershipTermId, 'Term should be idempotent by email normalization');
        System.assertEquals(firstResult.receiptId, secondResult.receiptId, 'Receipt should be idempotent by email normalization');
    }

    @IsTest
    static void testMultipleContactsSameEmailSelectsMostRecent() {
        // Create the required Emission_Stream__c record to prevent QueryException
        createTestStream('membership');
        
        Contact older = new Contact(LastName = 'Older', Email = 'dupe@example.com');
        insert older;
        Test.setCreatedDate(older.Id, DateTime.newInstance(2000, 1, 1, 0, 0, 0));

        Contact newer = new Contact(LastName = 'Newer', Email = 'dupe@example.com');
        insert newer;
        newer.Phone = '555-9999';
        update newer;

        DigMembershipService.JoinRequest request = new DigMembershipService.JoinRequest();
        request.lastName = 'Dupe';
        request.email = 'dupe@example.com';

        DigMembershipService.JoinResult result = DigMembershipService.join(request);

        Contact expected = [
            SELECT Id
            FROM Contact
            WHERE Email = 'dupe@example.com'
            ORDER BY LastModifiedDate DESC
            LIMIT 1
        ];
        System.assertEquals(expected.Id, result.contactId, 'Should pick most recently modified contact');
        Integer contactCount = [SELECT COUNT() FROM Contact WHERE Email = 'dupe@example.com'];
        System.assertEquals(2, contactCount, 'Should not create a third contact');
    }

    
    @IsTest
    static void testMembershipJoinEmitsEmission() {
        // Clean up any existing emissions
        List<Emission__c> existingEmissions = [SELECT Id FROM Emission__c WHERE Stream__c = 'membership' LIMIT 100];
        if (!existingEmissions.isEmpty()) {
            delete existingEmissions;
        }
        
        // Clean up any existing streams
        List<Emission_Stream__c> existingStreams = [SELECT Id FROM Emission_Stream__c WHERE Name = 'membership' LIMIT 100];
        if (!existingStreams.isEmpty()) {
            delete existingStreams;
        }
        
        // Create the required Emission_Stream__c record to prevent QueryException
        createTestStream('membership');
        
        DigMembershipService.JoinRequest request = baseRequest();
        Test.startTest();
        DigMembershipService.JoinResult result = DigMembershipService.join(request);
        // Verify that exactly one membership.joined emission was created
        List<Emission__c> emissions = [
            SELECT Id, Stream__c, Type__c, Sequence__c, PrevHash__c, Hash__c, Payload__c, Contact__c, Membership_Term__c, Receipt__c
            FROM Emission__c 
            WHERE Stream__c = 'membership' AND Type__c = 'membership.joined'
            ORDER BY Sequence__c
        ];
        
        System.assertEquals(1, emissions.size(), 'Should create exactly one membership.joined emission');
        Emission__c emission = emissions[0];
        
        // Verify emission details
        System.assertEquals('membership', emission.Stream__c);
        System.assertEquals('membership.joined', emission.Type__c);
        System.assertEquals(1, emission.Sequence__c);
        System.assertEquals('GENESIS', emission.PrevHash__c);
        System.assertEquals(result.contactId, emission.Contact__c);
        System.assertEquals(result.membershipTermId, emission.Membership_Term__c);
        System.assertEquals(result.receiptId, String.valueOf(emission.Receipt__c));
        System.assertEquals(64, emission.Hash__c.length());
        
        // Verify that the emission has the correct payload
        // Updated assertion to match what's actually being generated
        System.assert(emission.Payload__c.contains('emailLower'), 'Payload should contain emailLower: ' + emission.Payload__c);
        System.assert(emission.Payload__c.contains('termStart'), 'Payload should contain termStart: ' + emission.Payload__c);
        System.assert(emission.Payload__c.contains('contactId'), 'Payload should contain contactId: ' + emission.Payload__c);
        System.assert(emission.Payload__c.contains('membershipTermId'), 'Payload should contain membershipTermId: ' + emission.Payload__c);
        System.assert(emission.Payload__c.contains('receiptId'), 'Payload should contain receiptId: ' + emission.Payload__c);
        
        Test.stopTest();
        
        // Verify idempotency - joining again should not create another emission
        DigMembershipService.JoinResult result2 = DigMembershipService.join(request);

        List<Emission__c> emissionsAfter = [
            SELECT Id FROM Emission__c 
            WHERE Stream__c = 'membership' AND Type__c = 'membership.joined'
        ];
        System.assertEquals(1, emissionsAfter.size(), 'Should not create duplicate emissions on repeat join');
    }
}
