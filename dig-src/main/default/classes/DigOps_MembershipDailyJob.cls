public class DigOps_MembershipDailyJob implements Schedulable {
    public void execute(SchedulableContext sc) {
        Date today = Date.today();
        List<DIG_MembershipNoticeWindow__mdt> windows = DigOps_MembershipRules.getNoticeWindows();
        List<Task> tasksToInsert = new List<Task>();

        for (DIG_MembershipNoticeWindow__mdt window : windows) {
            Integer daysBefore = window.WindowDaysBeforeEnd__c == null
                ? 0
                : Integer.valueOf(window.WindowDaysBeforeEnd__c);
            if (daysBefore < 0) {
                continue;
            }
            if (window.CreateTask__c == false) {
                continue;
            }

            Date targetEndDate = today.addDays(daysBefore);
            List<Contact> contacts = [
                SELECT Id, OwnerId
                FROM Contact
                WHERE Membership_End_Date__c = :targetEndDate
                AND Membership_Status_Summary__c IN ('Active', 'Grace')
            ];
            if (contacts.isEmpty()) {
                continue;
            }

            String dedupeKey = String.isBlank(window.DedupeKey__c)
                ? 'NOTICE_' + String.valueOf(daysBefore)
                : window.DedupeKey__c;
            String marker = '[' + dedupeKey + ']';

            Set<Id> whoIds = new Set<Id>();
            for (Contact contact : contacts) {
                whoIds.add(contact.Id);
            }

            Set<Id> dedupedWhoIds = new Set<Id>();
            for (Task existing : [
                SELECT Id, WhoId
                FROM Task
                WHERE WhoId IN :whoIds
                AND IsClosed = false
                AND Subject LIKE :('%' + marker + '%')
                AND CreatedDate >= :System.now().addDays(-60)
            ]) {
                if (existing.WhoId != null) {
                    dedupedWhoIds.add(existing.WhoId);
                }
            }

            for (Contact contact : contacts) {
                if (dedupedWhoIds.contains(contact.Id)) {
                    continue;
                }
                Task task = new Task();
                task.WhoId = contact.Id;
                task.Subject = buildSubject(window.TaskSubject__c, daysBefore, marker);
                task.ActivityDate = today;
                task.Status = 'Not Started';
                task.Priority = 'Normal';
                task.OwnerId = resolveOwnerId(window, contact);
                tasksToInsert.add(task);
            }
        }

        if (!tasksToInsert.isEmpty()) {
            insert tasksToInsert;
        }
    }

    private static String buildSubject(String template, Integer days, String marker) {
        String base = String.isBlank(template)
            ? 'Membership renewal due in {days} days'
            : template;
        base = base.replace('{days}', String.valueOf(days));
        return marker + ' ' + base;
    }

    private static Id resolveOwnerId(DIG_MembershipNoticeWindow__mdt window, Contact contact) {
        String mode = window.TaskOwnerMode__c;
        if (mode == 'FixedUser' || mode == 'Queue') {
            if (!String.isBlank(window.TaskOwnerId__c)) {
                return (Id)window.TaskOwnerId__c;
            }
        }
        return contact.OwnerId;
    }
}
