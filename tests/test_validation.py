# SPDX-License-Identifier: MIT
"""
Tests for validation functionality
"""
import pytest
from nemt_837p_converter import build_837p_from_json, Config, ValidationError


def test_valid_claim_passes_validation(valid_claim_data):
    """Test that valid claim data passes validation"""
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    # Should not raise ValidationError
    edi = build_837p_from_json(valid_claim_data, cfg)
    assert edi is not None
    assert "ISA" in edi
    assert "GS" in edi


def test_invalid_npi_raises_error(valid_claim_data):
    """Test that invalid NPI raises validation error"""
    valid_claim_data["billing_provider"]["npi"] = "123"
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    with pytest.raises(ValidationError) as exc_info:
        build_837p_from_json(valid_claim_data, cfg)

    assert "npi must be 10 digits" in str(exc_info.value).lower()


def test_invalid_state_raises_error(valid_claim_data):
    """Test that invalid state code raises validation error"""
    valid_claim_data["billing_provider"]["address"]["state"] = "XX"
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    with pytest.raises(ValidationError) as exc_info:
        build_837p_from_json(valid_claim_data, cfg)

    assert "not a valid us state code" in str(exc_info.value).lower()


def test_invalid_zip_raises_error(valid_claim_data):
    """Test that invalid ZIP code raises validation error"""
    valid_claim_data["billing_provider"]["address"]["zip"] = "123"
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    with pytest.raises(ValidationError) as exc_info:
        build_837p_from_json(valid_claim_data, cfg)

    assert ("must be format 12345" in str(exc_info.value) or "not a valid zip code" in str(exc_info.value).lower())


def test_invalid_date_format_raises_error(valid_claim_data):
    """Test that invalid date format raises validation error"""
    valid_claim_data["claim"]["from"] = "01/01/2026"
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    with pytest.raises(ValidationError) as exc_info:
        build_837p_from_json(valid_claim_data, cfg)

    assert ("format yyyy-mm-dd" in str(exc_info.value).lower() or "yyyy-mm-dd format" in str(exc_info.value).lower())


def test_invalid_gender_raises_error(valid_claim_data):
    """Test that invalid gender code raises validation error"""
    valid_claim_data["subscriber"]["sex"] = "Male"
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    with pytest.raises(ValidationError) as exc_info:
        build_837p_from_json(valid_claim_data, cfg)

    assert "not a valid code" in str(exc_info.value).lower()


def test_invalid_pos_raises_error(valid_claim_data):
    """Test that invalid POS code raises validation error"""
    valid_claim_data["claim"]["pos"] = "999"
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    with pytest.raises(ValidationError) as exc_info:
        build_837p_from_json(valid_claim_data, cfg)

    assert "'999' is not a valid code" in str(exc_info.value)


def test_invalid_frequency_code_raises_error(valid_claim_data):
    """Test that invalid frequency code raises validation error"""
    valid_claim_data["claim"]["frequency_code"] = "9"
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    with pytest.raises(ValidationError) as exc_info:
        build_837p_from_json(valid_claim_data, cfg)

    assert "'9' is not a valid code" in str(exc_info.value)


def test_too_many_modifiers_raises_error(valid_claim_data):
    """Test that more than 4 modifiers raises validation error"""
    valid_claim_data["services"][0]["modifiers"] = ["AA", "BB", "CC", "DD", "EE"]
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    with pytest.raises(ValidationError) as exc_info:
        build_837p_from_json(valid_claim_data, cfg)

    assert ("4 modifiers" in str(exc_info.value).lower() or "maximum 4 modifiers" in str(exc_info.value).lower())


def test_missing_required_fields_raises_error(invalid_claim_data):
    """Test that missing required fields raises validation error"""
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    with pytest.raises(ValidationError) as exc_info:
        build_837p_from_json(invalid_claim_data, cfg)

    error_msg = str(exc_info.value).lower()
    assert "npi" in error_msg or "member_id" in error_msg or "clm_number" in error_msg


def test_field_length_validation(valid_claim_data):
    """Test that field length limits are enforced"""
    valid_claim_data["claim"]["clm_number"] = "X" * 100  # Too long
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    with pytest.raises(ValidationError) as exc_info:
        build_837p_from_json(valid_claim_data, cfg)

    assert "30 characters" in str(exc_info.value)
