public class DIG_TA_Registry {
  public static List<DIG_TA_Action> actionsFor(String sobjectApiName, String phase) {
    List<DIG_TA_Action> actions = new List<DIG_TA_Action>();

    if (sobjectApiName == 'Case' && phase == 'after insert') {
      actions.add(new DigCaseAction_ClassifyAndRoute());
      actions.add(new DigCaseAction_AutoAcknowledge());
    }

    return actions;
  }
}
