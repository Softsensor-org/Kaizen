"""
Flask Web Application for NEMT 837P EDI Generation

Provides a web interface to upload JSON or CSV files and generate 837P EDI files.
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from typing import List, Dict, Any, Optional
import json
import traceback
from datetime import datetime, timedelta

from nemt_837p_converter import build_837p_from_json, Config, validate_claim_json, BatchProcessor
from nemt_837p_converter.csv_converter import parse_csv_to_json
from nemt_837p_converter.payers import get_payer_config
import csv
import io

app = Flask(__name__)
CORS(app)  # Enable CORS for API calls


@app.route('/')
def index():
    """Serve the main HTML page"""
    return render_template('index.html')


@app.route('/api/generate-edi', methods=['POST'])
def generate_edi():
    """
    API endpoint to generate EDI from uploaded file (JSON or CSV).

    Request:
        - file: uploaded file (JSON or CSV)
        - file_type: "json" or "csv"
        - payer_code: optional payer code (e.g., "UHC_CS", "ANTHEM_KY")
        - use_cr1_locations: optional boolean (default: true)

    Response:
        JSON with:
        - success: boolean
        - edi: generated EDI string (if successful)
        - validation_report: validation results
        - error: error message (if failed)
    """
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file uploaded'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        # Get file type
        file_type = request.form.get('file_type', 'json').lower()
        if file_type not in ['json', 'csv']:
            return jsonify({
                'success': False,
                'error': f'Invalid file type: {file_type}'
            }), 400

        # Read file content
        content = file.read().decode('utf-8')

        # Parse content based on file type
        if file_type == 'json':
            claim_data = json.loads(content)
        else:  # csv
            # Get optional config for CSV parsing
            csv_config = {
                'submitter_name': request.form.get('submitter_name', 'Kaizen Health'),
                'submitter_id': request.form.get('submitter_id', 'KAIZEN01'),
                'submitter_contact': request.form.get('submitter_contact', 'Claims Department'),
                'submitter_phone': request.form.get('submitter_phone', '5555551234')
            }
            claim_data = parse_csv_to_json(content, csv_config)

        # Validate claim data
        validation_report = validate_claim_json(claim_data)
        if not validation_report.is_valid:
            return jsonify({
                'success': False,
                'error': 'Claim validation failed',
                'validation_report': str(validation_report),
                'validation_errors': [
                    {
                        'code': issue.code,
                        'field': issue.field_path,
                        'message': issue.message
                    }
                    for issue in validation_report.errors
                ]
            }), 400

        # Get configuration options
        payer_code = request.form.get('payer_code', 'UHC_CS')
        use_cr1_locations = request.form.get('use_cr1_locations', 'true').lower() == 'true'
        usage_indicator = request.form.get('usage_indicator', 'T')  # T=Test, P=Production

        # Get payer config
        payer_config = None
        if payer_code:
            try:
                payer_config = get_payer_config(payer_code)
            except ValueError:
                # Invalid payer code, continue without payer-specific config
                pass

        # Build configuration
        config = Config(
            sender_qual="ZZ",
            sender_id=request.form.get('sender_id', 'KAIZEN01'),
            receiver_qual="ZZ",
            receiver_id=request.form.get('receiver_id', payer_code),
            usage_indicator=usage_indicator,
            gs_sender_code=request.form.get('gs_sender', 'KAIZEN'),
            gs_receiver_code=request.form.get('gs_receiver', payer_code),
            payer_config=payer_config,
            use_cr1_locations=use_cr1_locations
        )

        # Generate EDI
        edi_output = build_837p_from_json(claim_data, config)

        # Return success response
        return jsonify({
            'success': True,
            'edi': edi_output,
            'validation_report': str(validation_report),
            'claim_data': claim_data,  # Return parsed claim data for review
            'stats': {
                'services': len(claim_data.get('services', [])),
                'total_charge': claim_data.get('claim', {}).get('total_charge', 0),
                'member_id': claim_data.get('subscriber', {}).get('member_id', ''),
                'payer': claim_data.get('receiver', {}).get('payer_name', ''),
                'generated_at': datetime.now().isoformat()
            }
        })

    except json.JSONDecodeError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid JSON format: {str(e)}'
        }), 400

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Data error: {str(e)}'
        }), 400

    except Exception as e:
        # Log full traceback for debugging
        print(f"Error generating EDI: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500


def convert_csv_rows_to_trips(csv_rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Convert flat CSV dictionaries to nested trip format expected by BatchProcessor.

    Args:
        csv_rows: List of flat CSV dictionaries with fields like member_id, billing_npi, etc.

    Returns:
        List of trip dictionaries with nested structure (member, billing_provider, etc.)
    """
    trips = []

    for row in csv_rows:
        trip = {
            "dos": row.get("dos", "").strip(),
            "pos": row.get("pos", "41").strip() if row.get("pos") else "41",
            "member": {
                "member_id": row.get("member_id", "").strip(),
                "name": {
                    "first": row.get("member_first", "").strip(),
                    "last": row.get("member_last", "").strip()
                },
                "dob": row.get("member_dob", "").strip(),
                "gender": row.get("member_gender", "").strip(),
                "address": {
                    "line1": row.get("member_address", "").strip(),
                    "city": row.get("member_city", "").strip(),
                    "state": row.get("member_state", "").strip(),
                    "zip": row.get("member_zip", "").strip()
                }
            },
            "billing_provider": {
                "npi": row.get("billing_npi", "").strip(),
                "name": row.get("billing_name", "").strip(),
                "address": {
                    "line1": row.get("billing_address", "").strip(),
                    "city": row.get("billing_city", "").strip(),
                    "state": row.get("billing_state", "").strip(),
                    "zip": row.get("billing_zip", "").strip()
                },
                "taxonomy": "343900000X",  # Standard NEMT taxonomy
                "tax_id": row.get("billing_tax_id", row.get("billing_npi", "")[:9]).strip()
            },
            "rendering_provider": {
                "npi": row.get("rendering_npi", "").strip(),
                "first": row.get("rendering_first", "").strip(),
                "last": row.get("rendering_last", "").strip(),
                "address_line1": row.get("rendering_address", row.get("billing_address", "")).strip(),
                "city": row.get("rendering_city", row.get("billing_city", "")).strip(),
                "state": row.get("rendering_state", row.get("billing_state", "")).strip(),
                "zip": row.get("rendering_zip", row.get("billing_zip", "")).strip()
            },
            "payer": {
                "payer_name": row.get("payer_name", "").strip(),
                "payer_id": row.get("payer_id", "").strip()
            },
            "service": {
                "hcpcs": row.get("hcpcs", "").strip(),
                "modifiers": [m.strip() for m in row.get("modifiers", "").split(",") if m.strip()],
                "charge": float(row.get("charge", 0) or 0),
                "units": int(row.get("units", 1) or 1),
                "pos": row.get("pos", "41").strip() if row.get("pos") else "41",
                "emergency": row.get("emergency", "").strip().upper() in ["Y", "YES", "TRUE", "1"],
                "trip_number": int(row.get("service_trip_number") or 1) if row.get("service_trip_number") else 1
            },
            # Claim-level fields expected by batch processor
            "network_indicator": row.get("network_indicator", "I").strip() if row.get("network_indicator") else "I",
            "rendering_network_indicator": row.get("rendering_network_indicator", "I").strip() if row.get("rendering_network_indicator") else "I",
            "auth_number": row.get("authorization_number", "").strip() if row.get("authorization_number") else "",
        }

        # Add ambulance info if present
        if row.get("transport_code") or row.get("transport_reason") or row.get("patient_weight"):
            trip["ambulance"] = {
                "transport_code": row.get("transport_code", "A").strip() if row.get("transport_code") else "A",
                "transport_reason": row.get("transport_reason", "C").strip() if row.get("transport_reason") else "C",
            }
            if row.get("patient_weight"):
                trip["ambulance"]["patient_weight_lbs"] = int(row.get("patient_weight"))
                trip["ambulance"]["weight_unit"] = "LB"

        # Add member group info if present
        if any([row.get("group_id"), row.get("sub_group_id"), row.get("class_id"),
                row.get("plan_id"), row.get("product_id")]):
            trip["member_group"] = {}
            if row.get("group_id"):
                trip["member_group"]["group_id"] = row.get("group_id", "").strip()
            if row.get("sub_group_id"):
                trip["member_group"]["sub_group_id"] = row.get("sub_group_id", "").strip()
            if row.get("class_id"):
                trip["member_group"]["class_id"] = row.get("class_id", "").strip()
            if row.get("plan_id"):
                trip["member_group"]["plan_id"] = row.get("plan_id", "").strip()
            if row.get("product_id"):
                trip["member_group"]["product_id"] = row.get("product_id", "").strip()

        # Add pickup/dropoff if present
        if row.get("service_pickup_addr"):
            trip["pickup"] = {
                "addr": row.get("service_pickup_addr", "").strip(),
                "city": row.get("service_pickup_city", "").strip(),
                "state": row.get("service_pickup_state", "").strip(),
                "zip": row.get("service_pickup_zip", "").strip()
            }

        if row.get("service_dropoff_addr"):
            trip["dropoff"] = {
                "addr": row.get("service_dropoff_addr", "").strip(),
                "city": row.get("service_dropoff_city", "").strip(),
                "state": row.get("service_dropoff_state", "").strip(),
                "zip": row.get("service_dropoff_zip", "").strip()
            }

        # Phase 3: Add payment/lifecycle fields with defaults
        # Use values from CSV if present, otherwise generate defaults
        trip["payment_status"] = row.get("payment_status", "P").strip() if row.get("payment_status") else "P"
        trip["submission_channel"] = row.get("submission_channel", "ELECTRONIC").strip() if row.get("submission_channel") else "ELECTRONIC"

        # Calculate lifecycle dates relative to DOS if not in CSV
        if row.get("dos"):
            try:
                dos_date = datetime.strptime(row["dos"].strip(), "%Y-%m-%d")
                trip["received_date"] = row.get("received_date", (dos_date + timedelta(days=1)).strftime("%Y-%m-%d"))
                trip["adjudication_date"] = row.get("adjudication_date", (dos_date + timedelta(days=4)).strftime("%Y-%m-%d"))
                trip["paid_date"] = row.get("paid_date", (dos_date + timedelta(days=9)).strftime("%Y-%m-%d"))
            except:
                pass  # Skip date calculation if DOS is invalid

        # Financial amounts - use charge as allowed amount by default
        charge_amt = float(row.get("charge", 0) or 0)
        trip["allowed_amount"] = float(row.get("allowed_amount", charge_amt)) if row.get("allowed_amount") else charge_amt
        trip["not_covered_amount"] = float(row.get("not_covered_amount", 0)) if row.get("not_covered_amount") else 0.0
        trip["patient_paid_amount"] = float(row.get("patient_paid_amount", 0)) if row.get("patient_paid_amount") else 0.0

        # Portal tracking fields for K3*SUB...;IPAD...;USER... segment
        trip["subscriber_internal_id"] = row.get("subscriber_internal_id") or row.get("member_id", "")
        trip["ip_address"] = row.get("ip_address", "192.168.1.100")  # Default portal IP
        trip["user_id"] = row.get("user_id", "PORTAL_USER_001")  # Default portal user

        trips.append(trip)

    return trips


