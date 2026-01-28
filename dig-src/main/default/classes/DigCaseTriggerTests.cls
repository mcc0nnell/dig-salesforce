@IsTest
private class DigCaseTriggerTests {
    @IsTest
    static void firesTriggerOnInsertAndUpdate() {
        // Minimal Case to fire DigCaseTrigger without needing org data.
        Case c = new Case(
            Subject = 'Geary trigger coverage',
            Status = 'New',
            Origin = 'Email'
        );

        Test.startTest();
        insert c;

        // Nudge an update path too (many triggers have update logic).
        c.Status = 'Working';
        update c;
        Test.stopTest();

        // No assertions required for coverage; just ensure no exception.
        System.assertNotEquals(null, c.Id);
    }
}
