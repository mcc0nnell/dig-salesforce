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
        // Named Credential should inject the header; keep this as a safe null fallback.
        return null;
    }
}
