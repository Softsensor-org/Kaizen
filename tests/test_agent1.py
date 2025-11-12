"""
Tests for Agent 1: Pre-Submission Validator

Tests the PreSubmissionValidator class independently with direct ValidationReport testing.
"""

import pytest
from nemt_837p_converter import (
    PreSubmissionValidator, validate_claim_json,
    ValidationReport, ValidationIssue, ValidationSeverity
)


def test_valid_claim_returns_valid_report(valid_claim_data):
    """Test that valid claim data returns is_valid=True report"""
    validator = PreSubmissionValidator()
    report = validator.validate_claim(valid_claim_data)

    assert isinstance(report, ValidationReport)
    assert report.is_valid is True
    assert len(report.errors) == 0


def test_validation_report_structure():
    """Test ValidationReport dataclass structure"""
    report = ValidationReport(is_valid=True)

    assert hasattr(report, 'is_valid')
    assert hasattr(report, 'errors')
    assert hasattr(report, 'warnings')
    assert hasattr(report, 'info')
    assert report.errors == []
    assert report.warnings == []
    assert report.info == []


def test_validation_issue_structure():
    """Test ValidationIssue dataclass structure"""
    issue = ValidationIssue(
        severity=ValidationSeverity.ERROR,
        field_path="test.field",
        message="Test message",
        code="TEST_001"
    )

    assert issue.severity == ValidationSeverity.ERROR
    assert issue.field_path == "test.field"
    assert issue.message == "Test message"
    assert issue.code == "TEST_001"


def test_invalid_npi_creates_error(valid_claim_data):
    """Test that invalid NPI creates ERROR severity issue"""
    valid_claim_data["billing_provider"]["npi"] = "123"

    validator = PreSubmissionValidator()
    report = validator.validate_claim(valid_claim_data)

    assert report.is_valid is False
    assert len(report.errors) > 0

    # Find NPI error
    npi_errors = [e for e in report.errors if "npi" in e.field_path.lower()]
    assert len(npi_errors) > 0
    assert npi_errors[0].severity == ValidationSeverity.ERROR
    assert "10 digits" in npi_errors[0].message.lower()


def test_invalid_state_creates_error(valid_claim_data):
    """Test that invalid state code creates ERROR"""
    valid_claim_data["billing_provider"]["address"]["state"] = "XX"

    validator = PreSubmissionValidator()
    report = validator.validate_claim(valid_claim_data)

    assert report.is_valid is False
    state_errors = [e for e in report.errors if "state" in e.field_path.lower()]
    assert len(state_errors) > 0
    assert state_errors[0].severity == ValidationSeverity.ERROR


def test_invalid_zip_creates_error(valid_claim_data):
    """Test that invalid ZIP code creates ERROR"""
    valid_claim_data["billing_provider"]["address"]["zip"] = "123"

    validator = PreSubmissionValidator()
    report = validator.validate_claim(valid_claim_data)

    assert report.is_valid is False
    zip_errors = [e for e in report.errors if "zip" in e.field_path.lower()]
    assert len(zip_errors) > 0
    assert zip_errors[0].severity == ValidationSeverity.ERROR


def test_invalid_date_format_creates_error(valid_claim_data):
    """Test that invalid date format creates ERROR"""
    valid_claim_data["claim"]["from"] = "01/01/2026"

    validator = PreSubmissionValidator()
    report = validator.validate_claim(valid_claim_data)

    assert report.is_valid is False
    date_errors = [e for e in report.errors if "from" in e.field_path.lower()]
    assert len(date_errors) > 0
    assert "yyyy-mm-dd" in date_errors[0].message.lower()


def test_invalid_gender_creates_error(valid_claim_data):
    """Test that invalid gender code creates ERROR"""
    valid_claim_data["subscriber"]["sex"] = "Male"

    validator = PreSubmissionValidator()
    report = validator.validate_claim(valid_claim_data)

    assert report.is_valid is False
    gender_errors = [e for e in report.errors if "sex" in e.field_path.lower()]
    assert len(gender_errors) > 0


def test_invalid_pos_creates_error(valid_claim_data):
    """Test that invalid POS code creates ERROR"""
    valid_claim_data["claim"]["pos"] = "999"

    validator = PreSubmissionValidator()
    report = validator.validate_claim(valid_claim_data)

    assert report.is_valid is False
    pos_errors = [e for e in report.errors if "pos" in e.field_path.lower()]
    assert len(pos_errors) > 0


