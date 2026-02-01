# HUD Embed Pattern (Google Sites)

## Goal
Embed in-meeting HUD inside ops.deafingov.org as an iframe, while keeping policy + receipts in the journal/runtime.

## Embed URL
https://hud.deafingov.org/meetings/{meetingKey}

## Modes
- viewer: read-only tail + snapshot
- operator: can run commands (advance agenda, open/close vote)
- approver: can approve/send comms and publish minutes

## Security
- Restrict HUD access to internal identity (Workspace groups) or an IdP gateway.
- Never put Salesforce tokens in browser JS.
- Commands require strong identity and emit receipts.

## Allowed origins
- ops.deafingov.org
- hud.deafingov.org
