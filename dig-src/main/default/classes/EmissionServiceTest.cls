@IsTest
public class EmissionServiceTest {
    
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
    
    @IsTest
    static void testAppend() {
        // Create a test stream
        Emission_Stream__c stream = createTestStream('test');
        
        // Test basic append
        String payload = '{"test": "value"}';
        Emission__c emission = EmissionService.append(
            'test',
            'test.type',
            payload,
            null,
            null,
            null,
            null
        );
        
        // Verify emission was created
        System.assertNotEquals(null, emission.Id);
        System.assertEquals('test', emission.Stream__c);
        System.assertEquals(1, emission.Sequence__c);
        System.assertEquals('test.type', emission.Type__c);
        System.assertEquals('GENESIS', emission.PrevHash__c);
        System.assertEquals(payload, emission.Payload__c);
        
        // Verify stream allocator was updated
        Emission_Stream__c updatedStream = [
            SELECT Id, Next_Sequence__c, Last_Hash__c 
            FROM Emission_Stream__c 
            WHERE Id = :stream.Id
        ];
        System.assertEquals(2, updatedStream.Next_Sequence__c);
        System.assertNotEquals('GENESIS', updatedStream.Last_Hash__c);
        System.assertEquals(64, updatedStream.Last_Hash__c.length());
    }
    
    @IsTest
    static void testAppendOnce() {
        // Create a test stream
        Emission_Stream__c stream = createTestStream('test2');
        
        // Test appendOnce with idempotency key
        String payload = '{"test": "value2"}';
        String idempotencyKey = 'test-key-123';
        
        Emission__c emission1 = EmissionService.appendOnce(
            'test2',
            idempotencyKey,
            'test.type2',
            payload,
            null,
            null,
            null,
            null
        );
        
        // Verify emission was created
        System.assertNotEquals(null, emission1.Id);
        System.assertEquals('test2', emission1.Stream__c);
        System.assertEquals(1, emission1.Sequence__c);
        System.assertEquals('test.type2', emission1.Type__c);
        System.assertEquals('GENESIS', emission1.PrevHash__c);
        System.assertEquals(payload, emission1.Payload__c);
        System.assertEquals(idempotencyKey, emission1.Idempotency_Key__c);
        System.assertEquals('test2:test-key-123', emission1.Stream_Idem__c);
        
        // Try to append again with same key - should return same emission
        Emission__c emission2 = EmissionService.appendOnce(
            'test2',
            idempotencyKey,
            'test.type2',
            payload,
            null,
            null,
            null,
            null
        );
        
        System.assertEquals(emission1.Id, emission2.Id, 'Should return same emission for same idempotency key');
        
        // Verify stream allocator was updated only once
        Emission_Stream__c updatedStream = [
            SELECT Id, Next_Sequence__c, Last_Hash__c 
            FROM Emission_Stream__c 
            WHERE Id = :stream.Id
        ];
        System.assertEquals(2, updatedStream.Next_Sequence__c);
    }
    
    @IsTest
    static void testChain() {
        // Create a test stream
        Emission_Stream__c stream = createTestStream('chain-test');
        
        // Append first emission
        String payload1 = '{"message": "first"}';
        Emission__c emission1 = EmissionService.append(
            'chain-test',
            'chain.first',
            payload1,
            null,
            null,
            null,
            null
        );
        
        // Append second emission
        String payload2 = '{"message": "second"}';
        Emission__c emission2 = EmissionService.append(
            'chain-test',
            'chain.second',
            payload2,
            null,
            null,
            null,
            null
        );
        
        // Verify sequence numbers
        System.assertEquals(1, emission1.Sequence__c);
        System.assertEquals(2, emission2.Sequence__c);
        
        // Verify hash chaining
        System.assertEquals('GENESIS', emission1.PrevHash__c);
        System.assertEquals(emission1.Hash__c, emission2.PrevHash__c);
        
        // Verify hash lengths
        System.assertEquals(64, emission1.Hash__c.length());
        System.assertEquals(64, emission2.Hash__c.length());
    }
    
