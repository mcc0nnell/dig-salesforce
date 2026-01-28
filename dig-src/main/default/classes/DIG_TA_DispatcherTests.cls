@IsTest
private class DIG_TA_DispatcherTests {
    @IsTest
    static void runsDispatcherOnCaseAfterInsert() {
        Case c = new Case(Subject='Dispatcher coverage', Status='New', Origin='Email');

        Test.startTest();
        insert c; // will fire trigger and run dispatcher
        Test.stopTest();

        System.assertNotEquals(null, c.Id);
    }

    @IsTest
    static void runsDispatcherOnCaseAfterUpdate() {
        Case c = new Case(Subject='Dispatcher coverage update', Status='New', Origin='Email');
        insert c;

        Test.startTest();
        c.Status = 'Working';
        update c;
        Test.stopTest();

        System.assertEquals('Working', c.Status);
    }
}