def convert_json_batch_to_trips(json_trips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert JSON batch trips to the format expected by BatchProcessor.
    JSON batch format has trips as flat dictionaries.
    """
    trips = []
    for trip_data in json_trips:
        # Build trip structure expected by BatchProcessor
        trip = {
            "dos": trip_data.get("dos", ""),
            "pos": trip_data.get("pos", "41"),
            "member": {
                "member_id": trip_data.get("member_id", ""),
                "name": {
                    "first": trip_data.get("member_first", ""),
                    "last": trip_data.get("member_last", "")
                },
                "dob": trip_data.get("member_dob", ""),
                "gender": trip_data.get("member_gender", ""),
                "addr": trip_data.get("member_address", ""),
                "city": trip_data.get("member_city", ""),
                "state": trip_data.get("member_state", ""),
                "zip": trip_data.get("member_zip", "")
            },
            "billing_provider": {
                "npi": trip_data.get("billing_npi", ""),
                "name": trip_data.get("billing_name", ""),
                "address": {
                    "line1": trip_data.get("billing_address", "200 Cab Lane"),
                    "city": trip_data.get("billing_city", "Louisville"),
                    "state": trip_data.get("billing_state", "KY"),
                    "zip": trip_data.get("billing_zip", "40202")
                },
                "taxonomy": trip_data.get("billing_taxonomy", "343900000X"),
                "tax_id": trip_data.get("billing_tax_id", trip_data.get("billing_npi", "")[:9] if trip_data.get("billing_npi") else "")
            },
            "payer": {
                "payer_name": trip_data.get("payer_name", ""),
                "payer_id": trip_data.get("payer_id", "")
            },
            "service": {
                "hcpcs": trip_data.get("hcpcs", ""),
                "charge": float(trip_data.get("charge", 0)),
                "units": float(trip_data.get("units", 1)),
                "modifiers": trip_data.get("modifiers", [])
            },
            "network_indicator": trip_data.get("network_indicator", "I"),
            "auth_number": trip_data.get("auth_number", "")
        }

        # Add rendering provider if present
        if trip_data.get("rendering_npi"):
            trip["rendering_provider"] = {
                "npi": trip_data.get("rendering_npi"),
                "first": trip_data.get("rendering_first", ""),
                "last": trip_data.get("rendering_last", "")
            }
            trip["rendering_network_indicator"] = trip_data.get("rendering_network_indicator", "I")

        # Add member group if present
        if trip_data.get("group_id"):
            trip["member_group"] = {
                "group_id": trip_data.get("group_id", ""),
                "sub_group_id": trip_data.get("sub_group_id", "KYSUB01"),
                "class_id": trip_data.get("class_id", "KYCLASS1"),
                "plan_id": trip_data.get("plan_id", "KYPLAN01"),
                "product_id": trip_data.get("product_id", "KYPROD01")
            }

        # Add pickup/dropoff if present
        if trip_data.get("pickup_addr"):
            trip["pickup"] = {
                "addr": trip_data.get("pickup_addr", ""),
                "city": trip_data.get("pickup_city", ""),
                "state": trip_data.get("pickup_state", ""),
                "zip": trip_data.get("pickup_zip", "")
            }

        if trip_data.get("dropoff_addr"):
            trip["dropoff"] = {
                "addr": trip_data.get("dropoff_addr", ""),
                "city": trip_data.get("dropoff_city", ""),
                "state": trip_data.get("dropoff_state", ""),
                "zip": trip_data.get("dropoff_zip", "")
            }

        # Phase 3 fields with defaults
        trip["payment_status"] = trip_data.get("payment_status", "P")
        trip["submission_channel"] = trip_data.get("submission_channel", "ELECTRONIC")
        trip["subscriber_internal_id"] = trip_data.get("subscriber_internal_id") or trip_data.get("member_id", "")
        trip["ip_address"] = trip_data.get("ip_address", "192.168.1.100")
        trip["user_id"] = trip_data.get("user_id", "PORTAL_USER_001")

        # Calculate lifecycle dates
        dos_str = trip_data.get("dos", "")
        if dos_str:
            try:
                dos_date = datetime.strptime(dos_str, "%Y-%m-%d")
                trip["received_date"] = trip_data.get("received_date", (dos_date + timedelta(days=1)).strftime("%Y-%m-%d"))
                trip["adjudication_date"] = trip_data.get("adjudication_date", (dos_date + timedelta(days=4)).strftime("%Y-%m-%d"))
                trip["paid_date"] = trip_data.get("paid_date", (dos_date + timedelta(days=9)).strftime("%Y-%m-%d"))
            except:
                pass

        # Financial amounts
        charge_amt = float(trip_data.get("charge", 0))
        trip["allowed_amount"] = float(trip_data.get("allowed_amount", charge_amt))
        trip["not_covered_amount"] = float(trip_data.get("not_covered_amount", 0))
        trip["patient_paid_amount"] = float(trip_data.get("patient_paid_amount", 0))

        trips.append(trip)

    return trips


@app.route('/api/batch-generate', methods=['POST'])
def batch_generate_edi():
    """
    API endpoint to generate multiple EDI files from a single CSV or JSON file.
    Automatically splits by provider and generates separate claims.

    Request:
        - file: uploaded CSV or JSON file
        - file_type: 'csv' or 'json' (auto-detected from filename if not specified)
        - payer_code: optional payer code
        - use_cr1_locations: optional boolean (default: true)

    Response:
        JSON with:
        - success: boolean
        - claims: array of claim objects with EDI
        - batch_report: batch processing report
        - error: error message (if failed)
    """
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file uploaded'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        # Detect file type
        file_type = request.form.get('file_type', '')
        if not file_type:
            # Auto-detect from filename
            if file.filename.endswith('.json'):
                file_type = 'json'
            else:
                file_type = 'csv'

        # Read file content
        content = file.read().decode('utf-8')

        # Parse based on file type
        if file_type == 'json':
            # JSON batch format: { "trips": [...] }
            batch_data = json.loads(content)
            if 'trips' not in batch_data:
                return jsonify({
                    'success': False,
                    'error': 'JSON file must contain a "trips" array'
                }), 400
            json_trips = batch_data['trips']
            if not json_trips:
                return jsonify({
                    'success': False,
                    'error': 'Trips array is empty'
                }), 400

            # Convert JSON trips to nested format expected by BatchProcessor
            trips = convert_json_batch_to_trips(json_trips)
            first_trip = trips[0]
            input_row_count = len(json_trips)
        else:
            # CSV format
            csv_reader = csv.DictReader(io.StringIO(content))
            csv_rows = list(csv_reader)

            if not csv_rows:
                return jsonify({
                    'success': False,
                    'error': 'CSV file is empty'
                }), 400

            # Convert CSV rows to trip format
            trips = convert_csv_rows_to_trips(csv_rows)
            first_trip = csv_rows[0] if csv_rows else {}
            input_row_count = len(csv_rows)

        # Prepare common data from first trip/row
        first_row = first_trip
        common_data = {
            "submitter": {
                "name": request.form.get('submitter_name', 'Kaizen Health Services'),
                "id": request.form.get('submitter_id', 'KAIZEN01'),
                "contact": request.form.get('submitter_contact', 'Claims Department'),
                "phone": request.form.get('submitter_phone', '5555551234')
            },
            "receiver": {
                "payer_name": first_row.get("payer_name", "").strip(),
                "payer_id": first_row.get("payer_id", "").strip()
            }
        }

        # Process batch - will automatically split by provider
        processor = BatchProcessor()
        claims, batch_report = processor.process_batch(trips, common_data)

        if not batch_report.success:
            return jsonify({
                'success': False,
                'error': 'Batch processing failed',
                'batch_report': str(batch_report),
                'errors': [
                    {
                        'code': issue.code,
                        'message': issue.message,
                        'trip_indices': issue.trip_indices
                    }
                    for issue in batch_report.errors
                ]
            }), 400

        # Add submitter and receiver to each claim
        for claim in claims:
            claim['submitter'] = common_data['submitter']
            claim['receiver'] = common_data['receiver']

        # Get configuration options
        payer_code = request.form.get('payer_code', 'UHC_CS')
        use_cr1_locations = request.form.get('use_cr1_locations', 'true').lower() == 'true'
        usage_indicator = request.form.get('usage_indicator', 'T')

        # Get payer config
        payer_config = None
        if payer_code:
            try:
                payer_config = get_payer_config(payer_code)
            except ValueError:
                pass

        # Build configuration
        config = Config(
            sender_qual="ZZ",
            sender_id=request.form.get('sender_id', 'KAIZEN01'),
            receiver_qual="ZZ",
            receiver_id=request.form.get('receiver_id', payer_code),
            usage_indicator=usage_indicator,
            gs_sender_code=request.form.get('gs_sender', 'KAIZEN'),
            gs_receiver_code=request.form.get('gs_receiver', payer_code),
            payer_config=payer_config,
            use_cr1_locations=use_cr1_locations
        )

        # Generate EDI for each claim
        results = []
        for i, claim in enumerate(claims, 1):
            try:
                # Validate claim
                validation_report = validate_claim_json(claim)

                if validation_report.is_valid:
                    # Generate EDI
                    edi_output = build_837p_from_json(claim, config)

                    results.append({
                        'claim_number': i,
                        'clm_id': claim.get('claim', {}).get('clm_number', ''),
                        'provider_name': claim.get('billing_provider', {}).get('name', ''),
                        'provider_npi': claim.get('billing_provider', {}).get('npi', ''),
                        'services': len(claim.get('services', [])),
                        'total_charge': claim.get('claim', {}).get('total_charge', 0),
                        'edi': edi_output,
                        'validation_report': str(validation_report),
                        'claim_data': claim
                    })
                else:
                    results.append({
                        'claim_number': i,
                        'provider_name': claim.get('billing_provider', {}).get('name', ''),
                        'error': 'Validation failed',
                        'validation_errors': [
                            {
                                'code': issue.code,
                                'field': issue.field_path,
                                'message': issue.message
                            }
                            for issue in validation_report.errors
                        ]
                    })

            except Exception as e:
                results.append({
                    'claim_number': i,
                    'provider_name': claim.get('billing_provider', {}).get('name', ''),
                    'error': f'EDI generation failed: {str(e)}',
                    'traceback': traceback.format_exc()
                })

        # Return success response
        return jsonify({
            'success': True,
            'claims': results,
            'batch_report': str(batch_report),
            'stats': {
                'input_rows': input_row_count,
                'claims_generated': len(claims),
                'successful_edi': len([r for r in results if 'edi' in r]),
                'failed': len([r for r in results if 'error' in r]),
                'total_charge': sum(r.get('total_charge', 0) for r in results),
                'generated_at': datetime.now().isoformat()
            }
        })

    except Exception as e:
        print(f"Error in batch processing: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/validate', methods=['POST'])
def validate_file():
    """
    API endpoint to validate file without generating EDI.

    Request:
        - file: uploaded file (JSON or CSV)
        - file_type: "json" or "csv"

    Response:
        JSON with validation report
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file uploaded'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        file_type = request.form.get('file_type', 'json').lower()
        content = file.read().decode('utf-8')

        # Parse content
        if file_type == 'json':
            claim_data = json.loads(content)
        else:
            claim_data = parse_csv_to_json(content)

        # Validate
        validation_report = validate_claim_json(claim_data)

        return jsonify({
            'success': True,
            'is_valid': validation_report.is_valid,
            'validation_report': str(validation_report),
            'errors': [
                {
                    'code': issue.code,
                    'field': issue.field_path,
                    'message': issue.message
                }
                for issue in validation_report.errors
            ],
            'warnings': [
                {
                    'code': issue.code,
                    'field': issue.field_path,
                    'message': issue.message
                }
                for issue in validation_report.warnings
            ]
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/payers', methods=['GET'])
def get_payers():
    """Get list of available payer configurations"""
    # This would be enhanced to dynamically load from payers module
    payers = [
        {'code': 'UHC_CS', 'name': 'UnitedHealthcare Community Plan - CS'},
        {'code': 'UHC_MD', 'name': 'UnitedHealthcare Community Plan - MD'},
        {'code': 'ANTHEM_KY', 'name': 'Anthem Kentucky'},
        {'code': 'ANTHEM_BCBS', 'name': 'Anthem Blue Cross Blue Shield'},
        {'code': 'GENERIC', 'name': 'Generic Payer (No specific config)'}
    ]
    return jsonify(payers)


if __name__ == '__main__':
    # Run development server
    print("=" * 60)
    print("NEMT 837P EDI Generator - Web Interface")
    print("=" * 60)
    print("Starting Flask development server...")
    print("Open your browser to: http://localhost:5000")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
