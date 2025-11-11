# NEMT 837P Converter - Gap Analysis & Agent Architecture

## Executive Summary

This document outlines critical gaps in the current NEMT 837P converter implementation, architectural recommendations, and proposed validation agents to ensure compliance with UHC Community & State requirements and ANSI X12 005010X222A1 specifications.

---

## Critical Gaps

### 1. CR1/CR109/CR110 Segment Construction **[CRITICAL]**

**Location:** `builder.py:126-127, 135, 173, 179`

**Current Issue:**
- Manually constructs CR1 segment with hardcoded positions and empty string padding
- Reuses CR1 segment tag for what should be CR109/CR110 data
- Line 126-127:
  ```python
  c1 = ["CR1", amb.get("weight_unit","LB"), str(amb.get("patient_weight_lbs","")).replace(".0",""), "", "", amb.get("transport_code",""), amb.get("transport_reason","")]
  ```
- Line 135: Second CR1 with 8 empty elements before description field
- Lines 173 & 179: Uses `w.segment("CR1", ...)` for CR109/CR110 data

**X12 Specification:**
- CR1 = Ambulance Transport Information (base segment)
- CR109 = Not a valid X12 segment - data should be in CR1 or NTE
- CR110 = Not a valid X12 segment - data should be in CR1 or NTE

**Impact:** Claims will be rejected by Availity/UHC for improper segment structure

**Recommendation:**
- Use proper CR1 segment structure per 005010X222A1
- Move CR109/CR110 data to NTE segments with proper qualifiers
- Implement segment builder class with validation

**Priority:** P0 - Must fix before production

---

### 2. Missing Trip Number at Service Line Level **[CRITICAL]**

**Location:** `builder.py:185`

**Current Issue:**
```python
if svc.get("trip_number") is not None:
    w.segment("REF", "LU", str(svc["trip_number"]).zfill(9))
```
- Code expects `trip_number` in service object
- Example JSON only has `claim.ambulance.trip_number`
- No cascade logic from claim to service level

**Impact:** REF*LU Trip Number missing at 2420D level, potential rejection

**Recommendation:**
- Clarify business rule: Does each service line have unique trip number?
- If not, cascade claim-level trip_number to service lines
- Add to JSON schema documentation

**Priority:** P0 - Required for UHC compliance

---

### 3. Loop Hierarchy Ambiguity (2310 vs 2420) **[HIGH]**

**Location:** `builder.py:137-141, 188-193`

**Current Issue:**
- README mentions "2310E/F and 2420G/H for pickup/drop-off"
- Code uses identical NM1*PW and NM1*45 at both claim and service levels
- No differentiation between claim-level (2310) and service-level (2420) pickup/dropoff

**X12 Specification:**
- 2310E/F = Claim-level Ambulance Pick-up/Drop-off locations
- 2420G/H = Service-level Ambulance Pick-up/Drop-off locations

**Current Code:**
```python
# Claim level (should be 2310E/F)
if amb.get("pickup"):
    w.segment("NM1", "PW", "2")  # Using PW qualifier

# Service level (should be 2420G/H)
if svc.get("pickup"):
    w.segment("NM1", "PW", "2")  # Same PW qualifier
```

**Impact:** Loop positioning violations, claim rejections

**Recommendation:**
- Verify correct qualifiers for 2310E (PW?) vs 2420G
- Ensure proper loop hierarchy in segment order
- Add loop markers in code comments

**Priority:** P1 - High risk of rejection

---

### 4. Missing Field Validation **[HIGH]**

**Location:** Throughout `builder.py`

**Current Issues:**
- No validation of required fields (NPI, member_id, claim_number)
- No length validation (NPI must be 10 digits, claim number ≤ 30 chars)
- No code value validation (POS codes, transport codes, modifiers)
- No date format validation (CCYYMMDD)
- Silent failures with empty strings

**Examples of Risk:**
- Invalid NPI: `"123"` → generates invalid segment
- Claim number overflow: 50 char string → truncated silently at line 43
- Invalid date: `"01/07/2026"` → `_fmt_d8()` produces `"01/07/2026"` instead of `"20260107"`

