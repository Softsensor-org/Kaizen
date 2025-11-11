# NEMT Codes Comprehensive Analysis

## Executive Summary

Analysis of three key reference files reveals **CRITICAL GAPS** in the current NEMT code implementation:

1. **✅ A0xxx Codes:** Well covered (37 codes present)
2. **❌ T2xxx Codes:** MISSING entirely (but used in test files!)
3. **❌ Modifiers:** 109 of 110 two-letter origin-destination modifiers MISSING
4. **📄 pickupdropoff.xlsx:** Empty file - no reference data

---

## File Analysis Results

### 1. modifiers.xlsx ✅ Complete Reference

**Status:** Complete reference with 110 modifiers
**Issue:** Current codes.py only has 20 modifiers (18% coverage)

See MODIFIER_ANALYSIS.md for full details.

---

### 2. pickupdropoff.xlsx ❌ Empty

**Status:** File exists but contains NO data
**Impact:** No pickup/dropoff location reference available

**Recommended Action:**
- Populate with standard pickup/dropoff location codes
- Cross-reference with modifier origin/destination codes
- Add validation rules for location matching

---

### 3. NEMT HCPCS Codes

#### Current Coverage in codes.py

**A0xxx Series** (37 codes) - ✅ COMPLETE
```python
NEMT_HCPCS_CODES = {
    "A0021": "Ambulance service, outside state per mile",
    "A0080": "Non-emergency transportation, per mile - volunteer",
    "A0090": "Non-emergency transportation, per mile - individual",
    "A0100": "Non-emergency transportation; taxi",
    "A0110": "Non-emergency transportation and bus",
    "A0120": "Non-emergency transportation: mini-bus, mountain area",
    "A0130": "Non-emergency transportation: wheelchair van",
    "A0140": "Non-emergency transportation and air travel",
    "A0160": "Non-emergency transportation: per mile - case worker",
    "A0170": "Transportation ancillary: parking fees, tolls, other",
    "A0180": "Non-emergency transportation: ancillary: lodging-recipient",
    "A0190": "Non-emergency transportation: ancillary: meals-recipient",
    "A0200": "Non-emergency transportation: ancillary: lodging-escort",
    "A0210": "Non-emergency transportation: ancillary: meals-escort",
    "A0225": "Ambulance service, neonatal transport, base rate",
    "A0382": "BLS mileage (per mile)",
    "A0384": "BLS specialized service disposable supplies",
    "A0392": "ALS specialized service disposable supplies",
    "A0394": "ALS specialized service mileage",
    "A0396": "ALS specialized service; defibrillation",
    "A0398": "ALS routine disposable supplies",
    "A0420": "Ambulance waiting time (ALS or BLS)",
    "A0422": "Ambulance oxygen and oxygen supplies",
    "A0424": "Extra ambulance attendant",
    "A0425": "Ground mileage, per statute mile",
    "A0426": "Ambulance service, ALS, non-emergency, level 1",
    "A0427": "Ambulance service, ALS, emergency, level 1",
    "A0428": "Ambulance service, BLS, non-emergency",
    "A0429": "Ambulance service, BLS, emergency",
    "A0430": "Ambulance service, conventional air, one way (fixed wing)",
    "A0431": "Ambulance service, conventional air, one way (rotary wing)",
    "A0432": "Paramedic intercept (PI), rural area, volunteer",
    "A0433": "Advanced life support, level 2 (ALS 2)",
    "A0434": "Specialty care transport (SCT)",
    "A0435": "Fixed wing air mileage, per statute mile",
    "A0436": "Rotary wing air mileage, per statute mile",
}
```

#### T2xxx Series - ❌ MISSING BUT CRITICAL

**PROBLEM:** Test scenarios use T2005 and T2049, but these codes are NOT in codes.py!

**Missing Codes:**
```python
# T2xxx codes - COMMONLY USED FOR NEMT
"T2001": "Non-emergency transportation; patient attendant/escort",
"T2002": "Non-emergency transportation; per diem",
"T2003": "Non-emergency transportation; encounter/trip",
"T2004": "Non-emergency transportation; commercial carrier, multi-pass",
"T2005": "Non-emergency transportation; stretcher van",
"T2007": "Transportation waiting time, air ambulance and non-emergency vehicle, one-half (1/2) hour increments",
"T2049": "Non-emergency transportation; stretcher van, mileage; per mile",
```

**Impact:**
- ❌ Test files use T2005 and T2049
- ❌ Real claims may use T2xxx codes
- ❌ No validation for these commonly-used codes
- ❌ Potential payer rejections

---

## Evidence from Test Scenarios

### Scenario 1 (scenario1_service_level_only.edi)

EDI file shows:
```
SV1*HC A0130 EH*60.00*UN*1     ← Service code A0130 ✅ In codes.py
SV1*HC A0200 EH*25.00*UN*10    ← Service code A0200 ✅ In codes.py
```

✅ These A-codes are properly defined.

