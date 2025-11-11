# Loop Hierarchy Test Scenarios for UHC/Availity Verification

## Purpose

These test scenarios demonstrate the loop hierarchy ambiguity with pickup/dropoff locations documented in [LOOP_HIERARCHY_ANALYSIS.md](../LOOP_HIERARCHY_ANALYSIS.md). They are designed for submission to UHC Community & State staging environment and Availity clearinghouse for verification.

## Test Scenarios

### Scenario 1: Service-Level Only (Baseline)
**File**: `scenario1_service_level_only.json` / `.edi`
**Claim Number**: `SCENARIO1-001`

**Structure**:
- ✓ Service-level pickup/dropoff (Loop 2420G/H) for both service lines
- ✗ NO claim-level pickup/dropoff (Loop 2310E/F)

**EDI Structure**:
```
CLM*SCENARIO1-001*...
  ... (claim-level segments)
  LX*1~
  SV1*...~
  NM1*PW*2~  ← Service-level pickup (2420G)
  N3*55 Oak Rd~
  N4*Frankfort*KY*40601~
  NM1*45*2~  ← Service-level dropoff (2420H)
  N3*100 Hospital Dr~
  N4*Lexington*KY*40508~

  LX*2~
  SV1*...~
  NM1*PW*2~  ← Service-level pickup (2420G)
  N3*100 Hospital Dr~
  N4*Lexington*KY*40508~
  NM1*45*2~  ← Service-level dropoff (2420H)
  N3*55 Oak Rd~
  N4*Frankfort*KY*40601~
```

**Expected Result**: ✓ **ACCEPT** - Clean, unambiguous structure

---

### Scenario 2: Claim-Level Only
**File**: `scenario2_claim_level_only.json` / `.edi`
**Claim Number**: `SCENARIO2-001`

**Structure**:
- ✓ Claim-level pickup/dropoff (Loop 2310E/F)
- ✗ NO service-level pickup/dropoff (Loop 2420G/H)

**EDI Structure**:
```
CLM*SCENARIO2-001*...
  ... (claim-level segments)
  NM1*PW*2~  ← Claim-level pickup (2310E)
  N3*55 Oak Rd (CLAIM LEVEL)~
  N4*Frankfort*KY*40601~
  NM1*45*2~  ← Claim-level dropoff (2310F)
  N3*100 Hospital Dr (CLAIM LEVEL)~
  N4*Lexington*KY*40508~

  LX*1~
  SV1*...~
  (no NM1*PW or NM1*45 at service level)

  LX*2~
  SV1*...~
  (no NM1*PW or NM1*45 at service level)
```

**Expected Result**: ✓ **ACCEPT** or ✗ **REJECT**?
**Question**: Does UHC/Availity support claim-level pickup/dropoff for all services, or must each service specify its own?

---

### Scenario 3: Both Levels Present (AMBIGUOUS)
**File**: `scenario3_both_levels_ambiguous.json` / `.edi`
**Claim Number**: `SCENARIO3-AMBIGUOUS`

**Structure**:
- ✓ Claim-level pickup/dropoff (Loop 2310E/F)
- ✓ Service-level pickup/dropoff (Loop 2420G/H) for all services
- ⚠️ **IDENTICAL NM1 qualifiers at both levels**

**EDI Structure**:
```
CLM*SCENARIO3-AMBIGUOUS*...
  ... (claim-level segments)
  NM1*PW*2~  ← Claim-level pickup (2310E) - SAME QUALIFIER
  N3*CLAIM LEVEL PICKUP - 2310E~
  N4*Frankfort*KY*40601~
  NM1*45*2~  ← Claim-level dropoff (2310F) - SAME QUALIFIER
  N3*CLAIM LEVEL DROPOFF - 2310F~
  N4*Lexington*KY*40508~

  LX*1~
  SV1*...~
  NM1*PW*2~  ← Service-level pickup (2420G) - SAME QUALIFIER!
  N3*SERVICE LEVEL PICKUP - 2420G~
  N4*Frankfort*KY*40601~
  NM1*45*2~  ← Service-level dropoff (2420H) - SAME QUALIFIER!
  N3*SERVICE LEVEL DROPOFF - 2420H~
  N4*Lexington*KY*40508~

  LX*2~
  SV1*...~
  NM1*PW*2~  ← Service-level pickup (2420G) - SAME QUALIFIER!
  N3*SERVICE LEVEL PICKUP 2 - 2420G~
  N4*Lexington*KY*40508~
  NM1*45*2~  ← Service-level dropoff (2420H) - SAME QUALIFIER!
  N3*SERVICE LEVEL DROPOFF 2 - 2420H~
  N4*Frankfort*KY*40601~
```

