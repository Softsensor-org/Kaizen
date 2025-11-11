# Mass-Transit / Monthly-Pass Requirements Document

**Status:** DRAFT - Requires Stakeholder Review
**Date:** 2025-01-11
**Priority:** MEDIUM
**Estimated Effort:** 8-12 hours (once requirements confirmed)

---

## 1. Executive Summary

This document outlines the requirements for implementing mass-transit and monthly-pass logic for NEMT claims. This functionality is currently **NOT IMPLEMENTED** and requires business rule definition from stakeholders before implementation can begin.

### Key Questions Requiring Stakeholder Input

1. **What constitutes a "monthly pass" transaction?**
2. **How are zero-dollar follow-up legs identified and processed?**
3. **What PYMS payment status codes are used for monthly passes?**
4. **How does CAS adjustment coordination work for monthly passes?**
5. **What are the 2420D payee selection rules for mass transit?**

---

## 2. Background

### Current State

**HCPCS Code A0110:**
- **Description:** "Non-emergency transportation and bus, intra- or inter-state carrier"
- **Status:** Code exists in `codes.py:44`
- **Usage:** Unknown - no special handling logic

**What's Missing:**
- No business rules for A0110 handling
- No zero-dollar leg processing
- No monthly pass detection
- No special payment coordination
- No mass-transit specific validation

### Industry Context

Mass-transit/monthly-pass scenarios typically involve:
- **Initial Payment:** Member or provider purchases monthly bus pass ($50-$100)
- **Subsequent Trips:** Multiple trips during the month using the same pass
- **Billing Pattern:** First trip billed at full amount, subsequent trips at $0.00
- **Payment Status:** PYMS codes reflect "prepaid" or "included in pass"
- **Adjudication:** CAS adjustments show "paid by other means"

---

## 3. Requirements (PENDING STAKEHOLDER REVIEW)

### 3.1 Monthly Pass Identification

**Question:** How do we identify that a claim involves a monthly pass?

**Possible Approaches:**
1. **HCPCS Code:** A0110 automatically indicates monthly pass
2. **Modifier:** Special modifier indicates monthly pass usage
3. **Service Amount:** $0.00 charge indicates subsequent trip
4. **Authorization:** Auth number contains monthly pass indicator
5. **K3 Segment:** Custom K3 segment identifies pass type/number

**Stakeholder Decision Needed:**
- [ ] Which approach is correct for UHC Kentucky contract?
- [ ] Can multiple approaches be combined?
- [ ] Are there different types of passes (weekly, monthly, annual)?

### 3.2 Zero-Dollar Follow-Up Leg Rules

**Question:** How should zero-dollar follow-up legs be processed?

**Scenarios:**

#### Scenario A: First Trip of Month
```
Trip 1 (Date: 2025-01-05):
- Service: A0110 (bus pass)
- Charge: $75.00
- Units: 1
- PYMS: PYMS-P (Paid)
- Patient: Pays upfront or copay
```

#### Scenario B: Subsequent Trip Same Month
```
Trip 2 (Date: 2025-01-10):
- Service: A0110 (bus pass)
- Charge: $0.00 or $75.00?
- Units: 1
- PYMS: PYMS-P or PYMS-I (Included)?
- CAS: What adjustment code?
```

**Stakeholder Decision Needed:**
- [ ] Is subsequent trip charge $0.00 or same as first trip?
- [ ] What PYMS code is used for subsequent trips?
- [ ] What CAS adjustment codes apply?
- [ ] How is "same month" defined (calendar month, 30-day rolling, contract-specific)?
- [ ] Is pass number/ID tracked anywhere?

### 3.3 PYMS/CAS Coordination

**Question:** How do payment status (PYMS) and adjustments (CAS) coordinate for monthly passes?

**Current PYMS Codes:**
```python
# From codes.py (custom UHC format)
PAYMENT_STATUS_CODES = {
    "P": "Paid",
    "D": "Denied",
}
```

**Possible PYMS Codes for Monthly Pass:**
- **PYMS-P**: Paid (for initial pass purchase)
- **PYMS-I**: Included in pass (for subsequent trips)
- **PYMS-X**: Prepaid (alternate approach)
- **PYMS-N**: No charge (zero-dollar legs)

**CAS Adjustment Codes:**
Common CAS codes for prepaid/pass scenarios:
- **CO-45**: Charge exceeds fee schedule (if claiming full amount each time)
- **OA-94**: Processed in accordance with contract terms (monthly pass terms)
- **PR-1**: Deductible amount (if pass is patient responsibility)
- **CO-24**: Charges are covered under capitation agreement (pass agreement)

