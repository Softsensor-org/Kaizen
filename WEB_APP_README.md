# NEMT 837P EDI Generator - Web Interface

A user-friendly web application to convert JSON or CSV claim data into EDI 837P format for NEMT (Non-Emergency Medical Transportation) claims submission.

## Features

- ✅ **Dual Input Format Support**: Upload JSON or CSV files
- ✅ **Real-time Validation**: Validates claims before EDI generation
- ✅ **Multiple Payer Support**: Pre-configured for UnitedHealthcare, Anthem, and others
- ✅ **CR109/CR110 Format**: Kaizen vendor default mode (§2.1.8)
- ✅ **Test & Production Modes**: Supports both test and production submissions
- ✅ **Interactive UI**: Modern, responsive web interface
- ✅ **Download & Copy**: Easy export of generated EDI files

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Web Server

```bash
python web_app.py
```

### 3. Open in Browser

Navigate to: [http://localhost:5000](http://localhost:5000)

## Usage

### Uploading JSON Files

1. Click "Select File" and choose your JSON file
2. Select "JSON" as the file type
3. Choose your payer from the dropdown
4. Click "Generate EDI"

**JSON Format Example:**
```json
{
  "submitter": { "name": "...", "id": "..." },
  "receiver": { "payer_name": "...", "payer_id": "..." },
  "billing_provider": { "npi": "...", "name": "..." },
  "subscriber": { "member_id": "...", "name": {...} },
  "claim": { "clm_number": "...", "total_charge": 100.00, ... },
  "services": [{ "hcpcs": "A0130", "charge": 100.00, ... }]
}
```

Download sample: [sample.json](static/examples/sample.json)

### Uploading CSV Files

1. Click "Select File" and choose your CSV file
2. Select "CSV" as the file type
3. Choose your payer from the dropdown
4. Click "Generate EDI"

**CSV Format Requirements:**

**Required Columns:**
- `member_id`, `member_first`, `member_last`, `member_dob`, `member_gender`
- `dos` (date of service), `hcpcs`, `charge`, `units`
- `billing_npi`, `billing_name`, `payer_name`, `payer_id`

**Optional Columns:**
- `rendering_npi`, `rendering_first`, `rendering_last`
- `supervising_npi`, `supervising_first`, `supervising_last`
- `pickup_addr`, `pickup_city`, `pickup_state`, `pickup_zip`
- `dropoff_addr`, `dropoff_city`, `dropoff_state`, `dropoff_zip`
- `transport_code`, `transport_reason`, `patient_weight`, `trip_number`
- `group_id`, `sub_group_id`, `class_id`, `plan_id`, `product_id`
- `network_indicator`, `authorization_number`, `modifiers`

Download sample: [sample.csv](static/examples/sample.csv)

## Configuration Options

### Payer Selection
- **UHC_CS**: UnitedHealthcare Community Plan - CS
- **UHC_MD**: UnitedHealthcare Community Plan - MD
- **ANTHEM_KY**: Anthem Kentucky
- **ANTHEM_BCBS**: Anthem Blue Cross Blue Shield
- **Generic**: No payer-specific configuration

### Mode Selection
- **Test Mode (T)**: For testing submissions
- **Production Mode (P)**: For live claims

### CR109/CR110 Format
- ✅ **Enabled (default)**: Kaizen vendor spec per §2.1.8
  - Pickup/dropoff in CR1 elements 9-10
  - No separate loops 2310E/F
- ❌ **Disabled**: Legacy NTE mode
  - CR1 with 8 elements
  - Separate loops 2310E/F for locations

## API Endpoints

### POST /api/generate-edi

Generate EDI from uploaded file.

**Request:**
```
Content-Type: multipart/form-data

file: [uploaded file]
file_type: "json" | "csv"
payer_code: "UHC_CS" | "ANTHEM_KY" | etc.
use_cr1_locations: "true" | "false"
usage_indicator: "T" | "P"
```

**Response:**
```json
{
  "success": true,
  "edi": "ISA*00*...",
  "validation_report": "...",
  "claim_data": {...},
  "stats": {
    "services": 2,
    "total_charge": 150.00,
    "member_id": "MEM123456789",
    "payer": "UNITED HEALTHCARE COMMUNITY"
  }
}
```

### POST /api/validate

Validate file without generating EDI.

**Request:**
```
Content-Type: multipart/form-data

file: [uploaded file]
file_type: "json" | "csv"
```

**Response:**
```json
{
  "success": true,
  "is_valid": true,
  "validation_report": "...",
  "errors": [],
  "warnings": []
}
```

### GET /api/payers

Get list of available payer configurations.

**Response:**
```json
[
  {"code": "UHC_CS", "name": "UnitedHealthcare Community Plan - CS"},
  {"code": "ANTHEM_KY", "name": "Anthem Kentucky"},
  ...
]
```

## File Structure

```
Kaizen/
├── web_app.py                          # Flask application
├── templates/
│   └── index.html                      # Main UI
├── static/
│   ├── css/
│   │   └── style.css                   # Styles
│   ├── js/
│   │   └── app.js                      # Client-side logic
│   └── examples/
│       ├── sample.json                 # Example JSON
│       └── sample.csv                  # Example CSV
├── nemt_837p_converter/
│   ├── csv_converter.py                # CSV to JSON converter
│   ├── builder.py                      # EDI builder
│   ├── validation.py                   # Pre-submission validation
│   └── ...
└── requirements.txt                    # Python dependencies
```

## CSV Converter Details

The CSV converter (`nemt_837p_converter/csv_converter.py`) automatically:

1. **Groups Service Lines**: Multiple CSV rows with same `member_id` → single claim with multiple services
2. **Calculates Totals**: Automatically sums service charges for `total_charge`
3. **Applies Defaults**: Uses sensible defaults for missing optional fields
4. **Validates Data**: Pre-validates before EDI generation
5. **Handles Locations**: Supports both claim-level and service-level pickup/dropoff

### CSV to JSON Mapping

| CSV Column | JSON Path |
|------------|-----------|
| `member_id` | `subscriber.member_id` |
| `member_first`, `member_last` | `subscriber.name.first/last` |
| `billing_npi`, `billing_name` | `billing_provider.npi/name` |
| `rendering_npi`, `rendering_first`, `rendering_last` | `rendering_provider.npi/first/last` |
| `hcpcs`, `charge`, `units` | `services[].hcpcs/charge/units` |
| `transport_code`, `transport_reason` | `claim.ambulance.transport_code/reason` |
| `group_id`, `sub_group_id`, ... | `claim.member_group.group_id/sub_group_id/...` |

## Validation

The web app validates claims using three agents:

1. **Agent 1**: Pre-submission validation
   - Required fields, data types, formats
   - Field lengths, value constraints
   - NEMT-specific business rules

2. **Agent 2**: X12 compliance checking (after generation)
   - Envelope structure, segment ordering
   - Loop hierarchy, element counts

3. **Agent 3**: Payer-specific validation
   - UHC business rules (UHC_001-UHC_020)
   - Payer-specific requirements

## Troubleshooting

### "No file selected" Error
- Make sure you've selected a file before clicking Generate/Validate

### "Invalid JSON format" Error
- Check JSON syntax is valid
- Use a JSON validator (e.g., jsonlint.com)
- Ensure all quotes are double-quotes (not single)

### "Claim validation failed" Error
- Review error messages in the Validation Report tab
- Check required fields are present
- Verify member_group fields are provided
- Ensure rendering provider has network_indicator

### CSV Import Issues
- Ensure header row has correct column names
- Check date format is YYYY-MM-DD
- Verify numeric fields (charge, units) are valid numbers
- Make sure modifiers are comma-separated if multiple

## Development

### Running Tests
```bash
# Test CSV converter and EDI generation
python test_web_app.py

# Run full test suite
python -m pytest tests/
```

### Adding Custom Payer Configs
Edit `nemt_837p_converter/payers.py` to add new payer configurations.

### Customizing the UI
- Edit `templates/index.html` for layout changes
- Edit `static/css/style.css` for styling
- Edit `static/js/app.js` for client-side behavior

## Compliance

**Current Compliance:** ~95% Kaizen Vendor Data Receipt Request

**Features Implemented:**
- ✅ Mandatory rendering provider with Kaizen fallback (§2.1.1)
- ✅ Member group enforcement (§2.1.2)
- ✅ CR109/CR110 default mode (§2.1.8)
- ✅ Coordination of Benefits (COB) support
- ✅ Auto-CAS generation for denied claims
- ✅ File naming convention validation (§2.2)
- ✅ NEMIS duplicate criteria (§2.1.10)

## Support

For issues or questions:
- Check the [main README](README.md)
- Review [VENDOR_RECEIPT_REQUEST_GAP_ANALYSIS.md](VENDOR_RECEIPT_REQUEST_GAP_ANALYSIS.md)
- Submit issues on GitHub

## License

Part of the Kaizen NEMT 837P Converter project.
