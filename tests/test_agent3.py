"""
Tests for Agent 3: UHC Business Rule Validator

Tests the UHCBusinessRuleValidator class with direct UHCReport testing.
"""

import pytest
from nemt_837p_converter import (
    UHCBusinessRuleValidator, validate_uhc_business_rules,
    UHCReport, UHCRuleViolation, UHCRuleSeverity
)


def test_valid_uhc_claim_passes(valid_claim_data):
    """Test that valid UHC claim returns is_compliant=True report"""
    # Add minimal UHC requirements
    valid_claim_data["claim"]["ambulance"] = {
        "transport_code": "A",
        "transport_reason": "A",
        "trip_number": 12345,
        "patient_weight_lbs": 150,
        "weight_unit": "LB"
    }
    valid_claim_data["claim"]["rendering_network_indicator"] = "I"
    valid_claim_data["claim"]["member_group"] = {"group_id": "GROUP123", "plan_id": "PLAN456"}
    valid_claim_data["claim"]["auth_number"] = "AUTH123"

    validator = UHCBusinessRuleValidator()
    report = validator.validate_claim(valid_claim_data)

    assert isinstance(report, UHCReport)
    assert report.is_compliant is True
    assert len(report.errors) == 0


def test_uhc_report_structure():
    """Test UHCReport dataclass structure"""
    report = UHCReport(is_compliant=True)

    assert hasattr(report, 'is_compliant')
    assert hasattr(report, 'errors')
    assert hasattr(report, 'warnings')
    assert hasattr(report, 'info')
    assert report.errors == []
    assert report.warnings == []
    assert report.info == []


def test_uhc_rule_violation_structure():
    """Test UHCRuleViolation dataclass structure"""
    violation = UHCRuleViolation(
        severity=UHCRuleSeverity.ERROR,
        code="UHC_001",
        message="Test message",
        rule_name="Test Rule"
    )

    assert violation.severity == UHCRuleSeverity.ERROR
    assert violation.code == "UHC_001"
    assert violation.message == "Test message"
    assert violation.rule_name == "Test Rule"


def test_uhc_001_nemt_ambulance_data_required(valid_claim_data):
    """Test UHC_001: NEMT claims with ambulance HCPCS codes must include ambulance data"""
    # Add NEMT code without ambulance data
    valid_claim_data["services"][0]["hcpcs"] = "A0130"
    # Remove ambulance data entirely
    if "ambulance" in valid_claim_data["claim"]:
        del valid_claim_data["claim"]["ambulance"]

    validator = UHCBusinessRuleValidator()
    report = validator.validate_claim(valid_claim_data)

    assert report.is_compliant is False
    uhc_001_errors = [e for e in report.errors if e.code == "UHC_001"]
    assert len(uhc_001_errors) == 1
    assert "ambulance data" in uhc_001_errors[0].message.lower()


def test_uhc_002_payment_status_values(valid_claim_data):
    """Test UHC_002: Payment status should be P (Paid) or D (Denied)"""
    valid_claim_data["claim"]["payment_status"] = "X"  # Invalid

    validator = UHCBusinessRuleValidator()
    report = validator.validate_claim(valid_claim_data)

    uhc_002_warnings = [w for w in report.warnings if w.code == "UHC_002"]
    assert len(uhc_002_warnings) == 1
    assert uhc_002_warnings[0].severity == UHCRuleSeverity.WARNING


def test_uhc_003_network_indicator_recommended(valid_claim_data):
    """Test UHC_003: Network indicator (I/O) recommended"""
    # Remove network indicator
    if "rendering_network_indicator" in valid_claim_data["claim"]:
        del valid_claim_data["claim"]["rendering_network_indicator"]

    validator = UHCBusinessRuleValidator()
    report = validator.validate_claim(valid_claim_data)

    uhc_003_warnings = [w for w in report.warnings if w.code == "UHC_003"]
    assert len(uhc_003_warnings) == 1
    assert "network indicator" in uhc_003_warnings[0].message.lower()


def test_uhc_004_submission_channel_tracking(valid_claim_data):
    """Test UHC_004: Submission channel tracking"""
    # Remove submission channel
    if "submission_channel" in valid_claim_data["claim"]:
        del valid_claim_data["claim"]["submission_channel"]

    validator = UHCBusinessRuleValidator()
    report = validator.validate_claim(valid_claim_data)

    uhc_004_info = [i for i in report.info if i.code == "UHC_004"]
    assert len(uhc_004_info) == 1
    assert uhc_004_info[0].severity == UHCRuleSeverity.INFO
    assert "submission channel" in uhc_004_info[0].message.lower()


