global with sharing class DigMembershipService {
    public class JoinRequest {
        public String firstName;
        public String lastName;
        public String email;
        public String phone;
        public String organization;
        public Boolean optInEmail;
        public String source;
    }

    global class JoinResult {
        public Boolean ok;
        public String message;
        public Id contactId;
        public Id membershipTermId;
        public String receiptId;
    }

    public class ValidationException extends Exception {
    }

    @TestVisible
    private static final Pattern EMAIL_PATTERN =
        Pattern.compile('^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$');

    public static JoinResult join(JoinRequest input) {
        JoinRequest request = normalize(input);
        String validationMessage = validate(request);
        if (validationMessage != null) {
            throw new ValidationException(validationMessage);
        }

        Contact contact = findOrCreateContact(request);
        Date today = Date.today();
        Membership_Term__c existingTerm = findActiveTerm(contact.Id, today);

        Date termStart = existingTerm != null ? existingTerm.Term_Start__c : today;
        Date termEnd = existingTerm != null ? existingTerm.Term_End__c : today.addYears(1).addDays(-1);

        String emailLower = request.email.toLowerCase();
        String receiptKey = computeReceiptKey(emailLower, termStart);
        Receipt__c receipt = findOrCreateReceipt(receiptKey, request, contact.Id, termStart, termEnd);

        Membership_Term__c term = existingTerm;
        if (term == null) {
            term = new Membership_Term__c(
                Contact__c = contact.Id,
                Term_Start__c = termStart,
                Term_End__c = termEnd,
                Status__c = 'Active',
                Source__c = request.source,
                Receipt__c = receipt.Id
            );
            insert term;
        } else if (term.Receipt__c == null && receipt.Id != null) {
            term.Receipt__c = receipt.Id;
            update term;
        }

        // Emit membership.joined using appendOnce
        String normalizedOrganization = normalizeOrganization(request.organization);
        Map<String, Object> payload = new Map<String, Object>();
        payload.put('emailLower', emailLower);
        payload.put('termStart', String.valueOf(termStart));
        payload.put('termEnd', String.valueOf(termEnd));
        payload.put('contactId', contact.Id);
        payload.put('membershipTermId', term.Id);
        payload.put('receiptId', receipt.Id);
        payload.put('orgCaptured', !String.isBlank(normalizedOrganization));
        payload.put('optInCaptured', request.optInEmail == true);
        payload.put('source', request.source);
        
        String payloadJson = CanonicalJson.canonicalize(payload);
        
        EmissionService.appendOnce(
            'membership',
            receiptKey,
            'membership.joined',
            payloadJson,
            UserInfo.getUserId(),
            contact.Id,
            term.Id,
            receipt.Id
        );

        JoinResult result = new JoinResult();
        result.ok = true;
        result.message = 'OK';
        result.contactId = contact.Id;
        result.membershipTermId = term.Id;
        result.receiptId = receipt.Id != null ? String.valueOf(receipt.Id) : receiptKey;
        return result;
    }

    @TestVisible
    private static String computeReceiptKey(String emailLower, Date termStart) {
        String seed = emailLower + ':' + String.valueOf(termStart);
        Blob digest = Crypto.generateDigest('SHA-256', Blob.valueOf(seed));
        return EncodingUtil.convertToHex(digest).toLowerCase();
    }

    private static JoinRequest normalize(JoinRequest input) {
        JoinRequest request = input == null ? new JoinRequest() : input;
        request.firstName = trim(request.firstName);
        request.lastName = trim(request.lastName);
        request.email = trim(request.email);
        request.phone = trim(request.phone);
        request.organization = trim(request.organization);
        request.source = trim(request.source);
        return request;
    }

    private static String trim(String value) {
        return value == null ? null : value.trim();
    }

    private static String validate(JoinRequest request) {
        if (String.isBlank(request.lastName)) {
            return 'Last name is required';
        }
        if (String.isBlank(request.email)) {
            return 'Email is required';
        }
        String emailLower = request.email.toLowerCase();
        if (!EMAIL_PATTERN.matcher(emailLower).matches()) {
            return 'Email is invalid';
        }
        return null;
    }

    private static Contact findOrCreateContact(JoinRequest request) {
        String normalizedOrganization = normalizeOrganization(request.organization);
        List<Contact> matches = [
            SELECT Id, FirstName, LastName, Email, Phone, Department, DIG_Organization__c, DIG_Email_Opt_In__c
            FROM Contact
            WHERE Email = :request.email
            ORDER BY LastModifiedDate DESC
            LIMIT 1
        ];

        if (!matches.isEmpty()) {
            Contact existing = matches[0];
            Contact updateContact = new Contact(Id = existing.Id);
            Boolean needsUpdate = false;

            if (String.isBlank(existing.FirstName) && !String.isBlank(request.firstName)) {
                updateContact.FirstName = request.firstName;
                needsUpdate = true;
            }
            if (String.isBlank(existing.LastName) && !String.isBlank(request.lastName)) {
                updateContact.LastName = request.lastName;
                needsUpdate = true;
            }
            if (String.isBlank(existing.Phone) && !String.isBlank(request.phone)) {
                updateContact.Phone = request.phone;
                needsUpdate = true;
            }
            if (!String.isBlank(normalizedOrganization)) {
                // First-write-wins for organization: preserve existing non-empty value.
                if (String.isBlank(existing.DIG_Organization__c)) {
                    updateContact.DIG_Organization__c = normalizedOrganization;
                    needsUpdate = true;
                }
            }
            if (request.optInEmail == true && existing.DIG_Email_Opt_In__c != true) {
                updateContact.DIG_Email_Opt_In__c = true;
                needsUpdate = true;
            }

            if (needsUpdate) {
                update updateContact;
            }
            return existing;
        }

        Contact contact = new Contact(
            FirstName = request.firstName,
            LastName = request.lastName,
            Email = request.email,
            Phone = request.phone
        );
        if (!String.isBlank(normalizedOrganization)) {
            contact.DIG_Organization__c = normalizedOrganization;
        }
        if (request.optInEmail == true) {
            contact.DIG_Email_Opt_In__c = true;
        }
        insert contact;
        return contact;
    }

    private static String normalizeOrganization(String organization) {
        String value = trim(organization);
        return String.isBlank(value) ? null : value;
    }

    private static Membership_Term__c findActiveTerm(Id contactId, Date today) {
        List<Membership_Term__c> terms = [
            SELECT Id, Term_Start__c, Term_End__c, Status__c, Receipt__c
            FROM Membership_Term__c
            WHERE Contact__c = :contactId
              AND Status__c = 'Active'
              AND Term_Start__c <= :today
              AND Term_End__c >= :today
            ORDER BY Term_Start__c DESC
            LIMIT 1
        ];
        return terms.isEmpty() ? null : terms[0];
    }

    private static Receipt__c findOrCreateReceipt(
        String receiptKey,
        JoinRequest request,
        Id contactId,
        Date termStart,
        Date termEnd
    ) {
        List<Receipt__c> existing = [
            SELECT Id, External_Id__c
            FROM Receipt__c
            WHERE External_Id__c = :receiptKey
            LIMIT 1
        ];
        if (!existing.isEmpty()) {
            return existing[0];
        }

        Receipt__c receipt = new Receipt__c(
            External_Id__c = receiptKey,
            Type__c = 'membership.join',
            Payload__c = buildReceiptPayload(request, contactId, termStart, termEnd, receiptKey),
            OccurredAt__c = System.now()
        );
        insert receipt;
        return receipt;
    }

    private static String buildReceiptPayload(
        JoinRequest request,
        Id contactId,
        Date termStart,
        Date termEnd,
        String receiptKey
    ) {
        Map<String, Object> payload = new Map<String, Object>();
        Map<String, Object> requestPayload = new Map<String, Object>();
        requestPayload.put('firstName', request.firstName);
        requestPayload.put('lastName', request.lastName);
        requestPayload.put('email', request.email);
        requestPayload.put('phone', request.phone);
        requestPayload.put('organization', request.organization);
        requestPayload.put('optInEmail', request.optInEmail);
        requestPayload.put('source', request.source);

        payload.put('request', requestPayload);
        payload.put('contactId', contactId);
        payload.put('termStart', String.valueOf(termStart));
        payload.put('termEnd', String.valueOf(termEnd));
        payload.put('receiptKey', receiptKey);
        return JSON.serialize(payload);
    }
}
