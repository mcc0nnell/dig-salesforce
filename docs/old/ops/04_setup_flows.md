# DIG Ops Admin - Flow Setup

## Overview
Build automation scaffolding using Flow (UI) for:
- Due-date reminders at T-24h to Owner
- Escalation at +48h overdue to Ops Lead
- Waiting-on-requester reminders at +3 days
- Auto-close at +14 days waiting (with reopen instructions)
- Record-triggered flow: on Closed → create Ops Change Log entry

If you want these flows in source control later, use the API names listed in `manifest/dig_ops_flows.xml`.

## Pre-work
1) Create a Public Group or User for **DIG Ops Lead** (used for escalations).
2) Confirm the Case fields exist:
   - Due_Date__c, Ops_Status__c, Ops_Priority__c, Next_Action__c, Requester_Email__c
3) Confirm Ops Change Log object exists (Ops_Change_Log__c).

## Scheduled Flow 1: Due-Date Reminder (T-24h)
1) Setup → Flows → New Flow → Scheduled-Triggered Flow
2) Start:
   - Run: Daily
   - Start Time: 08:00 (local)
   - API Name: `DIG_Ops_Due_Date_Reminder`
3) Object: Case
4) Condition Requirements:
   - `Due_Date__c = TODAY() + 1`
   - `IsClosed = False`
5) Action: Send Email (to Owner)
   - Subject: "Ops Ticket Due Tomorrow"
   - Body: include Case Number, Subject, Due Date, Next Action
6) Activate as **DIG Ops - Due Date Reminder**

## Scheduled Flow 2: Overdue Escalation (+48h)
1) New Scheduled-Triggered Flow
2) Start: Daily at 08:00
   - API Name: `DIG_Ops_Overdue_Escalation`
3) Object: Case
4) Condition Requirements:
   - `Due_Date__c <= TODAY() - 2`
   - `IsClosed = False`
5) Action: Send Email to **DIG Ops Lead**
   - Include Owner, Case Number, Subject, Due Date, Ops Status
6) Activate as **DIG Ops - Overdue Escalation**

## Scheduled Flow 3: Waiting on Requester Reminder (+3 days)
1) New Scheduled-Triggered Flow
2) Start: Daily at 08:00
   - API Name: `DIG_Ops_Waiting_Reminder`
3) Object: Case
4) Condition Requirements:
   - `Ops_Status__c = "Waiting on Requester"`
   - `LastModifiedDate <= TODAY() - 3`
5) Action: Send Email to Requester (Requester_Email__c)
   - Include reopen instructions and how to reply
6) Activate as **DIG Ops - Waiting Reminder**

## Scheduled Flow 4: Auto-Close Waiting (+14 days)
1) New Scheduled-Triggered Flow
2) Start: Daily at 08:00
   - API Name: `DIG_Ops_Auto_Close_Waiting`
3) Object: Case
4) Condition Requirements:
   - `Ops_Status__c = "Waiting on Requester"`
   - `LastModifiedDate <= TODAY() - 14`
5) Update Records:
   - Set `Ops_Status__c = "Closed"`
   - Optionally set `Status = "Closed"` (if using standard Status)
6) Email Requester:
   - Note the ticket is closed due to inactivity and how to reply to reopen.
7) Activate as **DIG Ops - Auto Close Waiting**

## Record-Triggered Flow: Closed → Ops Change Log
1) New Flow → Record-Triggered Flow
2) Object: Case
   - API Name: `DIG_Ops_Closed_to_Change_Log`
3) Trigger: When record is updated
4) Entry Criteria:
   - `ISCHANGED(Ops_Status__c) = TRUE`
   - `Ops_Status__c = "Closed"`
5) Create Records (Ops_Change_Log__c):
   - Date__c = TODAY()
   - Summary__c = Case.Subject
   - Decision__c = Case.Description
   - Approver__c = Case.OwnerId (or set later)
   - Tickets__c = Case.Id
6) Activate as **DIG Ops - Closed to Change Log**

## Notes
- If you keep standard Case Status unchanged, treat Ops_Status__c as the source of truth in flows.
- Consider adding a validation rule so Due Date + Next Action are required on save.