**Stakeholder Decision Needed:**
- [ ] Which PYMS codes apply to monthly pass scenarios?
- [ ] Which CAS adjustment codes should be used?
- [ ] Should we expand PAYMENT_STATUS_CODES dictionary?
- [ ] How does SVD05 (paid units) differ from SV104 (billed units) for passes?

### 3.4 Payee Selection (2420D Loop)

**Question:** Who is the payee for monthly pass reimbursement?

**Possible Payee Scenarios:**

#### Scenario 1: Provider Payee (Standard)
```
2420D Loop (Service Level):
- NM1*DQ*2*Mass Transit Authority*****XX*9876543210~
  (Payee = Transit authority that issued pass)
```

#### Scenario 2: Member Payee (Reimbursement)
```
2420D Loop (Service Level):
- NM1*DQ*1*Doe*John****MI*MEMBER123~
  (Payee = Member who purchased pass)
```

#### Scenario 3: No Payee (Zero-Dollar)
```
No 2420D loop for subsequent $0.00 trips
```

**Stakeholder Decision Needed:**
- [ ] Who receives reimbursement for monthly pass purchase?
- [ ] Is it always the same entity or does it vary?
- [ ] For zero-dollar legs, should 2420D loop be omitted?
- [ ] What NPI/Tax ID is used for transit authority payee?

### 3.5 Multi-Leg Pass Usage

**Question:** How are multiple legs within a single pass period handled?

**Example: Member uses pass for 10 trips in January**

**Option A: Bill only first trip**
```
Claim 1 (Jan 5): A0110, $75.00, PYMS-P
(Subsequent 9 trips not billed)
```

**Option B: Bill all trips, $0.00 for subsequent**
```
Claim 1 (Jan 5): A0110, $75.00, PYMS-P
Claim 2 (Jan 8): A0110, $0.00, PYMS-I
Claim 3 (Jan 12): A0110, $0.00, PYMS-I
... (10 claims total)
```

**Option C: Bill all trips at full amount, adjust at adjudication**
```
Claim 1 (Jan 5): A0110, $75.00, PYMS-P, no CAS
Claim 2 (Jan 8): A0110, $75.00, PYMS-P, CAS*CO*45*75.00 (covered by pass)
Claim 3 (Jan 12): A0110, $75.00, PYMS-P, CAS*CO*45*75.00
... (10 claims, first paid, rest adjusted)
```

**Stakeholder Decision Needed:**
- [ ] Which billing pattern is correct?
- [ ] Does it vary by contract or payer?
- [ ] How does Kaizen track pass usage across multiple claims?
- [ ] Is there a maximum number of trips per pass?

### 3.6 Authorization Requirements

**Question:** Do monthly pass claims require special authorization handling?

**Possible Requirements:**
- Pass number in auth_number field
- Pass expiration date validation
- Prior authorization for pass purchase
- Pass type (weekly/monthly/annual) documentation

**Stakeholder Decision Needed:**
- [ ] Is prior authorization required for pass purchase?
- [ ] Where is pass number/ID stored in claim?
- [ ] How is pass expiration validated?
- [ ] Are there limits on pass types (e.g., only monthly allowed)?

---

## 4. Technical Implementation Plan (PENDING REQUIREMENTS)

Once stakeholder decisions are made, implementation would include:

### 4.1 Data Model Updates

**Add to Trip/Claim Structure:**
```python
# New fields needed in trip JSON
{
    "monthly_pass": {
        "pass_id": "PASS-2025-01-12345",  # Unique pass identifier
        "pass_type": "monthly",  # weekly, monthly, annual
        "pass_cost": 75.00,  # Initial purchase price
        "purchase_date": "2025-01-05",  # When pass was purchased
        "expiration_date": "2025-02-05",  # Pass expiration
        "is_initial_purchase": true,  # First trip vs subsequent
        "trips_used": 1  # Counter for tracking
    },
    "service": {
        "hcpcs": "A0110",
        "charge": 75.00,  # or 0.00 for subsequent
        # ...
    }
}
```

### 4.2 Agent 1 Validation Updates

**Add Monthly Pass Validation:**
```python
def _validate_monthly_pass(self, trip: Dict):
    """Validate monthly pass data"""
    if trip.get("service", {}).get("hcpcs") == "A0110":
        # Check if monthly_pass structure exists
        # Validate pass dates
        # Validate pass_id format
        # Validate charge amount (0.00 for subsequent, >0 for initial)
        # Validate PYMS code matches pass scenario
```

