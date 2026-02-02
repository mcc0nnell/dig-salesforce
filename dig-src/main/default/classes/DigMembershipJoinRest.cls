@RestResource(urlMapping='/dig/membership/join')
global with sharing class DigMembershipJoinRest {
    @TestVisible
    private static Boolean forceException = false;

    @HttpPost
    global static DigMembershipService.JoinResult postJoin() {
        RestResponse response = RestContext.response;
        try {
            if (forceException) {
                Object fail = null;
                fail.toString();
            }
            DigMembershipService.JoinRequest request = parseRequest();
            DigMembershipService.JoinResult result = DigMembershipService.join(request);
            response.statusCode = 200;
            return result;
        } catch (DigMembershipService.ValidationException ex) {
            response.statusCode = 400;
            return errorResult(ex.getMessage());
        } catch (Exception ex) {
            System.debug(LoggingLevel.ERROR, 'DigMembershipJoinRest error: ' + ex.getMessage());
            response.statusCode = 500;
            return errorResult('Internal error');
        }
    }

    private static DigMembershipService.JoinRequest parseRequest() {
        RestRequest request = RestContext.request;
        if (request == null || request.requestBody == null) {
            return null;
        }
        String body = request.requestBody.toString();
        if (String.isBlank(body)) {
            return null;
        }
        return (DigMembershipService.JoinRequest) JSON.deserialize(body, DigMembershipService.JoinRequest.class);
    }

    private static DigMembershipService.JoinResult errorResult(String message) {
        DigMembershipService.JoinResult result = new DigMembershipService.JoinResult();
        result.ok = false;
        result.message = message;
        return result;
    }
}
