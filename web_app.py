"""
Flask Web Application for NEMT 837P EDI Generation

Provides a web interface to upload JSON or CSV files and generate 837P EDI files.
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
import traceback
from datetime import datetime

from nemt_837p_converter import build_837p_from_json, Config, validate_claim_json
from nemt_837p_converter.csv_converter import parse_csv_to_json
from nemt_837p_converter.payers import get_payer_config

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
