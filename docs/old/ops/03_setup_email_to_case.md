# DIG Ops Admin - Email-to-Case Setup

## Goal
Route inbound ops requests to the DIG Ops queues via Email-to-Case.

## UI steps
1) Setup → Email-to-Case
   - Enable Email-to-Case.
2) Setup → Email-to-Case → Routing Addresses
   - New Routing Address
   - Email address: `ops@<your-domain>` (or DIG-approved alias)
   - Queue: **DIG Ops - Triage** (or your preferred default queue)
   - Save
3) Setup → Organization-Wide Addresses
   - Add and verify a shared ops address (e.g., `ops@<your-domain>`).
4) (Optional) Email Templates
   - Create an auto-response template for requester confirmation.
   - Create an internal notification template for ops.
5) Enable Auto-Response Rules (optional)
   - Use Case Auto-Response Rules to send confirmation to Requester Email.

## Test plan
1) Send a test email to the routing address.
2) Confirm a Case is created with:
   - Owner = DIG Ops - Triage (or selected queue)
   - Subject + Description populated from the email
3) Update Category and verify assignment rules move it to the correct queue.
