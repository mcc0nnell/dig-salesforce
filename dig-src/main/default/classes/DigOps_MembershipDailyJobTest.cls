@IsTest
public class DigOps_MembershipDailyJobTest {
    @IsTest
    static void testDailyJobCreatesAndDedupesTasks() {
        Date today = Date.today();
        Contact c30 = DigOps_MembershipTestFactory.createContact('Notice30');
        Contact c14 = DigOps_MembershipTestFactory.createContact('Notice14');
        Contact c7 = DigOps_MembershipTestFactory.createContact('Notice7');

        DigOps_MembershipTestFactory.createMembership(
            c30.Id,
            today.addMonths(-1),
            today.addDays(30),
            'INDIVIDUAL',
            today.addMonths(-1),
            null,
            null
        );
        DigOps_MembershipTestFactory.createMembership(
            c14.Id,
            today.addMonths(-1),
            today.addDays(14),
            'INDIVIDUAL',
            today.addMonths(-1),
            null,
            null
        );
        DigOps_MembershipTestFactory.createMembership(
            c7.Id,
            today.addMonths(-1),
            today.addDays(7),
            'INDIVIDUAL',
            today.addMonths(-1),
            null,
            null
        );

        Test.startTest();
        new DigOps_MembershipDailyJob().execute(null);
        Test.stopTest();

        Integer initialCount = [
            SELECT Count()
            FROM Task
            WHERE WhoId IN :new Set<Id>{c30.Id, c14.Id, c7.Id}
        ];
        System.assertEquals(3, initialCount, 'Expected one task per window');

        new DigOps_MembershipDailyJob().execute(null);

        Integer secondCount = [
            SELECT Count()
            FROM Task
            WHERE WhoId IN :new Set<Id>{c30.Id, c14.Id, c7.Id}
        ];
        System.assertEquals(3, secondCount, 'Expected deduped tasks on rerun');
    }
}
