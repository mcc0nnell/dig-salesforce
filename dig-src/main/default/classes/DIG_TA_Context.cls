public class DIG_TA_Context {
  public final String sobjectApiName;
  public final String phase;
  public final List<SObject> newList;
  public final Map<Id,SObject> oldMap;

  public DIG_TA_Context(String sobjectApiName, String phase, List<SObject> newList, Map<Id,SObject> oldMap) {
    this.sobjectApiName = sobjectApiName;
    this.phase = phase;
    this.newList = (newList == null) ? new List<SObject>() : newList;
    this.oldMap = (oldMap == null) ? new Map<Id,SObject>() : oldMap;
  }
}
