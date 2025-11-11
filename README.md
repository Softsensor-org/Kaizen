# NEMT 837P Converter (Kaizen/UHC KY – JSON → X12 005010X222A1)

Implements Kaizen encounter requirements for UHC C&S:
- 2300 K3: PYMS P/D; SUB/IPAD/USER; SNWK I/O; TRPN-ASPUFEELEC/PAPER
- 2300 NTE: GRP/SGR/CLS/PLN/PRD group structure
- 2300 CR1: Proper X12 ambulance transport information (weight, transport code/reason)
- 2300 NTE: TRIPNUM/SPECNEED/ATTENDTY/ACCOMP/PICKUP/TRIPREQ (custom UHC format)
- 2310E/F and 2420G/H for pickup/drop-off
- 2310D/2420D supervising with REF*LU Trip Number (cascades from claim level if not specified at service level)
- 2400 NTE: PULOC/PUTIME/DOLOC/DOTIME
- 2400 NTE: Trip details (TRIPTYPE/TRIPLEG/VAS/TRANTYPE/APPTTIME/SCHPUTIME/TRIPRSN)
- 2400 NTE: Arrival/departure times (ARRIVTIME/DEPRTTIME)
- 2400 SV109 emergency Y/N
- CLM05-3 frequency (1/7/8), REF*D9 tracking, REF*F8 account
- 2430 SVD/CAS with paid units in SVD05, MOA at claim

## Installation & Run
```bash
cd nemt_837p_converter
python -m nemt_837p_converter examples/claim_kaizen.json --out out.edi \
  --sender-qual ZZ --sender-id KAIZENKZN01 \
  --receiver-qual ZZ --receiver-id 030240928 \
  --usage T --gs-sender KAIZENKZN01 --gs-receiver 030240928
```

## Input Validation

The converter validates all required fields before generating EDI. Validation errors will be displayed with specific field paths.

### Required Fields:

**Billing Provider:**
- `billing_provider.npi` (must be 10 digits)
- `billing_provider.name`
- `billing_provider.address` (line1, city, state, zip)

**Subscriber:**
- `subscriber.member_id`
- `subscriber.name.last`
- `subscriber.name.first`

**Claim:**
- `claim.clm_number` (max 30 characters)
- `claim.total_charge`
- `claim.from` (format: YYYY-MM-DD)

**Services:**
- At least one service required
- `services[].hcpcs`
- `services[].charge`

### Example Validation Error:
```
Validation Error: billing_provider.npi must be 10 digits, got: 123; claim.from must be in YYYY-MM-DD format, got: 01/07/2026
```

## P0 Fixes Applied

### 1. CR1 Segment Construction
- **Fixed:** Proper X12 CR1 format for ambulance transport information
- **Before:** Invalid CR109/CR110 pseudo-segments using CR1 tag
- **After:** Proper CR1 segment + NTE segments for custom UHC data

### 2. Trip Number Cascade
- **Fixed:** Automatic cascade from `claim.ambulance.trip_number` to service lines
- Service-level trip_number takes precedence if provided
- Enables REF*LU Trip Number at 2420D level

### 3. Input Validation
- Pre-submission validation with detailed error messages
- Required field checks
- Format validation (NPI, dates, claim number length)
- Prevents invalid EDI generation
