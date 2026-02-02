# Flow Resave Required

At least one flow must be re-saved in Flow Builder to resolve schema/order drift.

Steps:
1) Setup → Flows
2) Open the flow
3) Edit → Save → (Activate if needed)
4) Retrieve updated metadata:
   sf project retrieve start --metadata "Flow:<FlowApiName>"
5) Re-run:
   make dig-validate

Flows to resave:
- DIG_Membership_Screened_Onboarding