**Impact:** Invalid EDI files, difficult debugging, claim rejections

**Recommendation:**
Implement validation agent with:
- JSON schema validation
- X12-specific field rules
- Code value lookups
- Pre-submission validation report

**Priority:** P1 - Prevents invalid submissions

---

### 5. Hardcoded Payer Configuration **[MEDIUM]**

**Location:** `builder.py:76, 202`

**Current Issue:**
```python
w.segment("NM1", "PR", "2", recv.get("payer_name","UNITED HEALTHCARE"), "", "", "", "",
          "PI", recv.get("payer_id","87726"))
```
- Hardcoded fallback to payer_id "87726"
- Hardcoded payer name "UNITED HEALTHCARE"
- No configuration for multiple payers

**Impact:** Cannot support other payers without code changes

**Recommendation:**
- Create payer configuration system
- Support payer-specific rules (loop requirements, code values)
- Externalize payer mappings

**Priority:** P2 - Important for scalability

---

### 6. Frequency Code Logic Ambiguity **[MEDIUM]**

**Location:** `builder.py:80`

**Current Issue:**
```python
freq = clm.get("frequency_code") or ("8" if clm.get("adjustment_type")=="void" else
      ("7" if clm.get("adjustment_type")=="replacement" else "1"))
```
- Logic references `adjustment_type` field not in example JSON
- No documentation of correction/void workflow
- Unclear precedence: frequency_code vs adjustment_type

**X12 Specification (CLM05-3):**
- 1 = Original claim
- 7 = Replacement of prior claim
- 8 = Void/cancel of prior claim

**Impact:** Incorrect frequency codes on corrections/voids

**Recommendation:**
- Document void/replacement workflow
- Add to JSON schema
- Create correction processing guide

**Priority:** P2 - Required for claim corrections

---

### 7. CR109/CR110 Data Redundancy **[MEDIUM]**

**Location:** `builder.py:157-179`

**Current Issue:**
```python
# NTE segment (lines 157-162)
if svc.get("pickup_loc_code"): nte_parts.append(f"PULOC-{svc['pickup_loc_code']}")
if svc.get("drop_loc_code"): nte_parts.append(f"DOLOC-{svc['drop_loc_code']}")
if svc.get("drop_time"): nte_parts.append(f"DOTIME-{svc['drop_time']}")

# CR109 "segment" (lines 165-173)
if svc.get("trip_type"): cr109.append(f"TRIPTYPE-{svc['trip_type']}")
# ...

# CR110 "segment" (lines 174-179)
if svc.get("drop_loc_code"): cr110.append(f"DOLOC-{svc['drop_loc_code']}")
if svc.get("drop_time"): cr110.append(f"DOTIME-{svc['drop_time']}")
```

**Issue:** DOLOC and DOTIME appear in both NTE and "CR110" segments

**Impact:** Data redundancy, potential conflicts if values differ

**Recommendation:**
- Clarify UHC requirements for which fields go where
- Use single source for each data element
- Document custom K3/NTE/CR format specifications

**Priority:** P2 - Clean up for maintainability

---

### 8. No Test Coverage **[LOW]**

**Current State:**
- No unit tests
- No integration tests
- Single example JSON (`claim_kaizen.json`)

**Missing Test Scenarios:**
- Void claims (frequency 8)
- Replacement claims (frequency 7)
- Claims without adjudication (2430 SVD/CAS)
- Multi-service line claims (already in example)
- Different transport types (wheelchair, ambulette, etc.)
- Edge cases: missing optional fields, minimum required fields
- Invalid input handling

**Impact:** High regression risk, difficult refactoring

**Recommendation:**
- Pytest test suite
- Golden file comparisons
- Mock validation against X12 spec
- CI/CD integration

**Priority:** P3 - Important for long-term maintainability

---

### 9. Missing Documentation **[LOW]**

**Current State:**
- No field mapping reference (JSON → 837P segments)
- No explanation of custom K3/NTE/CR1 encoding formats
- Business mapping XLS exists but not integrated
- README has only basic run instructions

