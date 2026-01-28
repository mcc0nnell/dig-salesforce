public class DigCaseAction_ClassifyAndRoute implements DIG_TA_Action {
  public String name() { return 'DigCaseAction_ClassifyAndRoute'; }

  public void run(DIG_TA_Context ctx) {
    List<Case> updates = new List<Case>();

    for (SObject sob : ctx.newList) {
      Case c = (Case) sob;

      String body = (c.Description == null) ? '' : c.Description.toLowerCase();
      String subj = (c.Subject == null) ? '' : c.Subject.toLowerCase();
      String text = subj + ' ' + body;

      // Topic
      String topic = 'General';
      if (containsAny(text, new List<String>{'join','renew','dues','member','login'})) topic = 'Membership';
      else if (containsAny(text, new List<String>{'summit','event','registration','schedule','ticket'})) topic = 'Summit';
      else if (containsAny(text, new List<String>{'motion','vote','board','minutes'})) topic = 'Governance';
      else if (containsAny(text, new List<String>{'sponsor','donate','partnership','funding'})) topic = 'Sponsorship';

      // Urgency
      String urgency = containsAny(text, new List<String>{'urgent','asap','accessibility issue','cannot access','refund'})
        ? 'High' : 'Normal';

      // Sensitive
      Boolean sensitive = containsAny(text, new List<String>{'credit card','payment','chargeback','ssn','bank'});

      // SLA: 1 business day default (simple: +24h; replace with business hours later)
      Datetime firstBy = System.now().addHours(24);

      Case u = new Case(Id=c.Id);
      u.put('DIG_Topic__c', topic);
      u.put('DIG_Urgency__c', urgency);
      u.put('DIG_Sensitive__c', sensitive);
      u.put('DIG_SLA_FirstResponseBy__c', firstBy);
      u.put('DIG_SLA_Status__c', 'OnTrack');

      // AI draft hook
      if (!sensitive) u.put('DIG_AI_Draft_Status__c', 'Requested');
      else u.put('DIG_AI_Draft_Status__c', 'Suppressed');

      updates.add(u);
    }

    if (!updates.isEmpty()) update updates;
  }

  private static Boolean containsAny(String hay, List<String> needles) {
    for (String n : needles) if (hay.contains(n)) return true;
    return false;
  }
}
