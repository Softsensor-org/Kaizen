# X12 Loop Hierarchy Analysis - UHC/Availity Verification Required

## Critical Issue: Ambiguous NM1 Qualifiers at Claim vs Service Levels

### Summary

The current EDI implementation uses **identical NM1 qualifier codes** for pickup/dropoff locations at both claim level (Loop 2310E/F) and service line level (Loop 2420G/H). This creates potential ambiguity in X12 parsing that requires verification with UHC Community & State and Availity clearinghouse.

---

## Loop Hierarchy Structure

### ANSI X12 005010X222A1 Standard:

```
ISA/GS/ST (Envelope)
  └─ Loop 1000A/B (Submitter/Receiver)
      └─ Loop 2000A (Billing Provider HL)
          └─ Loop 2000B (Subscriber HL)
              └─ Loop 2300 (Claim Information)
                  ├─ Loop 2310A (Referring Provider)
                  ├─ Loop 2310B (Rendering Provider)
                  ├─ Loop 2310C (Service Facility)
                  ├─ Loop 2310D (Supervising Provider) **[Claim Level]**
                  ├─ Loop 2310E (Ambulance Pick-up) **[Claim Level]**
                  └─ Loop 2310F (Ambulance Drop-off) **[Claim Level]**
                  └─ Loop 2400 (Service Line)
                      ├─ Loop 2420A (Rendering Provider)
                      ├─ Loop 2420B (Assistant Surgeon)
                      ├─ Loop 2420C (Ordered By Provider)
                      ├─ Loop 2420D (Supervising Provider) **[Service Level]**
                      ├─ Loop 2420E (Ambulance to Hospital)
                      ├─ Loop 2420F (Ambulance to Patient)
                      ├─ Loop 2420G (Ambulance Pick-up) **[Service Level]**
                      └─ Loop 2420H (Ambulance Drop-off) **[Service Level]**
                      └─ Loop 2430 (Line Adjudication)
```

---

## The Ambiguity Problem

### Current Implementation

**Claim Level (Loop 2310E/F):**
```
Loop 2310E - Ambulance Pick-up Location (Claim Level)
    NM1*PW*2~  ← Qualifier "PW"
    N3*55 Oak Rd~
    N4*Frankfort*KY*40601~

Loop 2310F - Ambulance Drop-off Location (Claim Level)
    NM1*45*2~  ← Qualifier "45"
    N3*100 Hospital Dr~
    N4*Lexington*KY*40508~
```

**Service Level (Loop 2420G/H):**
```
Loop 2420G - Ambulance Pick-up Location (Service Line Level)
    NM1*PW*2~  ← SAME Qualifier "PW"
    N3*55 Oak Rd~
    N4*Frankfort*KY*40601~

Loop 2420H - Ambulance Drop-off Location (Service Line Level)
    NM1*45*2~  ← SAME Qualifier "45"
    N3*100 Hospital Dr~
    N4*Lexington*KY*40508~
```

### Issue Details

1. **Identical Qualifiers**: Both 2310E and 2420G use `NM1*PW` (Pick-up Address)
2. **Identical Qualifiers**: Both 2310F and 2420H use `NM1*45` (Drop-off Location)
3. **Parsing Ambiguity**: EDI parsers must rely on **segment positioning** (before vs after LX segment) to distinguish claim-level vs service-level locations
4. **Potential Conflict**: If both claim-level and service-level locations are present, parsers may:
   - Overwrite claim-level with service-level data
   - Reject the claim as malformed
   - Require explicit loop distinguishers

---

## Example Scenarios

### Scenario 1: Single Trip (Service-Level Only)
**Situation**: Patient has one roundtrip (A0130 + A0200)

**EDI Structure:**
```
CLM*...*  (Claim start)
...
LX*1~  (Service line 1 - outbound)
SV1*HC A0130*...~
NM1*PW*2~  (2420G - pickup at home)
N3*55 Oak Rd~
NM1*45*2~  (2420H - dropoff at hospital)
N3*100 Hospital Dr~

LX*2~  (Service line 2 - return)
SV1*HC A0200*...~
NM1*PW*2~  (2420G - pickup at hospital)
N3*100 Hospital Dr~
NM1*45*2~  (2420H - dropoff at home)
N3*55 Oak Rd~
```

**Status**: ✓ Clear - No ambiguity, all locations at service level

---

### Scenario 2: Claim-Level + Service-Level Locations
**Situation**: Claim has default pickup/dropoff, but one service line has different locations

**EDI Structure:**
```
CLM*...*  (Claim start)
...
NM1*PW*2~  (2310E - default pickup for all services)
N3*55 Oak Rd~
NM1*45*2~  (2310F - default dropoff for all services)
N3*100 Hospital Dr~
...
LX*1~  (Service line 1 - uses claim-level defaults)
SV1*HC A0130*...~
[No NM1*PW or NM1*45 here - should use claim-level]

LX*2~  (Service line 2 - override with different dropoff)
SV1*HC A0200*...~
NM1*45*2~  (2420H - specific dropoff for this service)
N3*999 Different Hospital~
```

**Status**: ⚠️ **AMBIGUOUS** - Does service line 1 inherit claim-level pickup/dropoff? Does service line 2's NM1*45 override claim-level or just apply to this line?

---

### Scenario 3: Both Present for All Services
**Situation**: Claim-level locations AND service-level locations both present