### 4.3 Agent 3 (UHC) Updates

**Add New Rule Codes:**
- **UHC_015**: Monthly pass authorization required
- **UHC_016**: Pass expiration date validation
- **UHC_017**: Zero-dollar leg PYMS/CAS validation
- **UHC_018**: Payee selection for mass transit
- **UHC_019**: Pass usage counter validation

### 4.4 Agent 5 (Batch) Updates

**Add Monthly Pass Aggregation:**
```python
def _aggregate_monthly_pass_trips(self, trips: List[Dict]):
    """Group trips by monthly pass ID"""
    # Group by pass_id
    # Mark first trip as initial purchase
    # Mark subsequent trips as zero-dollar
    # Validate trip count against pass type limits
    # Aggregate PYMS/CAS appropriately
```

### 4.5 Builder Updates

**Add 2420D Payee Loop for Mass Transit:**
```python
def _build_2420D_payee_loop(self, service: Dict):
    """Build payee loop for monthly pass reimbursement"""
    if service.get("hcpcs") == "A0110":
        # Check monthly_pass.is_initial_purchase
        # Build NM1*DQ for transit authority or member
        # Include payee NPI/Tax ID
```

**Add Zero-Dollar Leg Handling:**
```python
def _build_service_line(self, service: Dict):
    """Build SV1 with zero-dollar support"""
    charge = service.get("charge", 0.0)
    if charge == 0.0 and service.get("monthly_pass"):
        # Ensure PYMS indicates included/prepaid
        # Add appropriate CAS adjustments
```

---

## 5. Testing Requirements

### 5.1 Test Scenarios Needed

**T027: Monthly Pass Initial Purchase**
- Member purchases monthly bus pass
- Service: A0110, Charge: $75.00
- PYMS: PYMS-P (Paid)
- No CAS adjustments
- 2420D payee: Transit authority

**T028: Monthly Pass Subsequent Trip (Zero-Dollar)**
- Member uses existing pass
- Service: A0110, Charge: $0.00
- PYMS: PYMS-I (Included)
- CAS: (depends on requirements)
- 2420D payee: (depends on requirements)

**T029: Monthly Pass Expiration**
- Member attempts to use expired pass
- Validation error or new pass purchase required

**T030: Monthly Pass Multiple Legs**
- Member takes 3 round-trips in one month
- 6 service lines total (or 2 if only billing initial)
- Proper PYMS/CAS for each leg

**T031: Mixed Claims (Pass + Regular Transport)**
- Same member has pass trips and non-pass trips
- Proper separation and billing

### 5.2 Edge Cases to Test

1. **Pass purchased mid-month**
2. **Pass used across month boundary**
3. **Member has multiple active passes** (different types)
4. **Pass refund/cancellation**
5. **Shared family pass** (multiple members)
6. **Out-of-network transit authority**
7. **Emergency transport overriding pass**

---

## 6. Documentation Needs

Once implemented:

1. **User Guide:** "How to Bill Monthly Pass Trips"
2. **API Examples:** JSON structures for pass scenarios
3. **Troubleshooting:** Common pass billing errors
4. **Contract Appendix:** Pass rules by payer/state

---

## 7. Stakeholder Review Checklist

**Before implementation, obtain answers to:**

- [ ] Section 3.1: Monthly pass identification method
- [ ] Section 3.2: Zero-dollar follow-up rules
- [ ] Section 3.3: PYMS/CAS codes to use
- [ ] Section 3.4: Payee selection rules
- [ ] Section 3.5: Multi-leg billing pattern
- [ ] Section 3.6: Authorization requirements
- [ ] Contract-specific variations for UHC Kentucky
- [ ] Sample claims or reference transactions
- [ ] Payer remittance advice examples (835 files)

---

## 8. Risk Assessment

### Implementation Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Unclear business rules | HIGH | Delay implementation until clarified |
| Payer-specific variations | MEDIUM | Design flexible rule engine |
| Pass tracking complexity | MEDIUM | Use robust pass_id system |
| Zero-dollar leg rejection | HIGH | Validate PYMS/CAS requirements |
| Payee NPI validation | MEDIUM | Maintain transit authority registry |