def test_invalid_frequency_code_creates_error(valid_claim_data):
    """Test that invalid frequency code creates ERROR"""
    valid_claim_data["claim"]["frequency_code"] = "9"

    validator = PreSubmissionValidator()
    report = validator.validate_claim(valid_claim_data)

    assert report.is_valid is False
    freq_errors = [e for e in report.errors if "frequency_code" in e.field_path.lower()]
    assert len(freq_errors) > 0


def test_too_many_modifiers_creates_error(valid_claim_data):
    """Test that more than 4 modifiers creates ERROR"""
    valid_claim_data["services"][0]["modifiers"] = ["AA", "BB", "CC", "DD", "EE"]

    validator = PreSubmissionValidator()
    report = validator.validate_claim(valid_claim_data)

    assert report.is_valid is False
    mod_errors = [e for e in report.errors if "modifiers" in e.field_path.lower()]
    assert len(mod_errors) > 0
    assert "4 modifiers" in mod_errors[0].message.lower()


def test_claim_total_mismatch_creates_warning(valid_claim_data):
    """Test that claim total mismatch with service sum creates WARNING"""
    valid_claim_data["claim"]["total_charge"] = 999.99
    # Services total to 100.00, claim says 999.99

    validator = PreSubmissionValidator()
    report = validator.validate_claim(valid_claim_data)

    # This creates WARNING, not ERROR, so is_valid remains True
    assert report.is_valid is True
    assert len(report.warnings) > 0
    total_warnings = [w for w in report.warnings if "total_charge" in w.field_path.lower()]
    assert len(total_warnings) > 0
    assert "does not match" in total_warnings[0].message.lower()


def test_missing_required_billing_provider_fields(valid_claim_data):
    """Test that missing required billing provider fields creates ERRORS"""
    valid_claim_data["billing_provider"]["npi"] = ""

    validator = PreSubmissionValidator()
    report = validator.validate_claim(valid_claim_data)

    assert report.is_valid is False
    npi_errors = [e for e in report.errors if "npi" in e.field_path.lower()]
    assert len(npi_errors) > 0


def test_missing_required_subscriber_fields(valid_claim_data):
    """Test that missing required subscriber fields creates ERRORS"""
    valid_claim_data["subscriber"]["member_id"] = ""
    valid_claim_data["subscriber"]["name"]["last"] = ""

    validator = PreSubmissionValidator()
    report = validator.validate_claim(valid_claim_data)

    assert report.is_valid is False
    assert len(report.errors) >= 2  # member_id and name.last


def test_missing_required_claim_fields(valid_claim_data):
    """Test that missing required claim fields creates ERRORS"""
    valid_claim_data["claim"]["clm_number"] = ""
    valid_claim_data["claim"]["from"] = ""

    validator = PreSubmissionValidator()
    report = validator.validate_claim(valid_claim_data)

    assert report.is_valid is False
    assert len(report.errors) >= 2


def test_missing_required_service_fields(valid_claim_data):
    """Test that missing required service fields creates ERRORS"""
    valid_claim_data["services"][0]["hcpcs"] = ""
    del valid_claim_data["services"][0]["charge"]  # Remove charge entirely

    validator = PreSubmissionValidator()
    report = validator.validate_claim(valid_claim_data)

    assert report.is_valid is False
    assert len(report.errors) >= 2  # hcpcs and charge


def test_field_length_validation(valid_claim_data):
    """Test that field length limits are enforced"""
    valid_claim_data["claim"]["clm_number"] = "X" * 100  # Too long

    validator = PreSubmissionValidator()
    report = validator.validate_claim(valid_claim_data)

    assert report.is_valid is False
    length_errors = [e for e in report.errors if "clm_number" in e.field_path.lower()]
    assert len(length_errors) > 0
    assert "30 characters" in length_errors[0].message


def test_multiple_errors_accumulated(valid_claim_data):
    """Test that multiple validation errors are accumulated in report"""
    valid_claim_data["billing_provider"]["npi"] = "123"  # Invalid NPI
    valid_claim_data["subscriber"]["sex"] = "Male"  # Invalid gender
    valid_claim_data["claim"]["pos"] = "999"  # Invalid POS

    validator = PreSubmissionValidator()
    report = validator.validate_claim(valid_claim_data)

    assert report.is_valid is False
    assert len(report.errors) >= 3  # At least these 3 errors


