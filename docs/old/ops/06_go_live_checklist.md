# DIG Ops Admin - Go Live Checklist

## Metadata deployed
- Case fields deployed (`manifest/dig_ops_case_fields.xml`).
- Case record types deployed (`manifest/dig_ops_case_recordtypes.xml`).
- Ops Change Log object deployed (`manifest/dig_ops_change_log.xml`).
- Queues deployed (`manifest/dig_ops_queues.xml`).
- Reports and dashboard deployed (`manifest/dig_ops_reports.xml`, `manifest/dig_ops_dashboards.xml`).

## UI configured
- Case layout updated with Ops fields + required flags.
- Lightning App "DIG Ops Admin" created and assigned.
- Queues have members and (optional) queue email.
- Case Assignment Rule active for Category routing.
- Email-to-Case enabled and routing address tested.
- Flows created, activated, and tested.

## Policy checks
- Owner, Due Date, and Next Action required on every ticket.
- No work starts without a ticket.
- Ops Change Log entry created for Closed items.

## Smoke tests
1) Create a new Case → confirm record type + fields.
2) Set Category and confirm queue assignment.
3) Set Ops Status to Waiting on Requester → confirm reminder flow path works.
4) Close a Case → confirm Ops Change Log entry created.
5) Open the dashboard → confirm all tiles render.