**Expected Result**: ✗ **REJECT** or ✓ **ACCEPT**?
**Critical Questions**:
1. Which level takes precedence when both are present?
2. Does service-level override claim-level?
3. Is this ambiguity acceptable, or should we use different qualifiers?
4. Should we only use one level (claim OR service, not both)?

**Agent 2 Detection**:
- ⚠️ WARNING [LOOP_002]: Pickup location (NM1*PW) present at both claim level (2310E) and service level (2420G)
- ⚠️ WARNING [LOOP_003]: Dropoff location (NM1*45) present at both claim level (2310F) and service level (2420H)

---

## How to Use These Scenarios

### Step 1: Review EDI Files
```bash
# View Scenario 1 (Service-level only)
cat test_scenarios/scenario1_service_level_only.edi

# View Scenario 2 (Claim-level only)
cat test_scenarios/scenario2_claim_level_only.edi

# View Scenario 3 (Both levels - ambiguous)
cat test_scenarios/scenario3_both_levels_ambiguous.edi
```

### Step 2: Run Compliance Checks
```bash
cd test_scenarios
python analyze_scenarios.py
```

This will generate compliance reports for all scenarios using Agent 2 (X12 Compliance Checker).

### Step 3: Submit to Staging Environment

**For UHC Community & State:**
1. Access UHC EDI staging portal
2. Submit all three scenarios as separate test claims
3. Record acceptance/rejection status
4. Capture any rejection codes or error messages
5. Document which scenario(s) are accepted

**For Availity Clearinghouse:**
1. Access Availity staging/test environment
2. Submit all three scenarios through clearinghouse
3. Monitor for 277CA (acknowledgment) responses
4. Check for any validation errors or warnings
5. Document clearinghouse behavior for each scenario

### Step 4: Analyze Results

Create a results table:

| Scenario | UHC Status | Availity Status | Notes |
|----------|------------|-----------------|-------|
| 1 (Service-only) | ? | ? | Baseline - should accept |
| 2 (Claim-only) | ? | ? | Alternative approach |
| 3 (Both levels) | ? | ? | Ambiguous - key test |

### Step 5: Update Documentation

Based on test results, update `LOOP_HIERARCHY_ANALYSIS.md` with:
- Confirmed precedence rules (if Scenario 3 accepts)
- Recommended approach (Scenario 1 vs 2 vs 3)
- Any payer-specific requirements
- Implementation fixes needed in `builder.py`

---

## Questions for UHC/Availity Technical Support

Include these scenarios in your technical support inquiry:

**Subject**: X12 837P Loop Hierarchy Verification - NEMT Ambulance Pickup/Dropoff Locations

**Body**:
```
We are implementing NEMT 837P claims for UHC Community & State (Payer ID: 87726)
and need clarification on loop hierarchy for ambulance pickup/dropoff locations.

ISSUE:
Loops 2310E/F (claim-level) and 2420G/H (service-level) use identical NM1 qualifiers:
- Loop 2310E and 2420G both use NM1*PW (pickup)
- Loop 2310F and 2420H both use NM1*45 (dropoff)

QUESTIONS:
1. When both claim-level (2310E/F) and service-level (2420G/H) locations are present,
   which takes precedence?

2. For NEMT claims with multiple service lines (A0130 + A0200 roundtrips), which
   approach is preferred:
   a) Service-level only (2420G/H) - each service specifies pickup/dropoff
   b) Claim-level only (2310E/F) - default locations for all services
   c) Both levels - claim defaults, service-level overrides when different

3. Are the identical NM1 qualifiers acceptable, or should we use different
   qualifiers at claim vs service levels?

ATTACHED:
- LOOP_HIERARCHY_ANALYSIS.md - Detailed technical analysis
- scenario1_service_level_only.edi - Baseline test claim
- scenario2_claim_level_only.edi - Alternative approach
- scenario3_both_levels_ambiguous.edi - Ambiguous case requiring verification

Please advise on the recommended approach for production claims.
```

