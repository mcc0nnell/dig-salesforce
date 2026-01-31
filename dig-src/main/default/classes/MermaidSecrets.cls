/**
 * @description Secure storage and retrieval of Mermaid API key from Protected Custom Metadata.
 * This class provides a fallback mechanism when Named Credential cannot inject the X-Geary-Key header.
 */
public with sharing class MermaidSecrets {
    
    /**
     * @description Retrieves the Mermaid API key from Protected Custom Metadata.
     * @return The API key string or null if not found
     */
    public static String getKey() {
        // Query the protected custom metadata record
        List<Geary_Key__mdt> keys = [SELECT Id, Key__c FROM Geary_Key__mdt WHERE DeveloperName = 'Mermaid_API_Key' LIMIT 1];
        if (keys.isEmpty()) {
            return null;
        }
        return keys[0].Key__c;
    }
}