**Needed Documentation:**
- Complete field mapping table
- Code value lookup tables (POS, transport codes, modifiers)
- Scenario-based examples (original, replacement, void)
- UHC-specific requirements documentation
- Integration guide (Availity submission process)

**Impact:** Difficult onboarding, maintenance burden

**Recommendation:**
- Generate mapping docs from code
- Create scenario cookbook
- Document UHC custom requirements

**Priority:** P3 - Improves usability

---

### 10. No Batch Processing Support **[LOW]**

**Current State:**
- `cli.py` only processes single claim JSON
- No batch file support
- No control number management across batches

**Production Requirement:**
- Multiple claims per batch file
- Proper ISA/GS envelope management
- Control number sequencing
- Batch summary reporting

**Impact:** Manual processing for production volumes

**Recommendation:**
- Support batch JSON format
- Implement batch control number management
- Add batch processing CLI option

**Priority:** P3 - Production scalability

---

## Proposed Agent Architecture

### Agent 1: Pre-Submission Validator

**Purpose:** Validate JSON input before conversion

**Responsibilities:**
- JSON schema validation
- Required field checks
- Field length validation
- Code value validation (POS, HCPCS, modifiers, transport codes)
- Date format validation
- NPI checksum validation
- Cross-field business rules

**Implementation:**
```python
class PreSubmissionValidator:
    def validate(self, claim_json: dict) -> ValidationReport:
        - Check required fields
        - Validate NPI format (10 digits)
        - Validate dates (CCYY-MM-DD format)
        - Validate code values against lookup tables
        - Check claim-level vs line-level consistency
        - Return detailed error report
```

**Output:** Validation report with errors, warnings, info

---

### Agent 2: X12 Compliance Checker

**Purpose:** Validate generated EDI against X12 005010X222A1 spec

**Responsibilities:**
- Segment structure validation
- Loop hierarchy validation
- Required vs optional segment checks
- Element format validation (AN, N, R, ID, DT, TM)
- Segment order validation
- Control number validation

**Implementation:**
```python
class X12ComplianceChecker:
    def check(self, edi_content: str) -> ComplianceReport:
        - Parse EDI into segments
        - Validate segment structure
        - Check loop hierarchy
        - Validate element formats
        - Check required vs situational segments
        - Return compliance report
```

**Output:** Compliance report with X12 violations

---

### Agent 3: UHC Business Rule Validator

**Purpose:** Validate against UHC Community & State specific requirements

**Responsibilities:**
- K3 segment format validation (PYMS, SUB/IPAD/USER, SNWK, TRPN)
- NTE group structure validation (GRP/SGR/CLS/PLN/PRD)
- CR1 ambulance data validation (TRIPNUM, SPECNEED, etc.)
- 2310D/2420D supervising provider + REF*LU Trip Number
- 2400 NTE location/time format (PULOC/PUTIME/DOLOC/DOTIME)
- CLM05-3 frequency + REF*D9/F8 requirements
- 2430 SVD/CAS adjudication format

**Implementation:**
```python
class UHCBusinessRuleValidator:
    def validate(self, edi_content: str) -> UHCReport:
        - Parse EDI
        - Check K3 segment formats
        - Validate NTE group structure
        - Check ambulance-specific requirements
        - Validate trip number presence
        - Return UHC-specific violation report
```

**Output:** UHC compliance report

---

### Agent 4: Claim Enrichment Agent

**Purpose:** Auto-populate optional fields and defaults

**Responsibilities:**
- Cascade trip_number from claim to service lines if missing
- Set default POS code if missing
- Set default frequency code (1=original)
- Populate submission timestamps
- Generate control numbers
- Add missing address fields from provider registry

**Implementation:**
```python
class ClaimEnrichmentAgent:
    def enrich(self, claim_json: dict) -> dict:
        - Fill missing trip_number at service level
        - Set defaults for optional fields
        - Lookup provider data from registry
        - Generate control numbers
        - Return enriched claim JSON
```

**Output:** Enriched claim JSON ready for conversion

---

### Agent 5: Batch Processor

**Purpose:** Process multiple claims in batch

