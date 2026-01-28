public class DIG_TA_Dispatcher {
  public static void run(String sobjectApiName, String phase, List<SObject> newList, Map<Id,SObject> oldMap) {
    if (DIG_TA_Bypass.isEnabled(sobjectApiName)) return;

    DIG_TA_Context ctx = new DIG_TA_Context(sobjectApiName, phase, newList, oldMap);
    List<DIG_TA_Action> actions = DIG_TA_Registry.actionsFor(sobjectApiName, phase);

    for (DIG_TA_Action a : actions) {
      if (a == null) continue;
      if (DIG_TA_Bypass.isActionBypassed(a.name())) continue;
      a.run(ctx);
    }
  }
}
