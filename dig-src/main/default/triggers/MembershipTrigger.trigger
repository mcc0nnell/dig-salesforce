trigger MembershipTrigger on Membership__c (after insert, after update, after delete, after undelete) {
    Set<Id> contactIds = new Set<Id>();

    if (Trigger.isInsert || Trigger.isUpdate || Trigger.isUndelete) {
        for (Membership__c membership : Trigger.new) {
            if (membership.Contact__c != null) {
                contactIds.add(membership.Contact__c);
            }
        }
    }

    if (Trigger.isDelete) {
        for (Membership__c membership : Trigger.old) {
            if (membership.Contact__c != null) {
                contactIds.add(membership.Contact__c);
            }
        }
    }

    DigOps_MembershipService.recompute(contactIds);
}
