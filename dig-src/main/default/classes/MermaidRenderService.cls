/**
 * @description Mermaid rendering/parse service exposed to LWC. Wraps MermaidHttpClient and adds Blueprint generation.
 * Security:
 * - Calls out via Named Credential (MermaidHttpClient). API key never exposed to client.
 * - Validates payload size and basic content in MermaidHttpClient.
 * - Returns only necessary data to the UI.
 */
public with sharing class MermaidRenderService {
    public class AstAndBlueprint {
        @AuraEnabled public String astJson;       // Raw AST JSON string (pretty as returned)
        @AuraEnabled public String blueprintJson; // Generated minimal App Blueprint JSON
        @AuraEnabled public String requestId;
        @AuraEnabled public String svg;
    }

    @AuraEnabled(cacheable=false)
    public static String renderSvg(String mermaid, String id) {
        MermaidHttpClient.Result res = MermaidHttpClient.callWorker(mermaid, 'svg', id);
        if (res == null || res.ok == false) {
            throw new AuraHandledException(res == null ? 'Mermaid render failed.' : safeMsg(res.errorMessage));
        }
        return res.svg;
    }

    @AuraEnabled(cacheable=false)
    public static AstAndBlueprint parseAst(String mermaid, String id) {
        MermaidHttpClient.Result res = MermaidHttpClient.callWorker(mermaid, 'json', id);
        if (res == null || res.ok == false) {
            throw new AuraHandledException(res == null ? 'Mermaid parse failed.' : safeMsg(res.errorMessage));
        }
        AstAndBlueprint out = new AstAndBlueprint();
        out.astJson = res.astJson;
        out.requestId = res.requestId;
        out.blueprintJson = generateBlueprintFromAst(res.astJson);
        return out;
    }

    @AuraEnabled(cacheable=false)
    public static AstAndBlueprint renderBoth(String mermaid, String id) {
        // First get the AST and blueprint
        AstAndBlueprint result = parseAst(mermaid, id);
        // Then get the SVG
        MermaidHttpClient.Result res = MermaidHttpClient.callWorker(mermaid, 'svg', id);
        if (res == null || res.ok == false) {
            throw new AuraHandledException(res == null ? 'Mermaid render failed.' : safeMsg(res.errorMessage));
        }
        result.svg = res.svg;
        return result;
    }

    // MVP blueprint generator: map nodes to objects/screens and edges to actions/flows
    @TestVisible
    private static String generateBlueprintFromAst(String astJson) {
        // Default minimal structure
        Map<String, Object> blueprint = new Map<String, Object>{
            'objects'   => new List<Object>(),
            'fields'    => new List<Object>(),
            'lwcPages'  => new List<Object>(),
            'actions'   => new List<Object>()
        };
        if (String.isBlank(astJson)) {
            return JSON.serializePretty(blueprint);
        }
        // Attempt to deserialize AST (structure can vary by diagram type)
        Object root = JSON.deserializeUntyped(astJson);
        if (!(root instanceof Map<String, Object>)) {
            return JSON.serializePretty(blueprint);
        }
        Map<String, Object> ast = (Map<String, Object>) root;

        // Heuristics to extract nodes and edges across common Mermaid types;
        // We look for generic collections named "nodes", "vertices", "classes", etc., and "edges", "links", "relations".
        Set<String> nodeKeys = new Set<String>{'nodes','vertices','classDefs','classes','states','items'};
        Set<String> edgeKeys = new Set<String>{'edges','links','relations','relationships','transitions'};

        List<Map<String, Object>> nodes = new List<Map<String, Object>>();
        List<Map<String, Object>> edges = new List<Map<String, Object>>();

        // Breadth-first gather of candidates
        collectNodesAndEdges(ast, nodeKeys, edgeKeys, nodes, edges, 0, 3); // limit depth to avoid massive traversals

        // Build blueprint pieces
        List<Object> objects = (List<Object>) blueprint.get('objects');
        List<Object> lwcPages = (List<Object>) blueprint.get('lwcPages');
        List<Object> actions = (List<Object>) blueprint.get('actions');

        // Map nodes to candidate objects/pages
        for (Map<String, Object> n : nodes) {
            String name = coerceString(n.get('id'));
            if (String.isBlank(name)) {
                name = coerceString(n.get('name'));
            }
            if (String.isBlank(name)) {
                name = coerceString(n.get('label'));
            }
            if (String.isBlank(name)) continue;

            Map<String, Object> obj = new Map<String, Object>{
                'apiName' => sanitizeApiName(name),
                'label'   => name
            };
            objects.add(obj);

            Map<String, Object> page = new Map<String, Object>{
                'name'  => name + 'Page',
                'title' => name + ' Screen'
            };
            lwcPages.add(page);
        }

        // Map edges to candidate actions/flows
        for (Map<String, Object> e : edges) {
            String fromId = coerceString(e.get('from'));
            if (String.isBlank(fromId)) fromId = coerceString(e.get('start'));
            String toId   = coerceString(e.get('to'));
            if (String.isBlank(toId))   toId   = coerceString(e.get('end'));

            String label = coerceString(e.get('label'));
            if (String.isBlank(label))  label = coerceString(e.get('title'));

            if (String.isBlank(fromId) && String.isBlank(toId) && String.isBlank(label)) continue;

            Map<String, Object> action = new Map<String, Object>{
                'name'      => sanitizeApiName((String.isBlank(label) ? 'Action' : label)),
                'from'      => fromId,
                'to'        => toId,
                'actionType'=> 'Flow'
            };
            actions.add(action);
        }

        return JSON.serializePretty(blueprint);
    }

    // Recursively look for arrays under known keys; depth-limited for safety
    private static void collectNodesAndEdges(Object node, Set<String> nodeKeys, Set<String> edgeKeys,
                                             List<Map<String, Object>> nodes, List<Map<String, Object>> edges,
                                             Integer depth, Integer maxDepth) {
        if (depth > maxDepth || node == null) return;
        if (node instanceof Map<String, Object>) {
            Map<String, Object> m = (Map<String, Object>) node;
            for (String key : m.keySet()) {
                Object val = m.get(key);
                if (val == null) continue;
                String keyLower = key == null ? null : key.toLowerCase();
                if (keyLower != null && nodeKeys.contains(keyLower) && val instanceof List<Object>) {
                    for (Object o : (List<Object>) val) {
                        if (o instanceof Map<String, Object>) nodes.add((Map<String, Object>) o);
                    }
                }
                if (keyLower != null && edgeKeys.contains(keyLower) && val instanceof List<Object>) {
                    for (Object o : (List<Object>) val) {
                        if (o instanceof Map<String, Object>) edges.add((Map<String, Object>) o);
                    }
                }
                collectNodesAndEdges(val, nodeKeys, edgeKeys, nodes, edges, depth+1, maxDepth);
            }
        } else if (node instanceof List<Object>) {
            for (Object o : (List<Object>) node) {
                collectNodesAndEdges(o, nodeKeys, edgeKeys, nodes, edges, depth+1, maxDepth);
            }
        }
    }

    // Helpers
    @TestVisible
    private static String coerceString(Object o) {
        return o == null ? null : String.valueOf(o);
    }
    @TestVisible
    private static String sanitizeApiName(String s) {
        if (String.isBlank(s)) return null;
        String out = s.replaceAll('[^A-Za-z0-9_]', '_');
        if (!Pattern.matches('^[A-Za-z_].*', out)) {
            out = 'A_' + out;
        }
        return out;
    }
    private static String safeMsg(String s) {
        return String.isBlank(s) ? 'Mermaid service error.' : s;
    }
}