def test_uhc_005_member_group_structure(valid_claim_data):
    """Test UHC_005: UHC Kentucky requires group_id and plan_id"""
    valid_claim_data["claim"]["member_group"] = {"group_id": ""}  # Missing plan_id

    validator = UHCBusinessRuleValidator()
    report = validator.validate_claim(valid_claim_data)

    uhc_005_warnings = [w for w in report.warnings if w.code == "UHC_005"]
    assert len(uhc_005_warnings) == 1
    assert "member group" in uhc_005_warnings[0].message.lower()


def test_uhc_006_patient_weight_recommended(valid_claim_data):
    """Test UHC_006: Patient weight information recommended"""
    valid_claim_data["claim"]["ambulance"] = {
        "transport_code": "A",
        "transport_reason": "A"
        # Missing weight_unit and patient_weight_lbs
    }

    validator = UHCBusinessRuleValidator()
    report = validator.validate_claim(valid_claim_data)

    uhc_006_warnings = [w for w in report.warnings if w.code == "UHC_006"]
    assert len(uhc_006_warnings) == 1
    assert "weight" in uhc_006_warnings[0].message.lower()


def test_uhc_007_transport_code_required(valid_claim_data):
    """Test UHC_007: Transport code required for ambulance claims"""
    valid_claim_data["claim"]["ambulance"] = {
        "transport_reason": "A",
        "patient_weight_lbs": 150
        # Missing transport_code
    }

    validator = UHCBusinessRuleValidator()
    report = validator.validate_claim(valid_claim_data)

    assert report.is_compliant is False
    uhc_007_errors = [e for e in report.errors if e.code == "UHC_007"]
    assert len(uhc_007_errors) == 1
    assert "transport code" in uhc_007_errors[0].message.lower()


def test_uhc_008_transport_reason_required(valid_claim_data):
    """Test UHC_008: Transport reason required for ambulance claims"""
    valid_claim_data["claim"]["ambulance"] = {
        "transport_code": "A",
        "patient_weight_lbs": 150
        # Missing transport_reason
    }

    validator = UHCBusinessRuleValidator()
    report = validator.validate_claim(valid_claim_data)

    assert report.is_compliant is False
    uhc_008_errors = [e for e in report.errors if e.code == "UHC_008"]
    assert len(uhc_008_errors) == 1
    assert "transport reason" in uhc_008_errors[0].message.lower()


def test_uhc_009_trip_number_tracking(valid_claim_data):
    """Test UHC_009: Trip number recommended for tracking"""
    valid_claim_data["claim"]["ambulance"] = {
        "transport_code": "A",
        "transport_reason": "A"
        # Missing trip_number
    }

    validator = UHCBusinessRuleValidator()
    report = validator.validate_claim(valid_claim_data)

    uhc_009_warnings = [w for w in report.warnings if w.code == "UHC_009"]
    assert len(uhc_009_warnings) == 1
    assert "trip number" in uhc_009_warnings[0].message.lower()


def test_uhc_010_trip_type_validation(valid_claim_data):
    """Test UHC_010: Trip type must be I, R, or B"""
    valid_claim_data["services"][0]["trip_type"] = "X"  # Invalid

    validator = UHCBusinessRuleValidator()
    report = validator.validate_claim(valid_claim_data)

    assert report.is_compliant is False
    uhc_010_errors = [e for e in report.errors if e.code == "UHC_010"]
    assert len(uhc_010_errors) == 1
    assert "trip type" in uhc_010_errors[0].message.lower()


def test_uhc_011_trip_leg_validation(valid_claim_data):
    """Test UHC_011: Trip leg must be A or B"""
    valid_claim_data["services"][0]["trip_leg"] = "X"  # Invalid

    validator = UHCBusinessRuleValidator()
    report = validator.validate_claim(valid_claim_data)

    assert report.is_compliant is False
    uhc_011_errors = [e for e in report.errors if e.code == "UHC_011"]
    assert len(uhc_011_errors) == 1
    assert "trip leg" in uhc_011_errors[0].message.lower()


