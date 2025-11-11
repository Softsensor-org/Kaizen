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

# List available payer configurations
python -m nemt_837p_converter --list-payers

# Convert with specific payer configuration
python -m nemt_837p_converter examples/claim_kaizen.json --out out.edi \
  --sender-qual ZZ --sender-id KAIZENKZN01 \
  --receiver-qual ZZ --receiver-id 030240928 \
  --usage T --gs-sender KAIZENKZN01 --gs-receiver 030240928 \
  --payer UHC_CS

# Or use payer data from JSON (omit --payer argument)
python -m nemt_837p_converter examples/claim_kaizen.json --out out.edi \
  --sender-qual ZZ --sender-id KAIZENKZN01 \
  --receiver-qual ZZ --receiver-id 030240928 \
  --usage T --gs-sender KAIZENKZN01 --gs-receiver 030240928
```

## Input Validation

The converter performs comprehensive validation before generating EDI, including:
- **Required fields** - Ensures all mandatory data is present
- **Format validation** - Validates dates (YYYY-MM-DD), NPIs (10 digits), ZIP codes, etc.
- **Length validation** - Enforces X12 element length limits
- **Code value validation** - Validates against standard code sets

### Required Fields:

**Billing Provider:**
- `billing_provider.npi` (must be 10 digits)
- `billing_provider.name` (max 60 characters)
- `billing_provider.address.line1` (max 55 characters)
- `billing_provider.address.city` (max 30 characters)
- `billing_provider.address.state` (valid US state code)
- `billing_provider.address.zip` (format: 12345 or 12345-6789)
- `billing_provider.tax_id` (9 digits, optional)

**Subscriber:**
- `subscriber.member_id` (max 80 characters)
- `subscriber.name.last` (max 60 characters)
- `subscriber.name.first` (max 35 characters)
- `subscriber.dob` (format: YYYY-MM-DD, optional)
- `subscriber.sex` (F/M/U, optional)

**Claim:**
- `claim.clm_number` (max 30 characters)
- `claim.total_charge`
- `claim.from` (format: YYYY-MM-DD)
- `claim.to` (format: YYYY-MM-DD, optional)
- `claim.pos` (valid Place of Service code, optional)
- `claim.frequency_code` (1/6/7/8, optional)

**Services:**
- At least one service required
- `services[].hcpcs` (max 5 characters)
- `services[].charge`
- `services[].modifiers` (max 4 modifiers, 2 characters each, optional)
- `services[].dos` (format: YYYY-MM-DD, optional)

### Validated Code Values:

- **Place of Service (POS)** - 41 (Ambulance Land), 42 (Ambulance Air/Water), etc.
- **Transport Codes** - A, B, C, D, E
- **Transport Reason** - A, B, C, D, DH, E
- **Weight Units** - LB, KG
- **Gender** - F, M, U
- **Trip Types** - I (Initial), R (Return), B (Both)
- **Trip Legs** - A, B
- **Network Indicators** - I (In-network), O (Out-of-network)
- **Payment Status** - P (Paid), D (Denied)
- **Submission Channels** - ELECTRONIC, PAPER

### Example Validation Error:
```
Validation Error: billing_provider.npi must be 10 digits, got: 123; billing_provider.address.state 'XX' is not a valid US state code; claim.ambulance.transport_code 'Z' is not a valid code. Valid values: A, B, C, D, E
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

## P1 Enhancements Applied

### 4. Comprehensive Field Validation
- **Code value validation** - Validates against standard X12 code sets
  - Place of Service codes (POS 41, 42, etc.)
  - Transport codes (A, B, C, D, E)
  - Transport reason codes (A, B, C, D, DH, E)
  - Gender codes (F, M, U)
  - Trip types, legs, network indicators
  - Weight units (LB, KG)
  - Payment status (P, D)
- **Length validation** - Enforces X12 element length limits
  - Provider names, addresses
  - Subscriber names
  - HCPCS codes, modifiers
- **Format validation** - Extended to cover
  - State codes (US states)
  - ZIP codes (12345 or 12345-6789)
  - Tax ID (9 digits)
  - Date formats (YYYY-MM-DD)
- **Business rule validation**
  - Max 4 modifiers per service
  - Modifier length (2 characters)
  - HCPCS code length (5 characters)

### 5. Payer Configuration System
- **Externalized payer data** - No more hardcoded payer IDs
- **Predefined payer configurations:**
  - `UHC_CS` - United Healthcare Community & State (ID: 87726)
  - `UHC_KY` - United Healthcare Kentucky (ID: 87726)
  - `AVAILITY` - Availity (ID: 030240928)
- **CLI support** - `--payer UHC_CS` or use JSON receiver data
- **List payers** - `--list-payers` command shows available configs
- **Flexible configuration** - Can use predefined or custom payer data
- **Automatic fallback** - Uses receiver data from JSON if no payer specified

**Benefits:**
- Easy to add new payers without code changes
- Consistent payer data across claims
- Supports multi-payer environments
- Reduces configuration errors

## P2 Production Readiness Features

### 6. Frequency Code Workflow Documentation
- **Comprehensive guide** - See [FREQUENCY_CODES.md](FREQUENCY_CODES.md)
- **Supports all frequency types:**
  - `1` - Original claim (first submission)
  - `6` - Corrected claim (minor corrections)
  - `7` - Replacement claim (full replacement)
  - `8` - Void/cancel claim
- **Workflow examples** - Original → Replacement → Void scenarios
- **Best practices** - Claim number management, tracking, testing
- **Alternative format** - Support `adjustment_type` field (`"replacement"`, `"void"`)
- **Validation** - Allow zero charges for void claims (frequency_code=8)

### 7. Claim Enrichment Agent
- **Auto-populate defaults** - Automatically fill missing optional fields
- **Data cascading** - Cascade data from claim to service level
- **Smart defaults:**
  - `pos` defaults to "41" (Ambulance Land)
  - `frequency_code` defaults to "1" (Original)
  - `to` date defaults to `from` date
  - Service `dos` defaults to claim `from` date
  - Service `pos` defaults to claim `pos`
  - Service `units` defaults to 1
  - Service `emergency` defaults to False
- **Cascading features:**
  - `trip_number` from claim.ambulance to services
  - `payment_status` from claim to services
  - `pickup/dropoff` from claim.ambulance to services
- **Flexible usage:**
  - CLI: `--enrich` flag
  - API: `enrich_claim(data)` function
  - Custom defaults: `enrich_claim(data, defaults={"pos": "42"})`
  - In-place modification: `enrich_claim(data, in_place=True)`

**Example:**
```bash
# Auto-populate optional fields before conversion
python -m nemt_837p_converter claim.json --out out.edi --enrich ...
```

### 8. Comprehensive Test Suite
- **37 test cases** - Full coverage of validation, enrichment, and EDI generation
- **Test categories:**
  - Validation tests (12 tests) - Field validation, code values, formats
  - Enrichment tests (15 tests) - Default values, cascading, in-place
  - Builder tests (11 tests) - EDI structure, segments, frequency codes
- **Test fixtures** - Valid, minimal, invalid, replacement, void claims
- **Run tests:** `pytest tests/ -v`
- **Coverage:** Core functionality, edge cases, error handling
- **Continuous testing** - Easy to add new tests for new features

**Run tests:**
```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```