def test_report_string_representation(valid_claim_data):
    """Test ValidationReport __str__ method"""
    valid_claim_data["billing_provider"]["npi"] = "123"

    validator = PreSubmissionValidator()
    report = validator.validate_claim(valid_claim_data)

    report_str = str(report)
    assert "FAIL" in report_str or "Error" in report_str
    assert len(report_str) > 0


def test_convenience_function_returns_report(valid_claim_data):
    """Test that validate_claim_json convenience function returns ValidationReport"""
    report = validate_claim_json(valid_claim_data)

    assert isinstance(report, ValidationReport)
    assert report.is_valid is True


def test_valid_zip_formats(valid_claim_data):
    """Test that both 5-digit and 9-digit ZIP codes are accepted"""
    # Test 5-digit
    valid_claim_data["billing_provider"]["address"]["zip"] = "12345"
    validator = PreSubmissionValidator()
    report = validator.validate_claim(valid_claim_data)
    assert report.is_valid is True

    # Test 9-digit
    valid_claim_data["billing_provider"]["address"]["zip"] = "12345-6789"
    report = validator.validate_claim(valid_claim_data)
    assert report.is_valid is True


def test_valid_gender_codes(valid_claim_data):
    """Test that all valid gender codes are accepted"""
    validator = PreSubmissionValidator()

    for gender in ["M", "F", "U"]:
        valid_claim_data["subscriber"]["sex"] = gender
        report = validator.validate_claim(valid_claim_data)
        assert report.is_valid is True, f"Gender {gender} should be valid"


def test_valid_pos_codes(valid_claim_data):
    """Test that common POS codes are accepted"""
    validator = PreSubmissionValidator()

    for pos in ["11", "12", "21", "22", "41"]:
        valid_claim_data["claim"]["pos"] = pos
        report = validator.validate_claim(valid_claim_data)
        assert report.is_valid is True, f"POS {pos} should be valid"


def test_valid_frequency_codes(valid_claim_data):
    """Test that all valid frequency codes are accepted"""
    validator = PreSubmissionValidator()

    # Valid frequency codes are 1, 6, 7, 8
    for freq in ["1", "6", "7", "8"]:
        valid_claim_data["claim"]["frequency_code"] = freq
        # Per §2.1.6, frequency 7 and 8 require original_claim_number
        if freq in ("7", "8"):
            valid_claim_data["claim"]["original_claim_number"] = "ORIG-001"
        else:
            valid_claim_data["claim"].pop("original_claim_number", None)
        report = validator.validate_claim(valid_claim_data)
        assert report.is_valid is True, f"Frequency code {freq} should be valid"


def test_empty_services_list_creates_error(valid_claim_data):
    """Test that empty services list creates ERROR"""
    valid_claim_data["services"] = []

    validator = PreSubmissionValidator()
    report = validator.validate_claim(valid_claim_data)

    assert report.is_valid is False
    svc_errors = [e for e in report.errors if "services" in e.field_path.lower()]
    assert len(svc_errors) > 0


def test_add_issue_updates_is_valid(valid_claim_data):
    """Test that adding ERROR issue updates is_valid to False"""
    report = ValidationReport(is_valid=True)
    assert report.is_valid is True

    report.add_issue(ValidationIssue(
        severity=ValidationSeverity.ERROR,
        field_path="test",
        message="Test error",
        code="TEST_001"
    ))

    assert report.is_valid is False
    assert len(report.errors) == 1


def test_add_warning_does_not_update_is_valid():
    """Test that adding WARNING does not change is_valid"""
    report = ValidationReport(is_valid=True)

    report.add_issue(ValidationIssue(
        severity=ValidationSeverity.WARNING,
        field_path="test",
        message="Test warning",
        code="TEST_002"
    ))

    assert report.is_valid is True  # Still valid
    assert len(report.warnings) == 1


def test_severity_enum_values():
    """Test ValidationSeverity enum values"""
    assert ValidationSeverity.ERROR.value == "ERROR"
    assert ValidationSeverity.WARNING.value == "WARNING"
    assert ValidationSeverity.INFO.value == "INFO"