    @IsTest
    static void testNumericSequenceAndLookups() {
        // Create a test stream
        Emission_Stream__c stream = new Emission_Stream__c(
            Name = 'sequence-test',
            Next_Sequence__c = 1,
            Last_Hash__c = 'GENESIS'
        );
        insert stream;
        
        // Create test records for lookups
        Contact testContact = new Contact(
            FirstName = 'Test',
            LastName = 'Contact',
            Email = 'test@example.com'
        );
        insert testContact;
        
        Membership_Term__c testTerm = new Membership_Term__c(
            Contact__c = testContact.Id,
            Term_Start__c = Date.today(),
            Term_End__c = Date.today().addYears(1),
            Status__c = 'Active'
        );
        insert testTerm;
        
        Receipt__c testReceipt = new Receipt__c(
            External_Id__c = 'receipt-123',
            Type__c = 'test',
            Payload__c = 'test payload'
        );
        insert testReceipt;
        
        // Test append with lookup values
        String payload = '{"test": "value"}';
        Emission__c emission = EmissionService.append(
            'sequence-test',
            'test.type',
            payload,
            null,
            testContact.Id,
            testTerm.Id,
            testReceipt.Id
        );
        
        // Verify emission was created with new fields populated
        System.assertNotEquals(null, emission.Id);
        System.assertEquals('sequence-test', emission.Stream__c);
        System.assertEquals(1, Integer.valueOf(emission.Sequence__c)); // Legacy field
        System.assertEquals(1, emission.Sequence_Num__c); // New numeric field
        System.assertEquals('test.type', emission.Type__c);
        System.assertEquals('GENESIS', emission.PrevHash__c);
        System.assertEquals(payload, emission.Payload__c);
        System.assertEquals(testTerm.Id, emission.MembershipTerm__c); // New lookup
        System.assertEquals(testReceipt.Id, emission.ReceiptRef__c); // New lookup
        System.assertEquals(String.valueOf(testTerm.Id), emission.Membership_Term__c); // Legacy field
        System.assertEquals(String.valueOf(testReceipt.Id), emission.Receipt__c); // Legacy field
        System.assertEquals('sequence-test:1', emission.Stream_Seq__c); // New field
        
        // Verify stream allocator was updated
        Emission_Stream__c updatedStream = [
            SELECT Id, Next_Sequence__c, Last_Hash__c 
            FROM Emission_Stream__c 
            WHERE Id = :stream.Id
        ];
        System.assertEquals(2, updatedStream.Next_Sequence__c);
        System.assertNotEquals('GENESIS', updatedStream.Last_Hash__c);
        System.assertEquals(64, updatedStream.Last_Hash__c.length());
    }
    
    @IsTest
    static void testSequenceChainWithNumbers() {
        // Create a test stream
        Emission_Stream__c stream = createTestStream('numeric-chain-test');
        
        // Append first emission
        String payload1 = '{"message": "first"}';
        Emission__c emission1 = EmissionService.append(
            'numeric-chain-test',
            'chain.first',
            payload1,
            null,
            null,
            null,
            null
        );
        
        // Append second emission
        String payload2 = '{"message": "second"}';
        Emission__c emission2 = EmissionService.append(
            'numeric-chain-test',
            'chain.second',
            payload2,
            null,
            null,
            null,
            null
        );
        
        // Verify sequence numbers (both numeric and text)
        System.assertEquals(1, emission1.Sequence__c);
        System.assertEquals(1, emission1.Sequence_Num__c);
        System.assertEquals(2, emission2.Sequence__c);
        System.assertEquals(2, emission2.Sequence_Num__c);
        
        // Verify hash chaining
        System.assertEquals('GENESIS', emission1.PrevHash__c);
        System.assertEquals(emission1.Hash__c, emission2.PrevHash__c);
        
        // Verify hash lengths
        System.assertEquals(64, emission1.Hash__c.length());
        System.assertEquals(64, emission2.Hash__c.length());
    }
}
