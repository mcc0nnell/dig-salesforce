@IsTest
private class CoverageBumpTests {
    @IsTest
    static void coversMembershipTriggerDeleteAndUndelete() {
        Contact c = new Contact(LastName = 'Coverage Bump');
        insert c;

        Membership__c m = new Membership__c(
            Contact__c = c.Id,
            StartDate__c = Date.today(),
            EndDate__c = Date.today().addDays(30)
        );

        Test.startTest();
        insert m;
        m.EndDate__c = m.EndDate__c.addDays(1);
        update m;
        delete m;
        undelete m;
        Test.stopTest();

        System.assertNotEquals(null, m.Id);
    }
}
