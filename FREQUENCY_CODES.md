# Frequency Code Workflow Guide

## Overview

Frequency codes (CLM05-3) indicate the type of claim submission:
- **1** = Original claim (first submission)
- **6** = Corrected claim (correcting errors in a previously accepted claim)
- **7** = Replacement claim (replacing a previously submitted claim)
- **8** = Void/Cancel claim (canceling a previously submitted claim)

## Workflow Scenarios

### Scenario 1: Original Claim Submission

**Use Case:** First time submitting a claim

**Frequency Code:** `1` (Original)

**JSON Example:**
```json
{
  "claim": {
    "clm_number": "KZN-2026-000001",
    "frequency_code": "1",
    "total_charge": 85.0,
    ...
  }
}
```

**Notes:**
- If `frequency_code` is omitted, it defaults to "1"
- Use unique claim number for tracking

---

### Scenario 2: Replacement Claim

**Use Case:** Replacing a previously submitted claim that was accepted but needs to be replaced entirely

**Frequency Code:** `7` (Replacement)

**JSON Example:**
```json
{
  "claim": {
    "clm_number": "KZN-2026-000001",
    "frequency_code": "7",
    "total_charge": 90.0,
    ...
  }
}
```

**Requirements:**
- Use the **same claim number** as the original claim
- Include all corrected data
- Original claim will be replaced entirely

**When to Use:**
- Need to change service dates
- Need to change diagnosis codes
- Need to add/remove services
- Need to change substantial claim data

---

### Scenario 3: Corrected Claim

**Use Case:** Correcting specific errors in an already accepted claim

**Frequency Code:** `6` (Corrected)

**JSON Example:**
```json
{
  "claim": {
    "clm_number": "KZN-2026-000001",
    "frequency_code": "6",
    "total_charge": 85.0,
    ...
  }
}
```

**Requirements:**
- Use the **same claim number** as the original claim
- Include only the corrected information
- Typically used for minor corrections

**When to Use:**
- Correcting patient name
- Correcting provider information
- Fixing minor data errors
- Already processed claims

---

### Scenario 4: Void/Cancel Claim

**Use Case:** Canceling a previously submitted claim

**Frequency Code:** `8` (Void)

**JSON Example:**
```json
{
  "claim": {
    "clm_number": "KZN-2026-000001",
    "frequency_code": "8",
    "total_charge": 0.0,
    ...
  }
}
```

**Requirements:**
- Use the **same claim number** as the claim to void
- Set `total_charge` to `0.0`
- Service charges can be `0.0`
- Original claim will be canceled

**When to Use:**
- Claim submitted in error
- Duplicate claim was submitted
- Services were not actually provided
- Patient was not eligible

---

## Alternative: Using adjustment_type Field

The converter also supports the `adjustment_type` field as an alternative to `frequency_code`:

```json
{
  "claim": {
    "clm_number": "KZN-2026-000001",
    "adjustment_type": "replacement",
    ...
  }
}
```

**Valid values:**
- `"replacement"` → frequency_code = "7"
- `"void"` → frequency_code = "8"
- (omitted or other) → frequency_code = "1"

**Precedence:**
- If both `frequency_code` and `adjustment_type` are provided, `frequency_code` takes precedence

---

## Best Practices

### 1. Claim Number Management
- **Original claims:** Use unique, sequential claim numbers
- **Replacements/Voids:** Use the **exact same** claim number as the original
- **Format:** Include identifiers (e.g., `KZN-2026-000001`)

### 2. Tracking Numbers
- Use `tracking_number` (REF*D9) to track claim lifecycle
- Use consistent tracking numbers across original and replacement claims

### 3. Documentation
- Keep records of which claims were replaced/voided
- Document reason for replacement/void
- Track submission dates

### 4. Testing
- Always test replacements/voids in **Test mode** first (`usage_indicator: "T"`)
- Verify with payer before submitting production voids

---

## Workflow Examples

### Example 1: Correcting a Claim with Wrong Service Date

**Original Claim (Frequency 1):**
```json
{
  "claim": {
    "clm_number": "KZN-2026-000001",
    "frequency_code": "1",
    "from": "2026-01-07",
    "tracking_number": "TRK-12345"
  },
  "services": [
    {
      "hcpcs": "A0130",
      "dos": "2026-01-07",
      "charge": 60.0
    }
  ]
}
```

**Replacement Claim (Frequency 7):**
```json
{
  "claim": {
    "clm_number": "KZN-2026-000001",
    "frequency_code": "7",
    "from": "2026-01-08",
    "tracking_number": "TRK-12345-R1"
  },
  "services": [
    {
      "hcpcs": "A0130",
      "dos": "2026-01-08",
      "charge": 60.0
    }
  ]
}
```

---

### Example 2: Voiding a Duplicate Claim

**Original Claim:**
```json
{
  "claim": {
    "clm_number": "KZN-2026-000002",
    "frequency_code": "1",
    "total_charge": 85.0
  }
}
```

**Void Claim:**
```json
{
  "claim": {
    "clm_number": "KZN-2026-000002",
    "frequency_code": "8",
    "total_charge": 0.0
  },
  "services": [
    {
      "hcpcs": "A0130",
      "charge": 0.0,
      "units": 0
    }
  ]
}
```

---

## Payer-Specific Requirements

### UHC Community & State
- Support all frequency codes (1, 6, 7, 8)
- Requires same claim number for replacements/voids
- Accepts void claims with zero charges
- May require prior authorization for high-volume corrections

### General Guidelines
- Check with payer for specific requirements
- Some payers may have waiting periods before allowing replacements
- Voided claims may affect provider statistics

---

## Validation

The converter validates:
- ✓ Frequency code is in valid set (1, 6, 7, 8)
- ✓ Date formats
- ✓ Required fields present

The converter does NOT validate:
- ✗ Whether claim number matches an existing claim
- ✗ Whether replacement is appropriate
- ✗ Whether void is allowed by payer

**Recommendation:** Implement external validation to ensure:
- Replacement/void claims reference existing original claims
- Claim numbers are tracked in your system
- Business rules are enforced before submission

---

## Troubleshooting

### Issue: Replacement claim rejected - "Claim not found"
**Cause:** Claim number doesn't match any original claim
**Solution:** Verify original claim was accepted and use exact same claim number

### Issue: Void claim rejected - "Cannot void paid claim"
**Cause:** Some payers don't allow voiding after payment
**Solution:** Contact payer or submit corrected claim instead

### Issue: Multiple replacements rejected
**Cause:** Some payers limit number of replacements
**Solution:** Ensure accuracy before submission, contact payer for policy

---

## References

- ANSI X12 005010X222A1 Implementation Guide - CLM segment
- UHC Community & State EDI Companion Guide
- Availity Claim Status Guidelines

---

**Document Version:** 1.0
**Last Updated:** 2025-11-10