def test_uhc_012_location_information(valid_claim_data):
    """Test UHC_012: Pickup or dropoff location recommended"""
    # Remove all pickup/dropoff at both claim and service levels
    if "ambulance" in valid_claim_data["claim"]:
        valid_claim_data["claim"]["ambulance"].pop("pickup", None)
        valid_claim_data["claim"]["ambulance"].pop("dropoff", None)

    for svc in valid_claim_data["services"]:
        svc.pop("pickup", None)
        svc.pop("dropoff", None)

    validator = UHCBusinessRuleValidator()
    report = validator.validate_claim(valid_claim_data)

    uhc_012_warnings = [w for w in report.warnings if w.code == "UHC_012"]
    assert len(uhc_012_warnings) > 0
    assert "location" in uhc_012_warnings[0].message.lower()


def test_uhc_013_authorization_required(valid_claim_data):
    """Test UHC_013: Authorization number recommended"""
    # Remove authorization
    if "auth_number" in valid_claim_data["claim"]:
        del valid_claim_data["claim"]["auth_number"]

    validator = UHCBusinessRuleValidator()
    report = validator.validate_claim(valid_claim_data)

    uhc_013_warnings = [w for w in report.warnings if w.code == "UHC_013"]
    assert len(uhc_013_warnings) == 1
    assert "authorization" in uhc_013_warnings[0].message.lower()


def test_uhc_014_patient_account_tracking(valid_claim_data):
    """Test UHC_014: Patient account number helps with tracking"""
    # Remove patient account
    if "patient_account" in valid_claim_data["claim"]:
        del valid_claim_data["claim"]["patient_account"]

    validator = UHCBusinessRuleValidator()
    report = validator.validate_claim(valid_claim_data)

    uhc_014_info = [i for i in report.info if i.code == "UHC_014"]
    assert len(uhc_014_info) == 1
    assert uhc_014_info[0].severity == UHCRuleSeverity.INFO
    assert "patient account" in uhc_014_info[0].message.lower()


def test_multiple_violations_accumulated(valid_claim_data):
    """Test that multiple UHC violations are accumulated in report"""
    # Create multiple violations
    valid_claim_data["claim"]["payment_status"] = "X"  # UHC_002 WARNING
    valid_claim_data["claim"]["ambulance"] = {
        # Missing transport_code and transport_reason - UHC_007, UHC_008 ERRORS
        "patient_weight_lbs": 150
    }
    # Remove auth_number - UHC_013 WARNING
    if "auth_number" in valid_claim_data["claim"]:
        del valid_claim_data["claim"]["auth_number"]

    validator = UHCBusinessRuleValidator()
    report = validator.validate_claim(valid_claim_data)

    assert report.is_compliant is False  # Has errors
    assert len(report.errors) >= 2  # At least UHC_007, UHC_008
    assert len(report.warnings) >= 2  # At least UHC_002, UHC_013


def test_report_string_representation(valid_claim_data):
    """Test UHCReport __str__ method"""
    valid_claim_data["claim"]["ambulance"] = {}  # Missing required fields

    validator = UHCBusinessRuleValidator()
    report = validator.validate_claim(valid_claim_data)

    report_str = str(report)
    assert "FAIL" in report_str or "Error" in report_str
    assert len(report_str) > 0


def test_convenience_function_returns_report(valid_claim_data):
    """Test that validate_uhc_business_rules convenience function works"""
    valid_claim_data["claim"]["ambulance"] = {
        "transport_code": "A",
        "transport_reason": "A"
    }

    report = validate_uhc_business_rules(valid_claim_data)

    assert isinstance(report, UHCReport)


def test_add_violation_updates_is_compliant():
    """Test that adding ERROR violation updates is_compliant to False"""
    report = UHCReport(is_compliant=True)
    assert report.is_compliant is True

    report.add_violation(UHCRuleViolation(
        severity=UHCRuleSeverity.ERROR,
        code="UHC_001",
        message="Test error",
        rule_name="Test Rule"
    ))

    assert report.is_compliant is False
    assert len(report.errors) == 1


def test_add_warning_does_not_update_is_compliant():
    """Test that adding WARNING does not change is_compliant"""
    report = UHCReport(is_compliant=True)

    report.add_violation(UHCRuleViolation(
        severity=UHCRuleSeverity.WARNING,
        code="UHC_002",
        message="Test warning",
        rule_name="Test Rule"
    ))

    assert report.is_compliant is True  # Still compliant
    assert len(report.warnings) == 1


def test_severity_enum_values():
    """Test UHCRuleSeverity enum values"""
    assert UHCRuleSeverity.ERROR.value == "ERROR"
    assert UHCRuleSeverity.WARNING.value == "WARNING"
    assert UHCRuleSeverity.INFO.value == "INFO"