### Contract Compliance Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Incorrect billing pattern | HIGH | Review payer contracts thoroughly |
| Missing authorization | HIGH | Implement pre-auth validation |
| Pass expiration not checked | MEDIUM | Add date validation |
| Payee mismatch | MEDIUM | Verify payee rules per contract |

---

## 9. Success Criteria

Implementation will be considered successful when:

1. ✅ All stakeholder questions answered with documented decisions
2. ✅ Code supports identified billing patterns
3. ✅ All test scenarios (T027-T031) pass
4. ✅ Agent 1/3/5 validate monthly pass rules
5. ✅ Builder generates correct EDI for pass scenarios
6. ✅ Zero-dollar legs processed correctly
7. ✅ PYMS/CAS coordination working
8. ✅ 2420D payee selection correct
9. ✅ Documentation complete
10. ✅ Production-ready (no blockers)

---

## 10. Next Steps

### Immediate Actions (Stakeholder Required)

1. **Schedule requirements gathering session** with:
   - UHC Kentucky contract manager
   - Kaizen operations team
   - Finance/billing team
   - NEMT provider subject matter experts

2. **Review existing documentation:**
   - UHC Kentucky NEMT provider manual
   - Mass-transit billing guidelines
   - Sample monthly pass claims (if available)
   - Payer remittance advice (835 files) showing pass adjudication

3. **Gather reference data:**
   - Transit authority NPIs/Tax IDs
   - Common pass types and pricing
   - Authorization format for passes
   - Pass number/ID assignment rules

### Post-Requirements Actions

4. **Update this document** with stakeholder decisions
5. **Create technical specification** from requirements
6. **Implement data model updates**
7. **Implement validation rules (Agents 1, 3, 5)**
8. **Implement builder logic**
9. **Create test scenarios**
10. **Documentation and training**

---

## 11. Questions for Stakeholder Meeting

### Questions for UHC Kentucky

1. "Do you have a sample 837P claim showing A0110 monthly pass billing?"
2. "What PYMS payment status should be used for subsequent zero-dollar trips?"
3. "Do you require prior authorization for monthly pass purchases?"
4. "Who should be listed as payee (NM1*DQ) for pass reimbursement?"
5. "What CAS adjustment codes do you expect for zero-dollar legs?"

### Questions for Kaizen Operations

1. "How many members currently use monthly passes?"
2. "What percentage of NEMT trips are mass-transit vs vehicle?"
3. "How do we currently track pass purchases and usage?"
4. "What problems have we encountered with pass billing in the past?"
5. "Are there different pass types (weekly, monthly, annual)?"

### Questions for Finance

1. "What is the typical cost of a monthly bus pass?"
2. "Who pays for the pass - member, provider, or payer?"
3. "How are pass refunds handled?"
4. "What is our revenue per monthly pass transaction?"
5. "What is the rejection rate for A0110 claims?"

---

## Appendix A: A0110 Code Details

**HCPCS Code:** A0110
**Description:** Non-emergency transportation and bus, intra- or inter-state carrier
**Category:** Ambulatory Transport
**Typical Charges:** $50 - $150 per month
**Common Payers:** Medicaid, Managed Medicaid (UHC Community)
**Units:** Typically 1 (per pass or per trip, depending on billing pattern)

---

## Appendix B: Example Pass JSON Structure

```json
{
  "dos": "2025-01-05",
  "member": {
    "member_id": "M123456789",
    "first_name": "John",
    "last_name": "Doe"
  },
  "service": {
    "hcpcs": "A0110",
    "modifiers": [],
    "charge": 75.00,
    "units": 1
  },
  "monthly_pass": {
    "pass_id": "PASS-KY-2025-01-12345",
    "pass_type": "monthly",
    "pass_cost": 75.00,
    "purchase_date": "2025-01-05",
    "expiration_date": "2025-02-05",
    "is_initial_purchase": true,
    "trips_used": 1,
    "issuing_authority": {
      "name": "Louisville Metro Transit",
      "npi": "9876543210",
      "tax_id": "61-1234567"
    }
  },
  "claim": {
    "clm_number": "CLM-2025-01-001",
    "auth_number": "AUTH-PASS-2025-01-12345",
    "payment_status": "P",
    "patient_account": "PA-123456"
  }
}
```

---

**Document Status:** DRAFT - Requires Stakeholder Review
**Owner:** Technical Team
**Reviewers Needed:** Contract Management, Operations, Finance
**Target Completion:** TBD (pending stakeholder availability)

---

**Report Generated:** 2025-01-11
**Next Review:** After stakeholder requirements gathering session
