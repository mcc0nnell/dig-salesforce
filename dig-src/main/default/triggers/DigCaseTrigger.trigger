trigger DigCaseTrigger on Case (after insert) {
  DIG_TA_Dispatcher.run('Case', 'after insert', (List<SObject>) Trigger.new, null);
}
