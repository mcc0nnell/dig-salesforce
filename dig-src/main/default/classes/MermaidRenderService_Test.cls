@isTest
public class MermaidRenderService_Test {
    
    @isTest
    static void testRenderSvgSuccess() {
        // Mock the HTTP callout
        Test.setMock(HttpCalloutMock.class, new MermaidTestCalloutMock());
        
        String mockMermaid = 'graph TD\n    A-->B';
        String result = MermaidRenderService.renderSvg(mockMermaid, 'test-id-123');
        
        // Verify result is not null and contains expected SVG content
        System.assertNotEquals(null, result);
        System.assert(result.contains('<svg'), 'Result should contain SVG content');
    }
    
    @isTest
    static void testRenderSvgFailure() {
        // Mock the HTTP callout to return an error
        Test.setMock(HttpCalloutMock.class, new MermaidErrorCalloutMock());
        
        String mockMermaid = 'graph TD\n    A-->B';
        
        try {
            MermaidRenderService.renderSvg(mockMermaid, 'test-id-123');
            System.assert(false, 'Expected AuraHandledException to be thrown');
        } catch (AuraHandledException e) {
            // Expected
            System.assert(e.getMessage() != null, 'Should have error message');
        }
    }
    
    @isTest
    static void testParseAstSuccess() {
        // Mock the HTTP callout
        Test.setMock(HttpCalloutMock.class, new MermaidTestCalloutMock());
        
        String mockMermaid = 'graph TD\n    A-->B';
        MermaidRenderService.AstAndBlueprint result = MermaidRenderService.parseAst(mockMermaid, 'test-id-123');
        
        // Verify result is not null
        System.assertNotEquals(null, result);
        System.assertNotEquals(null, result.astJson);
        System.assertNotEquals(null, result.blueprintJson);
        System.assertNotEquals(null, result.requestId);
    }

    @isTest
    static void testRenderBothSuccess() {
        // Mock the HTTP callout
        Test.setMock(HttpCalloutMock.class, new MermaidTestCalloutMock());
        
        String mockMermaid = 'graph TD\n    A-->B';
        MermaidRenderService.AstAndBlueprint result = MermaidRenderService.renderBoth(mockMermaid, 'test-id-123');
        
        // Verify result is not null
        System.assertNotEquals(null, result);
        System.assertNotEquals(null, result.astJson);
        System.assertNotEquals(null, result.blueprintJson);
        System.assertNotEquals(null, result.requestId);
        System.assertNotEquals(null, result.svg); // Should also have SVG
    }
    
    @isTest
    static void testGenerateBlueprintFromAst() {
        // Test with null/empty input
        String result1 = MermaidRenderService.generateBlueprintFromAst(null);
        System.assertNotEquals(null, result1);
        
        String result2 = MermaidRenderService.generateBlueprintFromAst('');
        System.assertNotEquals(null, result2);
        
        // Test with valid AST JSON (mocked)
        String mockAstJson = '{"nodes":[{"id":"A","label":"Node A"}],"edges":[{"from":"A","to":"B"}]}';
        String result3 = MermaidRenderService.generateBlueprintFromAst(mockAstJson);
        System.assertNotEquals(null, result3);
    }
    
    @isTest
    static void testCoerceString() {
        String result1 = MermaidRenderService.coerceString(null);
        System.assertEquals(null, result1);
        
        String result2 = MermaidRenderService.coerceString('test');
        System.assertEquals('test', result2);
        
        Integer num = 123;
        String result3 = MermaidRenderService.coerceString(num);
        System.assertEquals('123', result3);
    }
    
    @isTest
    static void testSanitizeApiName() {
        String result1 = MermaidRenderService.sanitizeApiName(null);
        System.assertEquals(null, result1);
        
        String result2 = MermaidRenderService.sanitizeApiName('Valid_Name');
        System.assertEquals('Valid_Name', result2);
        
        String result3 = MermaidRenderService.sanitizeApiName('Invalid-Name');
        System.assertEquals('Invalid_Name', result3);
        
        String result4 = MermaidRenderService.sanitizeApiName('123Invalid');
        System.assertEquals('A_123Invalid', result4);
    }

