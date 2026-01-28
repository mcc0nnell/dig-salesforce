# DIG Control Room Dashboard (Spec + Build Runbook)

**Purpose:** One screen that answers, in under 10 seconds:

1) **What’s blocked?**  
2) **What’s at risk?**  
3) **What needs a decision?**

This dashboard is deliberately *cross-app*: DIG Ops + Summit + Governance (and later Comms Engine).

---

## 1) Dashboard name + placement

- Dashboard title: **DIG Control Room**
- Folder: **DIG Ops Admin** (or a dedicated folder: **DIG Control Room**)

Home page card: pin this dashboard to the **DIG Ops** app home.

---

## 2) KPI tiles (top row)

### A) Open Work (Cases)
- Metric: Count of open Cases
- Filter: `IsClosed = false`
- Drilldown: “Open Cases – by Status” report

### B) At Risk (SLA / Overdue)
Pick one depending on what you have today:

**Option 1 (now):** Case overdue by due date / age  
**Option 2 (Comms Engine):** `DIG_SLA_Status__c IN ('AtRisk','Breached')`

### C) Upcoming Summit Events (Next 14 Days)
- Metric: Count of Summit Instances starting in next 14 days
- Filter: `Start >= TODAY` and `Start < TODAY+14`

### D) Summit Accessibility At Risk
- Metric: Count of Summit Instances with accessibility risk flag
- Filter idea: `Accessibility_Status__c = 'AtRisk'` OR missing evidence

### E) Motions Pending Decision
- Metric: Count of Motions where `Status__c = 'Open'` OR `Result_Status__c != 'Certified'`

---

## 3) Operational panels (middle rows)

### Panel 1: Work Intake / Ops
**Chart:** Open Cases by Status  
**Chart:** Open Cases by Category (if you have a category field)  
**Table:** “Top 10 Oldest Open Cases”

### Panel 2: Summit Ops
**Chart:** Confirmed vs Capacity (aggregate / or count of events over 80% capacity)  
**Chart:** Events by Ops_Status__c (Draft/Scheduled/Open/Completed)  
**Table:** “Next 10 Events” with Start, Location, Ops_Status, Accessibility_Status, Confirmed_Count/Capacity

### Panel 3: Governance
**Chart:** Motions by Status (Draft/Open/Closed)  
**Table:** Open motions with Close_At, sponsor, and current vote tally (if available)  
**Tile:** “Certifications due” (closed but not certified)

---

## 4) Bottom row (signals + narrative)

### A) “Change Log” feed
A report or list of most recent changes:
- new members
- new sponsorships
- closed cases
- newly certified motions

### B) “This week in DIG” (optional)
If you’re using Agentforce drafting: a short narrative panel that can be generated weekly from KPIs.

---

## 5) Build approach: fastest path in Salesforce

1) Build the reports in the UI (Reports tab)  
2) Assemble dashboard in Lightning Dashboard Builder  
3) Put it on DIG Ops app home  
4) **Then** pull metadata with CLI to source control

Why: report/dashboard XML ordering issues are common if you try to hand-author first.

---

## 6) Report names (recommended)

Create a folder: **DIG Control Room**

Reports (suggested DeveloperName):
- `ControlRoom_Open_Cases_By_Status`
- `ControlRoom_Open_Cases_Oldest_10`
- `ControlRoom_AtRisk_Cases`
- `ControlRoom_Upcoming_Summit_14d`
- `ControlRoom_Summit_Accessibility_AtRisk`
- `ControlRoom_Motions_Pending`
- `ControlRoom_Change_Log_Recent`

---

## 7) Governance + Summit prerequisites checklist

Summit fields (or equivalents):
- Ops_Status
- Capacity
- Confirmed_Count
- Accessibility_Status

Governance fields:
- Motion.Status
- Motion.Result_Status
- Motion.Close_At

Comms Engine (later):
- Case.DIG_SLA_Status__c

---

## 8) “Control Room” success criteria

- 1 page
- no scrolling if possible
- every tile has a drilldown
- numbers match what humans believe on the ground
- can be screenshot and used in status meetings

---

## 9) Next step (lock metadata precisely)

Once you’ve built the dashboard + reports in the UI, run:
```bash
sf project retrieve start -o deafingov -m Dashboard:DIG_Control_Room/DIG_Control_Room
sf project retrieve start -o deafingov -m Report:DIG_Control_Room/ControlRoom_Open_Cases_By_Status
```

Then commit the retrieved metadata and this slice becomes fully deployable.
