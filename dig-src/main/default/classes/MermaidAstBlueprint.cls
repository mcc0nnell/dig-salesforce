/**
 * @description Helper class for generating App Blueprint from Mermaid AST.
 * This class is used by MermaidRenderService to transform AST into a minimal "App Blueprint".
 */
public with sharing class MermaidAstBlueprint {
    
    /**
     * @description Generates a minimal App Blueprint from AST JSON.
     * @param astJson The raw AST JSON string from Mermaid worker
     * @return Pretty-printed JSON string representing the App Blueprint
     */
    public static String generateBlueprintFromAst(String astJson) {
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

    /**
     * @description Recursively look for arrays under known keys; depth-limited for safety
     */
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

    /**
     * @description Helper to convert object to string
     */
    private static String coerceString(Object o) {
        return o == null ? null : String.valueOf(o);
    }

    /**
     * @description Sanitize string for use as API name
     */
    private static String sanitizeApiName(String s) {
        if (String.isBlank(s)) return null;
        String out = s.replaceAll('[^A-Za-z0-9_]', '_');
        if (!Pattern.matches('^[A-Za-z_].*', out)) {
            out = 'A_' + out;
        }
        return out;
    }
}
