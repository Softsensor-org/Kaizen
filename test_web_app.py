"""Quick test of CSV converter and EDI generation"""

from nemt_837p_converter import build_837p_from_json, Config, validate_claim_json
from nemt_837p_converter.csv_converter import convert_csv_file
from nemt_837p_converter.payers import get_payer_config
import json
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 60)
print("Testing NEMT 837P Web App Components")
print("=" * 60)

# Test 1: CSV to JSON conversion
print("\n1. Testing CSV Converter...")
try:
    claim_data = convert_csv_file('static/examples/sample.csv')
    print("[OK] CSV conversion successful")
    print(f"  - Member ID: {claim_data['subscriber']['member_id']}")
    print(f"  - Services: {len(claim_data['services'])}")
    print(f"  - Total: ${claim_data['claim']['total_charge']}")
except Exception as e:
    print(f"✗ CSV conversion failed: {e}")

# Test 2: JSON file loading
print("\n2. Testing JSON Loader...")
try:
    with open('static/examples/sample.json', 'r') as f:
        json_claim = json.load(f)
    print("✓ JSON loading successful")
    print(f"  - Member ID: {json_claim['subscriber']['member_id']}")
    print(f"  - Services: {len(json_claim['services'])}")
except Exception as e:
    print(f"✗ JSON loading failed: {e}")

# Test 3: Validation
print("\n3. Testing Claim Validation...")
try:
    validation_report = validate_claim_json(claim_data)
    if validation_report.is_valid:
        print("✓ Claim validation passed")
    else:
        print(f"✗ Claim validation failed with {len(validation_report.errors)} errors")
        for error in validation_report.errors[:3]:
            print(f"  - {error.message}")
except Exception as e:
    print(f"✗ Validation failed: {e}")

# Test 4: EDI Generation from CSV
print("\n4. Testing EDI Generation from CSV...")
try:
    config = Config(
        sender_id="TEST",
        receiver_id="TEST",
        gs_sender_code="TEST",
        gs_receiver_code="TEST",
        payer_config=get_payer_config("UHC_CS"),
        use_cr1_locations=True  # Kaizen default
    )
    edi = build_837p_from_json(claim_data, config)
    print("✓ EDI generation successful")
    print(f"  - EDI length: {len(edi)} characters")
    print(f"  - Segments: {edi.count('~')}")
    print(f"  - Preview: {edi[:100]}...")
except Exception as e:
    print(f"✗ EDI generation failed: {e}")

# Test 5: EDI Generation from JSON
print("\n5. Testing EDI Generation from JSON...")
try:
    edi_json = build_837p_from_json(json_claim, config)
    print("✓ EDI generation from JSON successful")
    print(f"  - EDI length: {len(edi_json)} characters")
except Exception as e:
    print(f"✗ EDI generation from JSON failed: {e}")

print("\n" + "=" * 60)
print("All tests completed!")
print("=" * 60)
print("\nReady to start web server with: python web_app.py")
