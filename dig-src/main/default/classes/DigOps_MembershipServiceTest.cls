@IsTest
public class DigOps_MembershipServiceTest {
    @IsTest
    static void testActiveMembershipSummary() {
        Date today = Date.today();
        Contact contact = DigOps_MembershipTestFactory.createContact('Active');
        DigOps_MembershipTestFactory.createMembership(
            contact.Id,
            today.addMonths(-1),
            today.addMonths(1),
            'INDIVIDUAL',
            today.addMonths(-1),
            null,
            null
        );

        Contact refreshed = [
            SELECT Is_Current_Member__c, Membership_Status_Summary__c, Membership_End_Date__c
            FROM Contact
            WHERE Id = :contact.Id
        ];
        System.assertEquals(true, refreshed.Is_Current_Member__c, 'Active should be current member');
        System.assertEquals('Active', refreshed.Membership_Status_Summary__c, 'Active summary');
        System.assertEquals(today.addMonths(1), refreshed.Membership_End_Date__c, 'End date carried');
    }

    @IsTest
    static void testGraceMembershipSummary() {
        Date today = Date.today();
        Contact contact = DigOps_MembershipTestFactory.createContact('Grace');
        DigOps_MembershipTestFactory.createMembership(
            contact.Id,
            today.addMonths(-2),
            today.addDays(-1),
            'INDIVIDUAL',
            today.addMonths(-2),
            null,
            null
        );

        Contact refreshed = [
            SELECT Is_Current_Member__c, Membership_Status_Summary__c
            FROM Contact
            WHERE Id = :contact.Id
        ];
        System.assertEquals(false, refreshed.Is_Current_Member__c, 'Grace should not be current');
        System.assertEquals('Grace', refreshed.Membership_Status_Summary__c, 'Grace summary');
    }

    @IsTest
    static void testLapsedMembershipSummary() {
        Date today = Date.today();
        Contact contact = DigOps_MembershipTestFactory.createContact('Lapsed');
        DigOps_MembershipTestFactory.createMembership(
            contact.Id,
            today.addMonths(-3),
            today.addDays(-45),
            'INDIVIDUAL',
            today.addMonths(-3),
            null,
            null
        );

        Contact refreshed = [
            SELECT Membership_Status_Summary__c
            FROM Contact
            WHERE Id = :contact.Id
        ];
        System.assertEquals('Lapsed', refreshed.Membership_Status_Summary__c, 'Lapsed summary');
    }

    @IsTest
    static void testLatestTermSelection() {
        Date today = Date.today();
        Contact contact = DigOps_MembershipTestFactory.createContact('TwoTerms');
        DigOps_MembershipTestFactory.createMembership(
            contact.Id,
            today.addMonths(-14),
            today.addMonths(-2),
            'INDIVIDUAL',
            today.addMonths(-14),
            null,
            null
        );
        DigOps_MembershipTestFactory.createMembership(
            contact.Id,
            today.addMonths(-1),
            today.addMonths(2),
            'INDIVIDUAL',
            today.addMonths(-1),
            null,
            null
        );

        Contact refreshed = [
            SELECT Membership_End_Date__c, Membership_Status_Summary__c
            FROM Contact
            WHERE Id = :contact.Id
        ];
        System.assertEquals(today.addMonths(2), refreshed.Membership_End_Date__c, 'Latest term end date selected');
        System.assertEquals('Active', refreshed.Membership_Status_Summary__c, 'Latest term status');
    }

    @IsTest
    static void testPendingWhenUnpaid() {
        Date today = Date.today();
        Contact contact = DigOps_MembershipTestFactory.createContact('Pending');
        Membership__c membership = DigOps_MembershipTestFactory.createMembership(
            contact.Id,
            today.addDays(-1),
            today.addMonths(1),
            'INDIVIDUAL',
            null,
            null,
            null
        );

        Membership__c refreshed = [SELECT Status__c FROM Membership__c WHERE Id = :membership.Id];
        System.assertEquals('Pending', refreshed.Status__c, 'Unpaid membership should be pending');
    }
}