---

## Expected Outcomes

### Best Case: Clear Precedence Rules
- Scenario 3 is accepted
- Documentation confirms service-level (2420) overrides claim-level (2310)
- Implementation: No changes needed, document precedence

### Alternative: Single-Level Requirement
- Scenario 3 is rejected
- Documentation requires ONE level only (either 2310 OR 2420, not both)
- Implementation: Add validation to prevent both levels

### Alternative Qualifiers Required
- Scenario 3 is rejected due to ambiguous qualifiers
- Documentation requires different NM1 codes at claim vs service levels
- Implementation: Research alternative qualifiers (e.g., NM1*TL for claim-level)

---

## Duplicate Rejection Mitigation Scenarios (State Reporting)

States that de-duplicate by `Member + DOS + Provider` require different claim
structures depending on whether the same rendering provider covers every leg or
multiple providers split the itinerary.

### Scenario 4: Multiple Legs, Single Provider
**File**: `scenario4_multi_trip_single_provider.json`

- Member takes three legs (Residence→Hospital→Lab→Residence) on the same DOS
- All transportation handled by **ABC Transport**
- Submit **one claim** with **six service lines** (pairs T2005/T2049 per leg)
- Prevents duplicate rejects because only one claim exists for the provider/DOS

Convert and inspect:
```bash
python -m nemt_837p_converter test_scenarios/scenario4_multi_trip_single_provider.json \
  --out out/scenario4.edi \
  --sender-qual ZZ --sender-id KAIZENKZN01 \
  --receiver-qual ZZ --receiver-id 030240928 \
  --usage T --gs-sender KAIZENKZN01 --gs-receiver 030240928
```

### Scenario 5: Multiple Legs, Multiple Providers
**Folder**: `scenario5_multi_provider/`

- Same member/DOS, but each leg handled by a different rendering provider
- Files:
  - `claim_cab_transport.json` (Residence→Hospital)
  - `claim_abc_transport.json` (Hospital→Lab)
  - `claim_def_transport.json` (Lab→Residence)
- Submit **three claims** (one per provider) with two service lines each

Convert each claim separately:
```bash
for claim in claim_cab_transport claim_abc_transport claim_def_transport; do
  python -m nemt_837p_converter test_scenarios/scenario5_multi_provider/${claim}.json \
    --out out/${claim}.edi \
    --sender-qual ZZ --sender-id KAIZENKZN01 \
    --receiver-qual ZZ --receiver-id 030240928 \
    --usage T --gs-sender KAIZENKZN01 --gs-receiver 030240928;
done
```

**Acceptance Criteria**
- Scenario 4: One claim, six `LX` segments, single billing/rendering provider
- Scenario 5: Three claims, two service lines each, provider-specific billing info
- Both approaches align with state duplicate logic (unique per DOS + provider)

---

## Files in This Directory

- `README.md` - This file
- `scenario1_service_level_only.json` - Scenario 1 input data
- `scenario1_service_level_only.edi` - Scenario 1 EDI output
- `scenario2_claim_level_only.json` - Scenario 2 input data
- `scenario2_claim_level_only.edi` - Scenario 2 EDI output
- `scenario3_both_levels_ambiguous.json` - Scenario 3 input data
- `scenario3_both_levels_ambiguous.edi` - Scenario 3 EDI output
- `analyze_scenarios.py` - Compliance analysis script
- `scenario4_multi_trip_single_provider.json` - Duplicate mitigation Scenario 4
- `scenario5_multi_provider/` - Folder containing three provider-specific claims

---

## Next Steps

1. ✅ Test scenarios created
2. ⏳ Submit to UHC/Availity staging (requires access)
3. ⏳ Analyze results and rejection codes
4. ⏳ Update LOOP_HIERARCHY_ANALYSIS.md with findings
5. ⏳ Implement fixes in builder.py (Sprint 1.5 completion)
6. ⏳ Add regression tests for verified scenarios

---

**Created**: 2025-11-11
**Status**: Ready for Staging Submission
**Priority**: Critical (P0) - Blocks production deployment
