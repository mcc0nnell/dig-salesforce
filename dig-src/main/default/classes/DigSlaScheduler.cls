global class DigSlaScheduler implements Schedulable {
  global void execute(SchedulableContext sc) {
    Datetime nowDt = System.now();

    List<Case> updates = new List<Case>();
    for (Case c : [
      SELECT Id, DIG_SLA_FirstResponseBy__c, DIG_SLA_Status__c
      FROM Case
      WHERE DIG_SLA_FirstResponseBy__c != null
      AND IsClosed = false
      AND DIG_SLA_Status__c != 'Breached'
      LIMIT 5000
    ]) {
      Datetime by = c.DIG_SLA_FirstResponseBy__c;
      if (by == null) continue;

      if (nowDt > by) {
        updates.add(new Case(Id=c.Id, DIG_SLA_Status__c='Breached'));
      } else if (nowDt.addHours(4) > by) {
        updates.add(new Case(Id=c.Id, DIG_SLA_Status__c='AtRisk'));
      }
    }

    if (!updates.isEmpty()) update updates;
  }

  public static void scheduleHourly() {
    String cron = '0 10 * * * ?';
    System.schedule('DigSlaSchedulerHourly', cron, new DigSlaScheduler());
  }
}
