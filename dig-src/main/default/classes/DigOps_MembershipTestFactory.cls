@IsTest
public class DigOps_MembershipTestFactory {
    public static Contact createContact(String lastName) {
        Contact contact = new Contact(LastName = lastName);
        insert contact;
        return contact;
    }

    public static Membership__c createMembership(
        Id contactId,
        Date startDate,
        Date endDate,
        String levelKey,
        Date paidDate,
        Date cancelledDate,
        String status
    ) {
        Membership__c membership = new Membership__c(
            Contact__c = contactId,
            StartDate__c = startDate,
            EndDate__c = endDate,
            Level__c = levelKey,
            PaidDate__c = paidDate,
            CancelledDate__c = cancelledDate,
            Status__c = status
        );
        insert membership;
        return membership;
    }
}
