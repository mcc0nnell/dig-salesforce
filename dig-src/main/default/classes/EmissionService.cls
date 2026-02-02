public with sharing class EmissionService {
    
    /**
     * Appends a new emission to the specified stream
     * @param stream The stream name
     * @param type The emission type
     * @param payloadJsonCanonical The canonicalized payload
     * @param actorId The actor Id (optional)
     * @param contactId The contact Id (optional)
     * @param termId The membership term Id (optional)
     * @param receiptId The receipt Id (optional)
     * @return The created Emission__c record
     */
    public static Emission__c append(
        String stream,
        String type,
        String payloadJsonCanonical,
        Id actorId,
        Id contactId,
        Id termId,
        Id receiptId
    ) {
        return appendInternal(stream, null, type, payloadJsonCanonical, actorId, contactId, termId, receiptId);
    }
    
    /**
     * Appends a new emission to the specified stream, ensuring idempotency
     * @param stream The stream name
     * @param idempotencyKey The idempotency key
     * @param type The emission type
     * @param payloadJsonCanonical The canonicalized payload
     * @param actorId The actor Id (optional)
     * @param contactId The contact Id (optional)
     * @param termId The membership term Id (optional)
     * @param receiptId The receipt Id (optional)
     * @return The created Emission__c record
     */
    public static Emission__c appendOnce(
        String stream,
        String idempotencyKey,
        String type,
        String payloadJsonCanonical,
        Id actorId,
        Id contactId,
        Id termId,
        Id receiptId
    ) {
        // Check if emission already exists with this idempotency key
        if (idempotencyKey != null && idempotencyKey != '') {
            String streamIdem = stream + ':' + idempotencyKey;
            List<Emission__c> existing = [
                SELECT Id FROM Emission__c 
                WHERE Stream_Idem__c = :streamIdem 
                LIMIT 1
            ];
            if (!existing.isEmpty()) {
                return existing[0];
            }
        }
        
        return appendInternal(stream, idempotencyKey, type, payloadJsonCanonical, actorId, contactId, termId, receiptId);
    }
    
    /**
     * Wrapper method for invocable action compatibility
     * @param stream The stream name
     * @param type The emission type
     * @param payload The payload object
     * @param idempotencyKey The idempotency key
     * @param contactId The contact Id (optional)
     * @param termId The membership term Id (optional)
     * @param receiptId The receipt Id (optional)
     * @return The created Emission__c record
     */
    public static Emission__c appendOnce(
        String stream,
        String type,
        Object payload,
        String idempotencyKey,
        Id contactId,
        Id termId,
        Id receiptId
    ) {
        String payloadJson = (payload == null) ? null : JSON.serialize(payload);
        return appendOnce(stream, idempotencyKey, type, payloadJson, null, contactId, termId, receiptId);
    }
    
    /**
     * Internal method to append an emission
     * @param stream The stream name
     * @param idempotencyKey The idempotency key (optional)
     * @param type The emission type
     * @param payloadJsonCanonical The canonicalized payload
     * @param actorId The actor Id (optional)
     * @param contactId The contact Id (optional)
     * @param termId The membership term Id (optional)
     * @param receiptId The receipt Id (optional)
     * @return The created Emission__c record
     */
    private static Emission__c appendInternal(
        String stream,
        String idempotencyKey,
        String type,
        String payloadJsonCanonical,
        Id actorId,
        Id contactId,
        Id termId,
        Id receiptId
    ) {
        // Get or create the emission stream allocator
        List<Emission_Stream__c> streamRows = [
            SELECT Id, Next_Sequence__c, Last_Hash__c 
            FROM Emission_Stream__c 
            WHERE Name = :stream 
            LIMIT 1 
            FOR UPDATE
        ];

        Emission_Stream__c streamRow;
        if (!streamRows.isEmpty()) {
            streamRow = streamRows[0];
        }

        if (streamRow == null) {
            // Create new stream allocator
            streamRow = new Emission_Stream__c(
                Name = stream,
                Next_Sequence__c = Decimal.valueOf(1),
                Last_Hash__c = 'GENESIS'
            );
            insert streamRow;
        }

        // Allocate sequence number
        Decimal nextSeq = streamRow.Next_Sequence__c;
        if (nextSeq == null) {
            nextSeq = Decimal.valueOf(1);
        }
        Long seq = nextSeq.longValue();
        
        // Get previous hash
        String prevHash = streamRow.Last_Hash__c;
        
        // Build canonical string for hashing
        String canonicalString = buildCanonicalString(
            stream,
            seq,
            type,
            DateTime.now(),
            prevHash,
            payloadJsonCanonical,
            actorId,
            contactId,
            termId,
            receiptId
        );
        
        // Calculate hash
        Blob hashBlob = Crypto.generateDigest('SHA-256', Blob.valueOf(canonicalString));
        String hash = EncodingUtil.convertToHex(hashBlob).toLowerCase();
        
        // Create emission record
        Emission__c emission = new Emission__c(
            Stream__c = stream,
            Sequence__c = Decimal.valueOf(seq),
            Sequence_Num__c = Decimal.valueOf(seq),
            Type__c = type,
            OccurredAt__c = DateTime.now(),
            Actor__c = actorId,
            Contact__c = contactId,
            MembershipTerm__c = termId,
            ReceiptRef__c = receiptId,
            Membership_Term__c = String.valueOf(termId),
            Receipt__c = String.valueOf(receiptId),
            Payload__c = payloadJsonCanonical,
            PrevHash__c = prevHash,
            Hash__c = hash,
            Canonical__c = canonicalString,
            // Surrogate key used for grouping/dedupe
            Stream_Seq__c = stream + ':' + String.valueOf(seq)
        );
        
        // Set idempotency fields if provided
        if (idempotencyKey != null && idempotencyKey != '') {
            emission.Idempotency_Key__c = idempotencyKey;
            emission.Stream_Idem__c = stream + ':' + idempotencyKey;
        }
        
        insert emission;
        
        // Update stream allocator
        streamRow.Next_Sequence__c = Decimal.valueOf(seq + 1);
        streamRow.Last_Hash__c = hash;
        update streamRow;
        
        return emission;
    }
    
    /**
     * Builds a canonical string for hashing
     * @param stream The stream name
     * @param seq The sequence number
     * @param type The emission type
     * @param occurredAt The occurrence datetime
     * @param prevHash The previous hash
     * @param payloadJsonCanonical The canonicalized payload
     * @param actorId The actor Id (optional)
     * @param contactId The contact Id (optional)
     * @param termId The membership term Id (optional)
     * @param receiptId The receipt Id (optional)
     * @return The canonical string
     */
    private static String buildCanonicalString(
        String stream,
        Long seq,
        String type,
        DateTime occurredAt,
        String prevHash,
        String payloadJsonCanonical,
        Id actorId,
        Id contactId,
        Id termId,
        Id receiptId
    ) {
        String result = 'v=1\n';
        result += 'stream=' + stream + '\n';
        result += 'seq=' + String.valueOf(seq) + '\n';
        result += 'type=' + type + '\n';
        result += 'occurredAt=' + occurredAt.format('yyyy-MM-dd\'T\'HH:mm:ss\'Z\'') + '\n';
        result += 'prevHash=' + prevHash + '\n';
        result += 'payload=' + payloadJsonCanonical + '\n';
        result += 'actorId=' + (actorId != null ? String.valueOf(actorId) : '') + '\n';
        result += 'contactId=' + (contactId != null ? String.valueOf(contactId) : '') + '\n';
        result += 'termId=' + (termId != null ? String.valueOf(termId) : '') + '\n';
        result += 'receiptId=' + (receiptId != null ? String.valueOf(receiptId) : '');
        
        return result;
    }
}
