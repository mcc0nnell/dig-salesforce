public class DIG_TA_Bypass {
  private static Set<String> bypassObjects = new Set<String>();
  private static Set<String> bypassActions = new Set<String>();

  public static void enable(String sobjectApiName) { bypassObjects.add(sobjectApiName); }
  public static void disable(String sobjectApiName) { bypassObjects.remove(sobjectApiName); }
  public static Boolean isEnabled(String sobjectApiName) { return bypassObjects.contains(sobjectApiName); }

  public static void enableAction(String actionName) { bypassActions.add(actionName); }
  public static void disableAction(String actionName) { bypassActions.remove(actionName); }
  public static Boolean isActionBypassed(String actionName) { return bypassActions.contains(actionName); }

  @TestVisible static void reset() { bypassObjects.clear(); bypassActions.clear(); }
}