**EDI Structure:**
```
CLM*...*  (Claim start)
NM1*PW*2~  (2310E - claim-level pickup)
N3*55 Oak Rd~
NM1*45*2~  (2310F - claim-level dropoff)
N3*100 Hospital Dr~
...
LX*1~
SV1*HC A0130*...~
NM1*PW*2~  (2420G - service-level pickup - SAME CODE!)
N3*55 Oak Rd~
NM1*45*2~  (2420H - service-level dropoff - SAME CODE!)
N3*100 Hospital Dr~
```

**Status**: ⚠️ **AMBIGUOUS** - Why are both present if they're identical? Which takes precedence?

---

## Questions for UHC/Availity

### 1. Loop Hierarchy Handling
**Question**: Does your EDI parser distinguish 2310E/F from 2420G/H based on loop position (before/after LX segment)?

**Expected Answer Options:**
- [ ] Yes - We use loop positioning to distinguish claim-level vs service-level
- [ ] No - We require different NM1 qualifiers for claim vs service levels
- [ ] Partial - We handle it, but prefer one level over the other

---

### 2. Precedence Rules
**Question**: If both claim-level (2310E/F) AND service-level (2420G/H) pickup/dropoff are present, which takes precedence?

**Expected Answer Options:**
- [ ] Service-level (2420) always overrides claim-level (2310)
- [ ] Claim-level (2310) is used only if service-level (2420) is absent
- [ ] Claim-level (2310) is not supported - always use service-level (2420)
- [ ] Both are supported and serve different purposes

---

### 3. Recommended Practice
**Question**: For NEMT claims with multiple service lines (A0130 + A0200 roundtrips), what is the recommended approach?

**Expected Answer Options:**
- [ ] **Option A**: Use service-level (2420G/H) for each service line (current implementation)
- [ ] **Option B**: Use claim-level (2310E/F) for common locations, service-level only for exceptions
- [ ] **Option C**: Use claim-level (2310E/F) exclusively, avoid service-level
- [ ] **Option D**: Use different NM1 qualifiers for claim vs service levels

---

### 4. Alternative Qualifiers
**Question**: If we need to distinguish claim-level from service-level, are alternative NM1 qualifiers acceptable?

**X12 Spec Alternatives:**
- **Loop 2310E**: `NM1*PW` (current) vs `NM1*TL` (Third Party Location)?
- **Loop 2310F**: `NM1*45` (current) vs other qualifier?
- **Loop 2420G**: Keep `NM1*PW`
- **Loop 2420H**: Keep `NM1*45`

**Expected Answer**: Guidance on whether alternative qualifiers are acceptable or if positioning is sufficient

---

## Current Implementation Status

### ✓ Working Correctly:
1. **Loop positioning**: 2310E/F before LX, 2420G/H after LX
2. **Loop marker comments**: Clear documentation of hierarchy
3. **Service-level support**: Full implementation of 2420G/H with addresses
4. **Claim-level support**: Full implementation of 2310E/F with addresses

### ⚠️ Requires Verification:
1. **UHC parsing**: Confirm UHC parser handles identical qualifiers correctly
2. **Availity clearinghouse**: Verify Availity forwards both levels correctly
3. **Precedence rules**: Document which level takes precedence when both present
4. **Best practices**: Establish when to use claim-level vs service-level

---

## Proposed Actions

### Immediate (Sprint 1.4):
1. **Document this analysis** ✓ (This file)
2. **Contact UHC/Availity** - Request clarification on loop hierarchy handling
3. **Test with sample claims** - Submit test claims with both levels to staging environment
4. **Review claim rejections** - Analyze any rejection codes related to location loops

### Follow-up (Sprint 1.5):
1. **Implement fixes** based on UHC/Availity response
2. **Update builder.py** if alternative qualifiers are required
3. **Add validation rules** to enforce recommended practices
4. **Update tests** to cover verified scenarios
5. **Document findings** in README and code comments

---

## References

- **X12 Spec**: ANSI X12 005010X222A1 - Health Care Claim: Professional
- **Loop 2310E**: Ambulance Pick-up Location (Claim Level)
- **Loop 2310F**: Ambulance Drop-off Location (Claim Level)
- **Loop 2420G**: Ambulance Pick-up Location (Service Line Level)
- **Loop 2420H**: Ambulance Drop-off Location (Service Line Level)
- **NM1 Qualifiers**:
  - `PW` = Pick-up Address
  - `45` = Drop-off Location
  - `TL` = Third Party Location (alternative)

---

## Contact Information Required

**UHC Community & State:**
- EDI Technical Support
- Payer ID: 87726
- Contact: [TO BE FILLED]
- Reference: NEMT 837P Loop Hierarchy Verification

**Availity Clearinghouse:**
- Clearinghouse Support
- Receiver ID: 030240928
- Contact: [TO BE FILLED]
- Reference: X12 Loop Positioning for NEMT Claims

---

## Next Steps

1. [ ] Submit this analysis to UHC EDI technical support
2. [ ] Submit this analysis to Availity clearinghouse support
3. [ ] Test claim submission with both scenarios to staging
4. [ ] Document responses in LOOP_HIERARCHY_RESOLUTION.md
5. [ ] Implement fixes in Sprint 1.5 based on responses

---

**Created**: 2025-11-11
**Sprint**: 1.4
**Status**: Awaiting UHC/Availity Response
**Priority**: Critical (P0)
