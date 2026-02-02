# DIG Emissions Spine — Spec + Implementation Details

**Org alias:** `deafingov`  
**Date:** 2026-02-01  
**Goal:** Implement an append-only, hash-chained, deterministic event journal for tracking important system events in a tamper-evident manner.

---

## 1) Overview

The DIG Emissions Spine provides a deterministic, append-only event journal that tracks important system events with cryptographic integrity. This enables:
- Immutable audit trails for critical operations
- Deterministic event replay capabilities
- Tamper-evident logging of system activities
- Integration with existing membership join flows

---

## 2) Core Components

### 2.1 `Emission__c` (Custom Object)
The primary event journal object that stores serialized events with cryptographic integrity.

Fields:
- `Stream__c` *(Text 18)* - Reference to the emission stream
- `Sequence__c` *(Number 18,2)* - Sequence number within the stream
- `Type__c` *(Text 40)* - Event type (e.g., "membership.joined")
- `OccurredAt__c` *(DateTime)* - When the event occurred
- `Actor__c` *(Text 18)* - User ID of actor who triggered the event
- `Contact__c` *(Text 18)* - Contact ID related to the event
- `Membership_Term__c` *(Text 18)* - Membership term ID (if applicable)
- `Receipt__c` *(Text 18)* - Receipt ID (if applicable)
- `Payload__c` *(Long Text Area)* - Raw JSON payload of the event
- `PrevHash__c` *(Text 64)* - SHA-256 hash of previous event in stream
- `Hash__c` *(Text 64)* - SHA-256 hash of current event
- `Canonical__c` *(Long Text Area)* - Canonical JSON representation for deterministic hashing
- `Stream_Seq__c` *(Text 100)* - Composite key: Stream__c + Sequence__c
- `Idempotency_Key__c` *(Text 100)* - Key for ensuring idempotent operations
- `Stream_Idem__c` *(Text 100)* - Composite key: Stream__c + Idempotency_Key__c

### 2.2 `Emission_Stream__c` (Custom Object)
Manages concurrency control and sequence numbers for emission streams.

Fields:
- `Next_Sequence__c` *(Number 18,2)* - Next available sequence number
- `Last_Hash__c` *(Text 64)* - SHA-256 hash of the last event in the stream

### 2.3 `DIG_Emissions_Perms` (Permission Set)
Provides appropriate field-level permissions for accessing emission data.

---

## 3) Implementation Details

### 3.1 Canonical JSON Serialization
The `CanonicalJson` class implements deterministic JSON serialization with:
- Keys sorted lexicographically
- Consistent formatting (no extra whitespace)
- Stable serialization for cryptographic hashing

### 3.2 Emission Service
The `EmissionService` class provides core functionality:
- `append()` - Append a new event to a stream
- `appendOnce()` - Append an event only if not already present (idempotent)
- Concurrency control using FOR UPDATE locks
- Deterministic hashing with SHA-256

### 3.3 Flow Integration
The `EmissionAppendAction` class provides an invocable method for integration with Salesforce Flows and Agentforce:

```apex
@InvocableMethod(label='Append Emission' description='Append an emission to the journal')
public static void appendEmission(List<Request> requests) {
    // Implementation details
}
```

---

## 4) Integration with Membership Join

The `DigMembershipService` class has been updated to emit membership events using the new emission system:

```apex
// When a membership is joined, emit an event
EmissionService.appendOnce(
    'membership.joined',
    new Map<String, Object>{
        'contactId' => contact.Id,
        'membershipTermId' => membershipTerm.Id,
        'occurredAt' => DateTime.now()
    },
    'membership-' + contact.Id
);
```

---

## 5) Security & Permissions

### 5.1 Field-Level Security
The `DIG_Emissions_Perms` permission set grants appropriate access to emission data fields.

### 5.2 Concurrency Control
Streams use FOR UPDATE locks to ensure thread-safe sequence number allocation.

### 5.3 Idempotency
The `Stream_Idem__c` field prevents duplicate events from being recorded.

---

## 6) Deployment & Testing

### 6.1 Deployment Manifests
Updated manifests include:
- `membership-mvp-package.xml`
- `slice-apex-comms-core.xml`
- `slice-objects.xml`
- `slice-permissionsets.xml`
- `mermaid-intake-package.xml`
- `slice-apex.xml`
- `slice-apex-classes.xml`

### 6.2 Test Coverage
Comprehensive unit tests cover:
- Canonical JSON serialization
- Emission service append/appendOnce operations
- Concurrency control
- Idempotency handling
- Hash calculation

---

## 7) CLI snippets (org alias: deafingov)

Deploy:
```bash
sf project deploy start --target-org deafingov --manifest manifest/membership-mvp-package.xml
```

Run tests:
```bash
sf apex run test --target-org deafingov --test-level RunLocalTests --result-format human
```

---

## 8) Future Enhancements

- Integration with external audit systems
- Event replay capabilities
- Advanced cryptographic verification features
- Stream-based analytics and reporting

---

**End of spec.**
