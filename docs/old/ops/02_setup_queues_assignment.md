# DIG Ops Admin - Queues + Assignment Rules

## Deploy queues
1) Deploy queue metadata:
   - `sf project deploy start --target-org deafingov --manifest manifest/dig_ops_queues.xml`

## Add queue members (UI)
1) Setup → Queues
2) For each queue, add DIG Ops users or a public group:
   - DIG Ops - Membership
   - DIG Ops - Events
   - DIG Ops - Comms
   - DIG Ops - Fundraising
   - DIG Ops - Governance
   - DIG Ops - IT
   - DIG Ops - Triage
3) Optional: set Queue Email to a shared ops inbox.

## Assignment rules (UI)
1) Setup → Case Assignment Rules
2) Create a new rule: **DIG Ops Assignment** (set as active).
3) Add rule entries in this order (top = highest priority):
   - If `Category__c = Membership` → Queue: DIG Ops - Membership
   - If `Category__c = Events` → Queue: DIG Ops - Events
   - If `Category__c = Comms` → Queue: DIG Ops - Comms
   - If `Category__c = Fundraising` → Queue: DIG Ops - Fundraising
   - If `Category__c = Governance` → Queue: DIG Ops - Governance
   - If `Category__c = IT` → Queue: DIG Ops - IT
   - Else (Category is blank) → Queue: DIG Ops - Triage
4) Save and activate the assignment rule.

## Validation
- Create a Case with each Category value and confirm Owner is assigned to the correct queue.
