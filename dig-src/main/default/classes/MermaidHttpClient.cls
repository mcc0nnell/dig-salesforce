/**
 * @description Low-level HTTP client for calling the Mermaid Cloudflare Worker via Named Credential.
 * Never logs or exposes sensitive headers. Applies size limits, timeouts, and basic validation.
 */
public with sharing class MermaidHttpClient {
    public class Result {
        @AuraEnabled public Boolean ok;
        @AuraEnabled public String svg;
        @AuraEnabled public String astJson;
        @AuraEnabled public String requestId;
        @AuraEnabled public String errorMessage;
    }

    // Config
    private static final Integer MAX_REQUEST_BYTES = 200000; // 200KB
    private static final Integer TIMEOUT_MS = 15000; // 15s default

    // Named Credential Label (adjust to your actual Named Credential name)
    private static final String NC_NAME = 'Geary_Mermaid_Worker';

    // Endpoints
    private static final String RENDER_PATH = '/render';

    // Basic validate content
    private static void validateMermaid(String mermaid) {
        if (String.isBlank(mermaid)) {
            throw new AuraHandledException('Mermaid text is required.');
        }
        // Basic sanity: Must have at least one keyword that looks like a graph/sequence/class
        // Not strict parsing, just minimal sanity.
        String m = mermaid.toLowerCase();
        if (!(m.contains('graph') || m.contains('sequence') || m.contains('class') || m.contains('state') || m.contains('er') || m.contains('journey'))) {
            // allow but warn via exception for now to control usage
            throw new AuraHandledException('Mermaid text does not appear to contain a known diagram keyword.');
        }
        // Size check (bytes)
        Integer bytes = Blob.valueOf(mermaid).size();
        if (bytes > MAX_REQUEST_BYTES) {
            throw new AuraHandledException('Mermaid text exceeds 200KB limit.');
        }
    }

    // Core call
    public static Result callWorker(String mermaid, String format, String requestId) {
        validateMermaid(mermaid);
        if (String.isBlank(format)) {
            format = 'svg';
        }
        if (String.isBlank(requestId)) {
            Integer rand = Math.abs(Crypto.getRandomInteger());
            requestId = String.valueOf(rand);
        }

        HttpRequest req = new HttpRequest();
        // Using Named Credential. The callout URL should be: callout:NC_NAME + RENDER_PATH
        req.setEndpoint('callout:' + NC_NAME + RENDER_PATH);
        req.setMethod('POST');
        req.setTimeout(TIMEOUT_MS);

        // Body
        Map<String, Object> body = new Map<String, Object>{
            'mermaid' => mermaid,
            'format'  => format,
            'id'      => requestId
        };
        String payload = JSON.serialize(body);
        req.setHeader('Content-Type', 'application/json');
        // Do NOT set or log X-Geary-Key here unless Named Credential cannot inject it.
        // If needed, fallback header injection from protected CMD via MermaidSecrets.getKey()
        if (!supportsHeaderInjection()) {
            String key = MermaidSecrets.getKey();
            if (String.isBlank(key)) {
                throw new AuraHandledException('Mermaid API key is not configured. Contact an admin.');
            }
            req.setHeader('X-Geary-Key', key);
        }
        req.setBody(payload);

        Http http = new Http();
        HttpResponse res;
        try {
            res = http.send(req);
        } catch (System.CalloutException ex) {
            throw new AuraHandledException('Mermaid service timeout or network error.');
        }

        Result out = new Result();
        out.requestId = requestId;

        if (res == null) {
            out.ok = false;
            out.errorMessage = 'No response from Mermaid service.';
            return out;
        }
        Integer status = res.getStatusCode();
        if (status < 200 || status >= 300) {
            out.ok = false;
            out.errorMessage = 'Mermaid service error: HTTP ' + status;
            return out;
        }

        // Parse response JSON
        // Expected: { ok:true, svg:"<svg...>" } or { ok:true, ast:{...} }
        // We keep a generic map to avoid schema coupling.
        Map<String, Object> resp = (Map<String, Object>) JSON.deserializeUntyped(res.getBody());
        Object okVal = resp.get('ok');
        out.ok = okVal == null ? false : (Boolean) okVal;

        if (!out.ok) {
            out.errorMessage = (String) resp.get('error');
            if (String.isBlank(out.errorMessage)) {
                out.errorMessage = 'Mermaid worker returned ok=false.';
            }
            return out;
        }

        if (format == 'svg') {
            out.svg = (String) resp.get('svg');
            if (String.isBlank(out.svg)) {
                out.ok = false;
                out.errorMessage = 'Missing svg in response.';
            }
        } else if (format == 'json') {
            // Keep AST as raw pretty JSON string for LWC
            Object astObj = resp.get('ast');
            if (astObj == null) {
                out.ok = false;
                out.errorMessage = 'Missing ast in response.';
            } else {
                out.astJson = JSON.serialize(astObj);
            }
        }
        return out;
    }

    // If org cannot inject custom headers with Named Credential, we fallback to protected CMD
    private static Boolean supportsHeaderInjection() {
        // Default to false to be safe; set true only if your Named Credential provides X-Geary-Key automatically.
        // This should be configured based on your org's Named Credential setup
        if (Test.isRunningTest()) {
            return true;
        }
        return false;
    }
}