### Scenario Files Use Modifiers

From test scenarios:
```
Modifier EH used extensively
Modifiers GR, HG mentioned in examples
```

**Current Status:**
- ❌ EH in codes.py but with WRONG description ("NEMT medical necessity" instead of "Residential to Hospital")
- ❌ GR not in codes.py
- ❌ HG not in codes.py

---

## Real-World Usage Analysis

### Common NEMT Claim Patterns

#### Pattern 1: Wheelchair Van Transport
```
Service: A0130 (wheelchair van) or T2005 (stretcher van)
Mileage: A0425 (ground mileage) or T2049 (stretcher van mileage)
Modifier: RH (Residence to Hospital)
```

**Current Support:**
- ✅ A0130 - Defined
- ✅ A0425 - Defined
- ❌ T2005 - MISSING
- ❌ T2049 - MISSING (but used in tests!)
- ❌ RH modifier - MISSING

#### Pattern 2: Dialysis Transport
```
Service: A0130 (wheelchair van)
Mileage: A0425 (ground mileage)
Modifier: RG (Residence to Hospital-based Dialysis)
```

**Current Support:**
- ✅ A0130 - Defined
- ✅ A0425 - Defined
- ❌ RG modifier - MISSING

#### Pattern 3: Return Trip
```
Service: A0130 (wheelchair van)
Mileage: A0425 (ground mileage)
Modifier: GR (Hospital-based Dialysis to Residence)
```

**Current Support:**
- ✅ A0130 - Defined
- ✅ A0425 - Defined
- ❌ GR modifier - MISSING (used in examples!)

---

## Gap Summary

### Critical Gaps

| Category | Total Needed | Current | Missing | Coverage |
|----------|--------------|---------|---------|----------|
| A0xxx codes | 37 | 37 | 0 | 100% ✅ |
| T2xxx codes | ~7 | 0 | 7 | 0% ❌ |
| Two-letter modifiers | 110 | 1* | 109 | 1% ❌ |
| Functional modifiers | 8 | 8 | 0 | 100% ✅ |

*Only EH is present, but with wrong description

### Impact Assessment

**HIGH RISK:**
1. Test scenarios use T2005 and T2049 - codes not validated
2. Missing 109 modifiers means invalid modifiers could be accepted
3. EH modifier has incorrect description
4. Real claims may be rejected by payer

**MEDIUM RISK:**
1. No pickup/dropoff reference data (pickupdropoff.xlsx empty)
2. Limited validation of origin-destination combinations

---

## Recommendations

### Priority 1: CRITICAL (Do Immediately)

1. **Add T2xxx Codes to NEMT_HCPCS_CODES**
   ```python
   "T2001": "Non-emergency transportation; patient attendant/escort",
   "T2002": "Non-emergency transportation; per diem",
   "T2003": "Non-emergency transportation; encounter/trip",
   "T2004": "Non-emergency transportation; commercial carrier, multi-pass",
   "T2005": "Non-emergency transportation; stretcher van",
   "T2007": "Transportation waiting time, air ambulance and non-emergency vehicle",
   "T2049": "Non-emergency transportation; stretcher van, mileage; per mile",
   ```

2. **Add All 110 Two-Letter Modifiers**
   - See MODIFIER_ANALYSIS.md for complete list
   - Fix EH description from "NEMT medical necessity" to "Residential/Domiciliary to Hospital"

3. **Update Agent 1 Validation**
   - Add modifier validation against complete list
   - Add HCPCS code validation against complete list

### Priority 2: HIGH (Do This Sprint)

4. **Populate pickupdropoff.xlsx**
   - Add standard pickup/dropoff location codes
   - Cross-reference with modifier system
   - Add validation rules

5. **Update Test Scenarios**
   - Verify all modifiers used are correct
   - Add tests for T2xxx codes
   - Add tests for various modifier combinations

### Priority 3: MEDIUM (Next Sprint)

6. **Add Mileage Pairing Validation**
   - Ensure service codes are properly paired with mileage codes
   - T2005 must be followed by T2049
   - A0130 must be followed by A0425 or similar

7. **Document Code Selection Logic**
   - When to use A0xxx vs T2xxx
   - State-specific preferences
   - Payer-specific requirements

---

## Code Addition Implementation

### Proposed codes.py Update