**Responsibilities:**
- Read batch JSON format
- Manage control numbers across batch
- Generate single EDI file with multiple ST/SE sets
- Create batch summary report
- Handle errors gracefully (skip invalid claims)

**Implementation:**
```python
class BatchProcessor:
    def process_batch(self, batch_json: dict) -> BatchResult:
        - Iterate over claims
        - Generate ST/SE for each claim
        - Manage GS/GE envelope
        - Manage ISA/IEA envelope
        - Create batch summary
        - Return EDI content + summary
```

**Output:** Batch EDI file + processing summary

---

## Recommended Workflow

```
┌─────────────────┐
│  Input JSON     │
└────────┬────────┘
         │
         v
┌─────────────────────────┐
│ Agent 4: Enrichment     │  ← Auto-populate defaults
└────────┬────────────────┘
         │
         v
┌─────────────────────────┐
│ Agent 1: Pre-Validation │  ← Validate JSON
└────────┬────────────────┘
         │
         ├─── FAIL ──> [Error Report]
         │
         v PASS
┌─────────────────────────┐
│  EDI Converter          │  ← builder.py
└────────┬────────────────┘
         │
         v
┌─────────────────────────┐
│ Agent 2: X12 Compliance │  ← Validate EDI structure
└────────┬────────────────┘
         │
         ├─── FAIL ──> [X12 Violation Report]
         │
         v PASS
┌─────────────────────────┐
│ Agent 3: UHC Validation │  ← Validate UHC rules
└────────┬────────────────┘
         │
         ├─── FAIL ──> [UHC Violation Report]
         │
         v PASS
┌─────────────────────────┐
│  Submit to Availity     │
└─────────────────────────┘
```

---

## Implementation Priorities

### Phase 1: Critical Fixes (P0)
- Fix CR1/CR109/CR110 segment construction
- Resolve trip_number cascade logic
- Implement basic input validation

### Phase 2: Compliance (P1)
- Fix 2310E/F vs 2420G/H loop hierarchy
- Implement Agent 1: Pre-Submission Validator
- Implement Agent 2: X12 Compliance Checker
- Implement Agent 3: UHC Business Rule Validator

### Phase 3: Production Readiness (P2)
- Externalize payer configuration
- Document frequency code workflow
- Implement Agent 4: Claim Enrichment
- Create test suite

### Phase 4: Scale & Polish (P3)
- Implement Agent 5: Batch Processor
- Generate comprehensive documentation
- Create scenario cookbook
- Add monitoring/logging

---

## Field Mapping Reference

### Claim-Level K3 Segments

| JSON Field | K3 Format | Example | Notes |
|------------|-----------|---------|-------|
| `claim.payment_status` | `PYMS-{P|D}` | `K3*PYMS-P~` | P=Paid, D=Denied |
| `claim.subscriber_internal_id` | `SUB-{value}` | `K3*SUB-SUB-INT-555~` | Part of compound K3 |
| `claim.ip_address` | `IPAD-{value}` | `K3*SUB-SUB-INT-555;IPAD-192.168.1.1~` | Part of compound K3 |
| `claim.user_id` | `USER-{value}` | `K3*USER-user123~` | Part of compound K3 |
| `claim.rendering_network_indicator` | `SNWK-{I|O}` | `K3*SNWK-I~` | I=In-network, O=Out |
| `claim.submission_channel` | `TRPN-ASPUFE{ELEC|PAPER}` | `K3*TRPN-ASPUFEELEC~` | Submission method |

### Claim-Level NTE Group Structure

| JSON Field | NTE Format | Position |
|------------|------------|----------|
| `claim.member_group.group_id` | `GRP-{value}` | 1 |
| `claim.member_group.sub_group_id` | `SGR-{value}` | 2 |
| `claim.member_group.class_id` | `CLS-{value}` | 3 |
| `claim.member_group.plan_id` | `PLN-{value}` | 4 |
| `claim.member_group.product_id` | `PRD-{value}` | 5 |

**Example:** `NTE*ADD*GRP-KYCD;SGR-KY11;CLS-KYRA;PLN-KYMANC;PRD-KYMANC~`

