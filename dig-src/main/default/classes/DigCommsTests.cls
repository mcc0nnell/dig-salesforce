@IsTest
public class DigCommsTests {
  @IsTest
  static void classify_setsTopicAndSla() {
    Case c = new Case(
      Subject='Renew membership ASAP',
      Description='I need to renew my dues, urgent.',
      Origin='Email'
    );
    insert c;

    Case got = [SELECT DIG_Topic__c, DIG_Urgency__c, DIG_Sensitive__c, DIG_AI_Draft_Status__c, DIG_SLA_FirstResponseBy__c, DIG_SLA_Status__c
                FROM Case WHERE Id = :c.Id];

    System.assertEquals('Membership', got.DIG_Topic__c);
    System.assertEquals('High', got.DIG_Urgency__c);
    System.assertEquals(false, got.DIG_Sensitive__c);
    System.assertEquals('Requested', got.DIG_AI_Draft_Status__c);
    System.assertEquals('OnTrack', got.DIG_SLA_Status__c);
    System.assertNotEquals(null, got.DIG_SLA_FirstResponseBy__c);
  }
}
