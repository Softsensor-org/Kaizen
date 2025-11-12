# SPDX-License-Identifier: MIT
"""
Pytest configuration and fixtures
"""
import pytest
import json
from pathlib import Path


@pytest.fixture
def valid_claim_data():
    """Valid claim data for testing"""
    return {
        "submitter": {
            "id_qualifier": "ZZ",
            "id": "TESTID01",
            "name": "TEST SUBMITTER",
            "contact_name": "Test Contact",
            "contact_phone": "5555551234"
        },
        "receiver": {
            "payer_name": "TEST PAYER",
            "payer_id": "12345"
        },
        "billing_provider": {
            "npi": "1234567890",
            "tax_id": "123456789",
            "taxonomy": "343900000X",
            "name": "Test Provider",
            "address": {
                "line1": "123 Test St",
                "city": "Testville",
                "state": "NY",
                "zip": "12345"
            }
        },
        "subscriber": {
            "relationship": "self",
            "member_id": "TEST123456",
            "name": {
                "last": "Test",
                "first": "Patient"
            },
            "dob": "1990-01-01",
            "sex": "M",
            "address": {
                "line1": "456 Patient Rd",
                "city": "Testville",
                "state": "NY",
                "zip": "12345"
            }
        },
        "claim": {
            "clm_number": "TEST-001",
            "total_charge": 100.0,
            "pos": "41",
            "icd10": ["R99"],
            "from": "2026-01-01",
            "to": "2026-01-01",
            "frequency_code": "1",
            "member_group": {
                "group_id": "TESTGRP",
                "sub_group_id": "TESTSUB",
                "class_id": "TESTCLS",
                "plan_id": "TESTPLN",
                "product_id": "TESTPRD"
            },
            "rendering_network_indicator": "I"
        },
        "services": [
            {
                "seq": 1,
                "hcpcs": "A0130",
                "modifiers": ["EH"],
                "units": 1,
                "charge": 100.0,
                "dos": "2026-01-01",
                "emergency": False
            }
        ]
    }


@pytest.fixture
def minimal_claim_data():
    """Minimal valid claim data"""
    return {
        "submitter": {
            "id": "TEST01",
            "name": "Test Sub"
        },
        "receiver": {
            "payer_name": "Test Payer",
            "payer_id": "12345"
        },
        "billing_provider": {
            "npi": "1234567890",
            "name": "Test Provider",
            "address": {
                "line1": "123 Test St",
                "city": "Test",
                "state": "NY",
                "zip": "12345"
            }
        },
        "subscriber": {
            "member_id": "TEST123",
            "name": {
                "last": "Test",
                "first": "Patient"
            }
        },
        "claim": {
            "clm_number": "TEST-001",
            "total_charge": 100.0,
            "from": "2026-01-01",
            "member_group": {
                "group_id": "TESTGRP",
                "sub_group_id": "TESTSUB",
                "class_id": "TESTCLS",
                "plan_id": "TESTPLN",
                "product_id": "TESTPRD"
            },
            "rendering_network_indicator": "I"
        },
        "services": [
            {
                "hcpcs": "A0130",
                "charge": 100.0
            }
        ]
    }


@pytest.fixture
def invalid_claim_data():
    """Invalid claim data for testing validation"""
    return {
        "submitter": {},
        "receiver": {},
        "billing_provider": {
            "npi": "123",  # Invalid: must be 10 digits
            "name": "",
            "address": {
                "line1": "Test",
                "city": "Test",
                "state": "XX",  # Invalid state code
                "zip": "123"  # Invalid ZIP
            }
        },
        "subscriber": {
            "member_id": "",
            "name": {}
        },
        "claim": {
            "clm_number": "",
            "total_charge": 0,
            "from": "01/01/2026"  # Invalid date format
        },
        "services": []
    }


@pytest.fixture
def replacement_claim_data(valid_claim_data):
    """Replacement claim data"""
    data = valid_claim_data.copy()
    data["claim"]["frequency_code"] = "7"
    data["claim"]["tracking_number"] = "TRK-001-R1"
    data["claim"]["original_claim_number"] = "ORIG-001"  # Required for adjustments per §2.1.6
    return data


@pytest.fixture
def void_claim_data(valid_claim_data):
    """Void claim data"""
    data = valid_claim_data.copy()
    data["claim"]["frequency_code"] = "8"
    data["claim"]["total_charge"] = 0.0
    data["claim"]["original_claim_number"] = "ORIG-001"  # Required for adjustments per §2.1.6
    data["services"][0]["charge"] = 0.0
    data["services"][0]["units"] = 0
    return data


@pytest.fixture
def example_claim_data():
    """Load example claim data from examples/claim_kaizen.json"""
    example_path = Path(__file__).parent.parent / "examples" / "claim_kaizen.json"
    if example_path.exists():
        with open(example_path) as f:
            return json.load(f)
    return None