    @isTest
    static void testMermaidAstBlueprintGenerate() {
        String mockAstJson = '{"nodes":[{"id":"A","label":"Node A"}],"edges":[{"from":"A","to":"B"}]}';
        String result = MermaidAstBlueprint.generateBlueprintFromAst(mockAstJson);
        System.assertNotEquals(null, result);
        System.assert(result.contains('objects'), 'Blueprint should include objects');
    }

    @isTest
    static void testMermaidHttpClientCallWorkerSvg() {
        Test.setMock(HttpCalloutMock.class, new MermaidTestCalloutMock());
        String mockMermaid = 'graph TD\n    A-->B';
        MermaidHttpClient.Result res = MermaidHttpClient.callWorker(mockMermaid, 'svg', 'test-id-123');
        System.assertEquals(true, res.ok);
        System.assertNotEquals(null, res.svg);
        System.assertEquals('test-id-123', res.requestId);
    }

    @isTest
    static void testMermaidHttpClientCallWorkerJson() {
        Test.setMock(HttpCalloutMock.class, new MermaidTestCalloutMock());
        String mockMermaid = 'graph TD\n    A-->B';
        MermaidHttpClient.Result res = MermaidHttpClient.callWorker(mockMermaid, 'json', 'test-id-123');
        System.assertEquals(true, res.ok);
        System.assertNotEquals(null, res.astJson);
        System.assertEquals('test-id-123', res.requestId);
    }

    @isTest
    static void testMermaidHttpClientMissingSvg() {
        Test.setMock(HttpCalloutMock.class, new MermaidOkNoSvgMock());
        String mockMermaid = 'graph TD\n    A-->B';
        MermaidHttpClient.Result res = MermaidHttpClient.callWorker(mockMermaid, 'svg', 'test-id-123');
        System.assertEquals(false, res.ok);
        System.assertNotEquals(null, res.errorMessage);
    }

    @isTest
    static void testMermaidHttpClientMissingAst() {
        Test.setMock(HttpCalloutMock.class, new MermaidOkNoSvgMock());
        String mockMermaid = 'graph TD\n    A-->B';
        MermaidHttpClient.Result res = MermaidHttpClient.callWorker(mockMermaid, 'json', 'test-id-123');
        System.assertEquals(false, res.ok);
        System.assertNotEquals(null, res.errorMessage);
    }

    @isTest
    static void testMermaidHttpClientOkFalse() {
        Test.setMock(HttpCalloutMock.class, new MermaidOkFalseMock());
        String mockMermaid = 'graph TD\n    A-->B';
        MermaidHttpClient.Result res = MermaidHttpClient.callWorker(mockMermaid, 'svg', 'test-id-123');
        System.assertEquals(false, res.ok);
        System.assertNotEquals(null, res.errorMessage);
    }

    @isTest
    static void testMermaidSecretsGetKey() {
        System.assertEquals(null, MermaidSecrets.getKey());
    }
    
    // Mock callout class for successful responses
    private class MermaidTestCalloutMock implements HttpCalloutMock {
        public HttpResponse respond(HttpRequest request) {
            HttpResponse response = new HttpResponse();
            response.setStatusCode(200);
            response.setHeader('Content-Type', 'application/json');
            response.setBody('{"ok":true,"svg":"<svg>test</svg>","ast":{"nodes":[],"edges":[]},"id":"test-id-123"}');
            return response;
        }
    }
    
    // Mock callout class for error responses
    private class MermaidErrorCalloutMock implements HttpCalloutMock {
        public HttpResponse respond(HttpRequest request) {
            HttpResponse response = new HttpResponse();
            response.setStatusCode(500);
            response.setHeader('Content-Type', 'application/json');
            response.setBody('{"ok":false,"error":"Internal Server Error"}');
            return response;
        }
    }

    private class MermaidOkNoSvgMock implements HttpCalloutMock {
        public HttpResponse respond(HttpRequest request) {
            HttpResponse response = new HttpResponse();
            response.setStatusCode(200);
            response.setHeader('Content-Type', 'application/json');
            response.setBody('{"ok":true}');
            return response;
        }
    }

    private class MermaidOkFalseMock implements HttpCalloutMock {
        public HttpResponse respond(HttpRequest request) {
            HttpResponse response = new HttpResponse();
            response.setStatusCode(200);
            response.setHeader('Content-Type', 'application/json');
            response.setBody('{"ok":false,"error":"Bad request"}');
            return response;
        }
    }
}
