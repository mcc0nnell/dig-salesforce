# Orphaned Flow Artifacts

These flows are not present in the org and should be removed locally.

Org check (expect no match):
  sf org list metadata --metadata-type Flow --target-org deafingov | rg -n "<FlowApiName>"
  # no match for DIG_Membership_Screened_Onboarding

Suggested removal:
  git rm dig-src/main/default/flows/DIG_Membership_Screened_Onboarding.flow-meta.xml

Reference cleanup search:
  rg -n "<FlowApiName>" manifest docs scripts dig-src

Retrieve real flows:
  sf project retrieve start --metadata "Flow:DIG_Membership_OnCreate" --target-org deafingov
  sf project retrieve start --metadata "Flow:DIG_Membership_OnUpdate_Status" --target-org deafingov

Re-validate:
  make dig-validate