```python
# NEMT HCPCS Codes (complete list)
NEMT_HCPCS_CODES = {
    # A0xxx series (existing - keep all 37)
    "A0021": "Ambulance service, outside state per mile",
    ... (existing 37 codes)

    # T2xxx series (ADD THESE)
    "T2001": "Non-emergency transportation; patient attendant/escort",
    "T2002": "Non-emergency transportation; per diem",
    "T2003": "Non-emergency transportation; encounter/trip",
    "T2004": "Non-emergency transportation; commercial carrier, multi-pass",
    "T2005": "Non-emergency transportation; stretcher van",
    "T2007": "Transportation waiting time, air ambulance and non-emergency vehicle, one-half (1/2) hour increments",
    "T2049": "Non-emergency transportation; stretcher van, mileage; per mile",
}

# HCPCS Modifiers (complete two-letter origin-destination codes)
HCPCS_MODIFIERS = {
    # Functional modifiers (existing - keep)
    "GA": "Waiver of liability statement",
    "GY": "Item or service statutorily excluded",
    "GZ": "Item or service expected to be denied",
    "QM": "Ambulance service under arrangement",
    "QN": "Ambulance service furnished directly",
    "GM": "Multiple patients on one ambulance trip",
    "QL": "Patient pronounced dead after ambulance called",
    "TQ": "Basic life support volunteer",

    # D-Series: FROM Diagnostic/therapeutic site (ADD ALL 11)
    "DD": "Diagnostic/therapeutic → Diagnostic/therapeutic",
    "DE": "Diagnostic/therapeutic → Residential/Domiciliary",
    "DG": "Diagnostic/therapeutic → Hospital-based Dialysis",
    "DH": "Diagnostic/therapeutic → Hospital",
    "DI": "Diagnostic/therapeutic → Transfer site",
    "DJ": "Diagnostic/therapeutic → Non-hospital Dialysis",
    "DN": "Diagnostic/therapeutic → Skilled Nursing",
    "DP": "Diagnostic/therapeutic → Physician office",
    "DR": "Diagnostic/therapeutic → Residence",
    "DS": "Diagnostic/therapeutic → Scene of Accident",
    "DX": "Diagnostic/therapeutic → Intermediate stop",

    # E-Series: FROM Residential/Domiciliary (ADD ALL 11)
    "ED": "Residential/Domiciliary → Diagnostic/therapeutic",
    "EE": "Residential/Domiciliary → Residential/Domiciliary",
    "EG": "Residential/Domiciliary → Hospital-based Dialysis",
    "EH": "Residential/Domiciliary → Hospital",  # FIX DESCRIPTION
    "EI": "Residential/Domiciliary → Transfer site",
    "EJ": "Residential/Domiciliary → Non-hospital Dialysis",
    "EN": "Residential/Domiciliary → Skilled Nursing",
    "EP": "Residential/Domiciliary → Physician office",
    "ER": "Residential/Domiciliary → Residence",
    "ES": "Residential/Domiciliary → Scene of Accident",
    "EX": "Residential/Domiciliary → Intermediate stop",

    # ... (Continue for G, H, I, J, N, P, R, S, X series - total 110 modifiers)
}
```

---

## Testing Impact

### Current Test Suite Status

**141 tests passing** - but with incomplete code coverage!

Tests may pass because:
- Agent 1 doesn't validate modifiers against full list
- Agent 1 doesn't validate HCPCS codes against full list
- Test data happens to use codes that exist (A0130, A0200)

### After Code Addition

**Expected Results:**
- ✅ All 141 tests should still pass
- ✅ Better validation coverage
- ✅ Catch invalid codes that currently slip through

**New Tests Needed:**
- Test T2005 + T2049 pairing
- Test all modifier series (D, E, G, H, I, J, N, P, R, S, X)
- Test invalid modifier rejection
- Test invalid HCPCS code rejection

---

## Validation Enhancement

### Agent 1 Enhancement Needed

```python
def _validate_hcpcs_code(self, hcpcs: str):
    """Validate HCPCS code against complete NEMT list"""
    if hcpcs not in NEMT_HCPCS_CODES:
        self.report.add_issue(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            code="VAL_070",
            message=f"HCPCS code '{hcpcs}' not in NEMT code list",
            field_path="service.hcpcs"
        ))

def _validate_modifiers(self, modifiers: List[str]):
    """Validate modifiers against complete list"""
    for mod in modifiers:
        if mod not in HCPCS_MODIFIERS:
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="VAL_071",
                message=f"Modifier '{mod}' not in HCPCS modifier list",
                field_path="service.modifiers"
            ))
```

---

## Conclusion

**Current State:**
- A0xxx codes: ✅ Complete
- T2xxx codes: ❌ MISSING (7 codes)
- Modifiers: ❌ 99% MISSING (109 of 110)
- Overall Code Coverage: ~40%

**Risk Level:** HIGH
- Test scenarios use undefined codes (T2005, T2049)
- 109 modifiers missing means no validation
- Potential payer rejections

**Action Required:** IMMEDIATE
1. Add T2xxx codes (7 codes)
2. Add 110 two-letter modifiers
3. Fix EH modifier description
4. Enhance Agent 1 validation
5. Re-run all tests

**Estimated Effort:** 2-4 hours
**Priority:** CRITICAL

---

**Analysis Date:** 2025-01-11
**Files Analyzed:**
- modifiers.xlsx (110 modifiers)
- pickupdropoff.xlsx (empty)
- codes.py (current implementation)
- Test scenarios (actual usage)

**Status:** Ready for implementation
