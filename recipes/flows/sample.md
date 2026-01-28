---
recipe: flow
name: Summit_Sample_Recipe
apiVersion: 65.0
packageDir: dig-src
slice:
  alias: summit-sample
  withDeps: true

# Screen definitions for [Screen: <Key>] nodes in Mermaid.
# Convention: recipe uses form.<name> but compiler flattens to Flow vars form_<name>.
screens:
  Overview:
    label: "Summit overview"
    nextLabel: "Continue"
    components:
      - type: displayText
        text: "Summit sample flow with LWC + Apex."
      - type: lwc
        component: digMembershipPanel
        label: "Membership panel"
---

```mermaid
flowchart TD
  Start([Start]) --> S1[Screen: Overview]
  S1 --> A[RecordCreate: Summit__c]
  A --> X[Apex: DigOps_MembershipRules.apply]
  X --> D{{Decision: "Proceed?"}}
  D|Yes| --> B[RecordUpdate: Summit__c]
  D|No| --> End([End])
  B --> End([End])
```

## Capabilities
### Flow actions
- Record create: `Summit__c`
- Screen: `Overview` (includes LWC `digMembershipPanel`)
- Apex action: `DigOps_MembershipRules.apply`
- Decision: `Proceed?`
- Record update: `Summit__c`

### Data writes
- Creates `Summit__c`
- Updates `Summit__c` (only on the Yes branch)

### External calls
- None in this recipe (Apex action is a local call; any callouts would be inside Apex if implemented)

### Dependencies
- Apex class: `DigOps_MembershipRules` with method `apply`
- Object: `Summit__c` (create/update permissions required)
- LWC bundle: `digMembershipPanel`

### Security / permissions
- Flow runtime user needs create/update access on `Summit__c`
- Apex action requires execute access to `DigOps_MembershipRules`
- LWC requires access to the `digMembershipPanel` component (and any Apex it calls)

### Outputs
- If decision is Yes: updated `Summit__c` record
- If decision is No: no update beyond the initial create
