# Scenario 2: Multiple Trips, Same DOS, Different Providers

## Overview

This scenario demonstrates what happens when a member takes multiple trips on the same date of service (DOS) using **different transportation providers**. According to billing rules, each provider must submit a separate claim.

## Scenario Details

**Member:** John Doe (JOHN123456)
**Date of Service:** January 1, 2026
**Total Trips:** 3
**Total Service Lines:** 6 (2 per trip: transport + mileage)
**Combined Charges:** $625.00

## Trip Breakdown

| Trip | Provider | HCPCS | Modifier | Units/Miles | Charge | Route |
|------|----------|-------|----------|-------------|--------|-------|
| **1** | **CAB Transport** | | | | **$180.00** | **Residence → Hospital** |
| | (NPI: 2222222222) | T2005 | EH | 1 | $100.00 | Transport |
| | | T2049 | EH | 8 miles | $80.00 | Mileage |
| **2** | **ABC Transport** | | | | **$225.00** | **Hospital → LAB** |
| | (NPI: 4444444444) | T2006 | HG | 1 | $125.00 | Wheelchair van |
| | | T2049 | HG | 10 miles | $100.00 | Mileage |
| **3** | **DEF Transport** | | | | **$220.00** | **LAB → Residence** |
| | (NPI: 6666666666) | T2005 | GR | 1 | $100.00 | Transport |
| | | T2049 | GR | 12 miles | $120.00 | Mileage |

## Files Provided

### CSV Format (Raw Data)
- **`scenario2_multi_provider.csv`** - All 6 service lines in one file
  - Contains 3 different billing NPIs
  - Requires batch processing to split into separate claims
  - Use with batch processor (Agent 5)

### JSON Formats

#### Individual Claims (Web Interface Ready)
1. **`scenario2_claim1_cab.json`** - CAB Transport claim only ($180.00)
2. **`scenario2_claim2_abc.json`** - ABC Transport claim only ($225.00)
3. **`scenario2_claim3_def.json`** - DEF Transport claim only ($220.00)

Each JSON file is a complete, standalone claim ready for EDI generation.

#### Batch Format
- **`scenario2_multi_provider_batch.json`** - All 6 trips as raw trip data
  - Use with batch processor
  - Will be automatically split by provider

## Key Differences from Scenario 1

| Aspect | Scenario 1 | Scenario 2 |
|--------|------------|------------|
| **Providers** | Same provider (ABC) | 3 different providers |
| **Claims** | 1 claim, 6 service lines | 3 claims, 2 service lines each |
| **Claim Numbers** | 1 (CLM20260101001) | 3 (CLM...CAB001, CLM...ABC002, CLM...DEF003) |
| **Submission** | Single claim submission | Requires 3 separate submissions |
| **Batch Processing** | Optional (grouping) | **Required** (claim splitting) |

## Usage

### Web Interface (Single Claim)

Upload **individual claim files** to generate EDI:

```bash
# Generate EDI for CAB Transport trip
Upload: scenario2_claim1_cab.json
Result: 1 claim with 2 service lines

# Generate EDI for ABC Transport trip
Upload: scenario2_claim2_abc.json
Result: 1 claim with 2 service lines

# Generate EDI for DEF Transport trip
Upload: scenario2_claim3_def.json
Result: 1 claim with 2 service lines
```

### Batch Processing (Multiple Claims)

Use **CSV or batch JSON** with the batch processor:

```python
from nemt_837p_converter import BatchProcessor

# Process CSV - automatically splits by provider
processor = BatchProcessor()
report = processor.process_file('scenario2_multi_provider.csv')

# Result: 3 separate claims generated
# - CAB Transport: 2 service lines
# - ABC Transport: 2 service lines
# - DEF Transport: 2 service lines
```

## Business Rules

### Why Separate Claims?

Per §2.1.9 (Grouping & Encounter Scenarios):

> **Rule:** Claims are grouped by billing provider NPI + rendering provider NPI + DOS + member ID

When any of these change, a **new claim** must be created.

In this scenario:
- ✅ Same DOS (2026-01-01)
- ✅ Same member (JOHN123456)
- ❌ **Different providers** → Requires separate claims

### Claim Splitting Criteria

The batch processor splits claims when:
1. Billing provider NPI changes
2. Rendering provider NPI changes
3. Date of service changes
4. Member ID changes

## NEMIS Duplicate Detection

Each claim has unique identifiers to avoid duplicate detection:

- **Claim 1:** CLM20260101CAB001 + CAB Transport NPI
- **Claim 2:** CLM20260101ABC002 + ABC Transport NPI
- **Claim 3:** CLM20260101DEF003 + DEF Transport NPI

Even though they're the same member/DOS, different providers = different claims.

## Testing

```bash
# Test CSV conversion and claim count
python -c "
from nemt_837p_converter.csv_converter import convert_csv_file
claim = convert_csv_file('static/examples/scenario2_multi_provider.csv')
print(f'Services: {len(claim[\"services\"])}')  # Shows 6
print(f'Provider: {claim[\"billing_provider\"][\"name\"]}')  # Shows first provider
"

# Test individual claim JSON files
python -c "
from nemt_837p_converter import build_837p_from_json, Config
import json

config = Config(sender_id='TEST', receiver_id='TEST',
                gs_sender_code='TEST', gs_receiver_code='TEST')

for claim_file in ['scenario2_claim1_cab.json',
                   'scenario2_claim2_abc.json',
                   'scenario2_claim3_def.json']:
    with open(f'static/examples/{claim_file}', 'r') as f:
        claim = json.load(f)
    edi = build_837p_from_json(claim, config)
    print(f'{claim_file}: {edi.count(\"~\")} segments')
"
```

## Expected EDI Output

Each claim generates approximately:
- **42 segments** per claim
- **1,150-1,170 characters** per EDI file

Total across 3 claims:
- **126 segments** total
- **~3,500 characters** total

## Related Scenarios

- **Scenario 1:** Multiple trips, same provider (1 claim)
- **Scenario 3:** Multiple trips, different DOS (separate claims by date)
- **Scenario 4:** Adjustment claims (frequency code 7/8)

## Notes

⚠️ **Important:** When using the web interface, you must upload each claim separately. The web interface is designed for single claim submission. For bulk processing with automatic claim splitting, use the batch processor.

✅ **Compliance:** This scenario is fully compliant with Kaizen vendor requirements and NEMIS grouping rules.
