# Email/Comms Runbook (DIG)

## Two-lane architecture

- Lane A (Transactional, MVP): Salesforce Flow + Lightning Email Templates for renewal/confirmation/notice emails.
- Lane B (Broadcast/Newsletter, scale path): Salesforce Foundations marketing (early stage) or external ESP (MailerSend).

Contacts are the membership spine; Membership records drive the reminder logic.

## Do Today checklist (UI setup)

1) Setup -> Deliverability
   - Access Level: All Email
2) Setup -> Org-Wide Email Addresses (OWEA)
   - Add + verify `membership@deafingov.org` (minimum)
   - Optional: `ops@deafingov.org`
   - Set default no-reply (Org-Wide Email Address for "No-Reply")
3) Setup -> DKIM Keys
   - Generate a DKIM key for the sending domain (or subdomain)
   - Publish the provided CNAME record(s) in DNS
4) SPF/DMARC (domain-level DNS)
   - SPF: include Salesforce/MailerSend as needed (one SPF record total)
   - DMARC: start with `p=none` and move to `quarantine` or `reject` after monitoring

## Transactional templates (Lightning Email Templates)

Create in folder `DIG Email`:
- Membership Renewal - Next 7 Days
- Membership Renewal - Next 30 Days
- Membership Lapsed

## Flow pattern

Use a **Scheduled Flow** that runs daily and checks renewal windows.
- Scheduled beats record-triggered for time-based reminders because it avoids per-record timing drift and keeps reminders deterministic.
- The flow should:
  - Query Memberships due in 7/30 days (or lapsed).
  - Check last-sent throttling fields to avoid daily repeats.
  - Send Email (template + OWEA) and update last-sent fields.

## Anti-spam throttling design

Add last-sent date fields and check them before sending:
- `Last_Renewal_Reminder_7D_Sent__c` (Date)
- `Last_Renewal_Reminder_30D_Sent__c` (Date)

Preferred location: `Membership__c` (since Membership drives renewal timing).
If your org stores membership directly on Contact, move these fields to Contact and update the flow + manifest accordingly.

## Broadcast options

Option 1: **Salesforce Foundations marketing** (early stage)
- Keep lists small, segment by Membership Status and opt-in.

Option 2: **MailerSend** (recommended at scale)
- Clean separation of broadcast vs transactional traffic.
- Better deliverability controls and list hygiene.

## DirectAdmin + MailerSend power moves

- Subdomain separation:
  - Bulk/newsletter: `news.deafingov.org`
  - Transactional: `ops.deafingov.org`
- Inbound routes (optional future enhancement):
  - `ops@deafingov.org` -> webhook -> create Case

## Version control guidance

- Track: Lightning Email Templates, Flows/FlowDefinitions, throttling fields, and any required permission sets.
- Avoid profiles/layouts unless explicitly required; document UI-only config here instead.

## Helper script

Use the mega script on macOS/Linux:
- `scripts/email-comms.sh retrieve`
- `scripts/email-comms.sh deploy`
- `scripts/email-comms.sh validate`

## Windows note for helper script

The `scripts/email-comms.sh` helper is executable for macOS/Linux. On Windows, run it with:
- Git Bash, or
- WSL, or
- run the underlying `sf ...` commands directly.