### Claim-Level CR1 Ambulance Data

| JSON Field | CR1 Position | Format | Example |
|------------|--------------|--------|---------|
| `ambulance.weight_unit` | CR101 | ID | `LB` |
| `ambulance.patient_weight_lbs` | CR102 | R | `165` |
| `ambulance.transport_code` | CR105 | ID | `A` |
| `ambulance.transport_reason` | CR106 | ID | `DH` |

**Second CR1 for trip details (custom format in CR109 - needs verification):**

| JSON Field | Format | Example |
|------------|--------|---------|
| `ambulance.trip_number` | `TRIPNUM-{9digits}` | `TRIPNUM-000000001` |
| `ambulance.special_needs` | `SPECNEED-{Y|N}` | `SPECNEED-N` |
| `ambulance.attendant_type` | `ATTENDTY-{value}` | `ATTENDTY-X` |
| `ambulance.accompany_count` | `ACCOMP-{count}` | `ACCOMP-1` |
| `ambulance.pickup_indicator` | `PICKUP-{value}` | `PICKUP-YM` |
| `ambulance.requested_date` | `TRIPREQ-{CCYYMMDD}` | `TRIPREQ-20260106` |

### Service-Level NTE Location/Time

| JSON Field | NTE Format | Example |
|------------|------------|---------|
| `services[].pickup_loc_code` | `PULOC-{code}` | `PULOC-RE` |
| `services[].pickup_time` | `PUTIME-{HHMM}` | `PUTIME-1100` |
| `services[].drop_loc_code` | `DOLOC-{code}` | `DOLOC-DO` |
| `services[].drop_time` | `DOTIME-{HHMM}` | `DOTIME-1130` |

**Example:** `NTE*ADD*PULOC-RE;PUTIME-1100;DOLOC-DO;DOTIME-1130~`

### Service-Level CR109 Trip Details (custom format - needs verification)

| JSON Field | Format | Example |
|------------|--------|---------|
| `services[].trip_type` | `TRIPTYPE-{I|R}` | `TRIPTYPE-I` |
| `services[].trip_leg` | `TRIPLEG-{A|B}` | `TRIPLEG-A` |
| `services[].vas_indicator` | `VAS-{Y|N}` | `VAS-N` |
| `services[].transport_type` | `TRANTYPE-{value}` | `TRANTYPE-WV` |
| `services[].appointment_time` | `APPTTIME-{HHMM}` | `APPTTIME-1130` |
| `services[].scheduled_pickup_time` | `SCHPUTIME-{HHMM}` | `SCHPUTIME-1100` |
| `services[].trip_reason_code` | `TRIPRSN-{code}` | `TRIPRSN-DO` |

### Service-Level CR110 Time/Location (custom format - needs verification)

| JSON Field | Format | Example |
|------------|--------|---------|
| `services[].arrive_time` | `ARRIVTIME-{HHMM}` | `ARRIVTIME-1055` |
| `services[].depart_time` | `DEPRTTIME-{HHMM}` | `DEPRTTIME-1102` |
| `services[].drop_loc_code` | `DOLOC-{code}` | `DOLOC-DO` |
| `services[].drop_time` | `DOTIME-{HHMM}` | `DOTIME-1130` |

---

## Next Steps

1. **Verify with UHC:** Confirm CR109/CR110 custom format requirements
2. **Fix Critical Issues:** Address gaps #1, #2, #3
3. **Implement Validators:** Build Agent 1, 2, 3 for compliance checking
4. **Create Test Suite:** Cover all scenarios (original, replacement, void)
5. **Document:** Create complete field mapping and scenario guide
6. **Production Hardening:** Batch processing, error handling, logging

---

## References

- ANSI X12 005010X222A1 Implementation Guide
- UHC Community & State NEMT Requirements
- Availity Submission Guidelines
- Kaizen Business Mapping 1.0
- UHC Kentucky NEMT Codes

---

**Document Version:** 1.0
**Last Updated:** 2025-11-10
**Author:** Gap Analysis & Architecture Review