def test_valid_transport_codes(valid_claim_data):
    """Test that all valid transport codes are accepted"""
    valid_claim_data["claim"]["ambulance"] = {
        "transport_reason": "A",
        "patient_weight_lbs": 150
    }

    validator = UHCBusinessRuleValidator()

    for code in ["A", "B", "C", "D", "E"]:
        valid_claim_data["claim"]["ambulance"]["transport_code"] = code
        report = validator.validate_claim(valid_claim_data)

        # Should not have UHC_007 error
        uhc_007_errors = [e for e in report.errors if e.code == "UHC_007"]
        assert len(uhc_007_errors) == 0, f"Transport code {code} should be valid"


def test_valid_transport_reasons(valid_claim_data):
    """Test that all valid transport reasons are accepted"""
    valid_claim_data["claim"]["ambulance"] = {
        "transport_code": "A",
        "patient_weight_lbs": 150
    }

    validator = UHCBusinessRuleValidator()

    for reason in ["A", "B", "C", "D", "DH", "E"]:
        valid_claim_data["claim"]["ambulance"]["transport_reason"] = reason
        report = validator.validate_claim(valid_claim_data)

        # Should not have UHC_008 error
        uhc_008_errors = [e for e in report.errors if e.code == "UHC_008"]
        assert len(uhc_008_errors) == 0, f"Transport reason {reason} should be valid"


def test_valid_trip_types(valid_claim_data):
    """Test that all valid trip types are accepted"""
    validator = UHCBusinessRuleValidator()

    for trip_type in ["I", "R", "B"]:
        valid_claim_data["services"][0]["trip_type"] = trip_type
        report = validator.validate_claim(valid_claim_data)

        # Should not have UHC_010 error
        uhc_010_errors = [e for e in report.errors if e.code == "UHC_010"]
        assert len(uhc_010_errors) == 0, f"Trip type {trip_type} should be valid"


def test_valid_trip_legs(valid_claim_data):
    """Test that all valid trip legs are accepted"""
    validator = UHCBusinessRuleValidator()

    for trip_leg in ["A", "B"]:
        valid_claim_data["services"][0]["trip_leg"] = trip_leg
        report = validator.validate_claim(valid_claim_data)

        # Should not have UHC_011 error
        uhc_011_errors = [e for e in report.errors if e.code == "UHC_011"]
        assert len(uhc_011_errors) == 0, f"Trip leg {trip_leg} should be valid"


def test_valid_payment_status_codes(valid_claim_data):
    """Test that P and D payment status codes are accepted"""
    validator = UHCBusinessRuleValidator()

    for status in ["P", "D"]:
        valid_claim_data["claim"]["payment_status"] = status
        report = validator.validate_claim(valid_claim_data)

        # Should not have UHC_002 warning
        uhc_002_warnings = [w for w in report.warnings if w.code == "UHC_002"]
        assert len(uhc_002_warnings) == 0, f"Payment status {status} should be valid"


def test_location_at_claim_level_satisfies_uhc_012(valid_claim_data):
    """Test that claim-level location satisfies UHC_012"""
    valid_claim_data["claim"]["ambulance"] = {
        "transport_code": "A",
        "transport_reason": "A",
        "pickup": {"addr": "123 Main", "city": "City", "state": "KY", "zip": "40202"}
    }

    # Remove service-level locations
    for svc in valid_claim_data["services"]:
        svc.pop("pickup", None)
        svc.pop("dropoff", None)

    validator = UHCBusinessRuleValidator()
    report = validator.validate_claim(valid_claim_data)

    # Should not have UHC_012 warning
    uhc_012_warnings = [w for w in report.warnings if w.code == "UHC_012"]
    assert len(uhc_012_warnings) == 0


def test_location_at_service_level_satisfies_uhc_012(valid_claim_data):
    """Test that service-level location satisfies UHC_012"""
    valid_claim_data["services"][0]["pickup"] = {
        "addr": "123 Main", "city": "City", "state": "KY", "zip": "40202"
    }

    # Remove claim-level locations
    if "ambulance" in valid_claim_data["claim"]:
        valid_claim_data["claim"]["ambulance"].pop("pickup", None)
        valid_claim_data["claim"]["ambulance"].pop("dropoff", None)

    validator = UHCBusinessRuleValidator()
    report = validator.validate_claim(valid_claim_data)

    # Should not have UHC_012 warning for this service
    uhc_012_warnings = [w for w in report.warnings if w.code == "UHC_012"]
    assert len(uhc_012_warnings) == 0
