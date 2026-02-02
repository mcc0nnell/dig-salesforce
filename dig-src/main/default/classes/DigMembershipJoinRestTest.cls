@IsTest
public class DigMembershipJoinRestTest {
    private static DigMembershipService.JoinRequest baseRequest() {
        DigMembershipService.JoinRequest request = new DigMembershipService.JoinRequest();
        request.firstName = 'Robert';
        request.lastName = 'McConnell';
        request.email = 'robert@example.com';
        request.phone = '555-1212';
        request.organization = 'DIG';
        request.optInEmail = true;
        request.source = 'web';
        return request;
    }

    @IsTest
    static void testRestSuccess() {
        DigMembershipService.JoinRequest request = baseRequest();
        String body = JSON.serialize(request);

        RestRequest restRequest = new RestRequest();
        restRequest.requestUri = '/services/apexrest/dig/membership/join';
        restRequest.httpMethod = 'POST';
        restRequest.requestBody = Blob.valueOf(body);
        RestContext.request = restRequest;
        RestContext.response = new RestResponse();

        Test.startTest();
        DigMembershipService.JoinResult result = DigMembershipJoinRest.postJoin();
        Test.stopTest();

        System.assertEquals(200, RestContext.response.statusCode, 'Expected success');
        System.assertEquals(true, result.ok, 'REST should return ok');
        System.assertNotEquals(null, result.membershipTermId, 'Expected term id');
        System.assertNotEquals(null, result.receiptId, 'Expected receipt id');
    }

    @IsTest
    static void testRestValidation400() {
        DigMembershipService.JoinRequest request = new DigMembershipService.JoinRequest();
        request.lastName = 'MissingEmail';
        String body = JSON.serialize(request);

        RestRequest restRequest = new RestRequest();
        restRequest.requestUri = '/services/apexrest/dig/membership/join';
        restRequest.httpMethod = 'POST';
        restRequest.requestBody = Blob.valueOf(body);
        RestContext.request = restRequest;
        RestContext.response = new RestResponse();

        Test.startTest();
        DigMembershipService.JoinResult result = DigMembershipJoinRest.postJoin();
        Test.stopTest();

        System.assertEquals(400, RestContext.response.statusCode, 'Expected validation error');
        System.assertEquals(false, result.ok, 'Expected ok=false');
        System.assert(result.message != null && result.message.length() > 0, 'Expected message');
    }

    @IsTest
    static void testRestUnexpected500() {
        DigMembershipService.JoinRequest request = baseRequest();
        String body = JSON.serialize(request);

        RestRequest restRequest = new RestRequest();
        restRequest.requestUri = '/services/apexrest/dig/membership/join';
        restRequest.httpMethod = 'POST';
        restRequest.requestBody = Blob.valueOf(body);
        RestContext.request = restRequest;
        RestContext.response = new RestResponse();

        DigMembershipJoinRest.forceException = true;
        Test.startTest();
        DigMembershipService.JoinResult result = DigMembershipJoinRest.postJoin();
        Test.stopTest();
        DigMembershipJoinRest.forceException = false;

        System.assertEquals(500, RestContext.response.statusCode, 'Expected internal error');
        System.assertEquals(false, result.ok, 'Expected ok=false');
        System.assertEquals('Internal error', result.message, 'Expected internal error message');
    }
}
