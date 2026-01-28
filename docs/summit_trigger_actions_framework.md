# Summit Ops Refactor: Trigger Actions Framework (Apex)

**Goal:** Refactor Summit ops automation to an **ordered, bypassable** “actions” model so you can:
- control execution order explicitly
- disable/bypass automation in migrations/tests
- keep triggers thin and logic modular
- mix Apex + Flow safely later

This scaffold is inspired by the **Salesforce Trigger Actions Framework** concept (partitioning record-triggered logic into ordered actions).  
You can implement this fully in Apex now, then optionally add Flow actions later.

---

## 1) Concept

Instead of writing triggers that become a monolith, we do:

- One thin trigger per object:
  - `SummitInstance.trigger`
  - `SummitRegistration.trigger`

- Each trigger calls a dispatcher:
  - `TA_Dispatcher.run(...)`

- Dispatcher runs ordered actions:
  - `Instance.NormalizeStatus`
  - `Instance.EnsureOpsChecklist`
  - `Registration.ApplyCapacityRules`
  - `Registration.StampCommsFlags`
  - etc.

Actions are:
- small, composable classes
- bulk-safe (operate on lists/maps)
- easy to test independently

---

## 2) Files included in this ZIP

```
force-app/main/default/
  classes/
    TA_Action.cls
    TA_Context.cls
    TA_Dispatcher.cls
    TA_Registry.cls
    TA_Bypass.cls

    SummitSchema.cls
    SummitSelectors.cls
    SummitLifecycleAction_NormalizeStatus.cls
    SummitRegistrationAction_Capacity.cls

    Summit_ActionTests.cls
  triggers/
    SummitEventInstanceTrigger.trigger
    SummitRegistrationTrigger.trigger
manifest/
  summit-actions.xml
docs/
  summit-trigger-actions.md
```

---

## 3) How ordering works

`TA_Registry` defines the ordered action list per object + context:

- Object: `summit__Instance__c`
  - `before update`: NormalizeStatus
- Object: `summit__Registration__c`
  - `before insert`: ApplyCapacityRules

Add actions by appending to the list.

---

## 4) Bypass controls (migration / tests)

You can bypass in code:

```apex
TA_Bypass.enable('summit__Registration__c');
```

Or bypass a specific action:

```apex
TA_Bypass.enableAction('SummitRegistrationAction_Capacity');
```

This is very useful when you:
- seed data
- run backfills
- deploy changes that would otherwise re-trigger logic

---

## 5) Next step for you (wiring Summit API names)

Update `SummitSchema.cls` to match your installed Summit package fields.
The scaffold assumes (likely) names:
- `summit__Instance__c`
- `summit__Registration__c`
…but your org may differ.

After mapping, you can start turning on more actions.

---

## 6) Deploy / validate

```bash
sf project deploy validate -o deafingov -p force-app
sf project deploy start    -o deafingov -p force-app
```

---

## 7) Recommended action roadmap

Instance actions (in order):
1. Normalize status (deterministic)
2. Compute landing URL
3. Ensure ops checklist tasks
4. Compute risk flags (accessibility/capacity/logistics)

Registration actions:
1. Capacity confirm/waitlist
2. Stamp reminder flags
3. Create payment follow-ups (if applicable)

This keeps logic small, ordered, and observable.
