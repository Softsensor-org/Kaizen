"""Tests for file naming validation per §2.2"""

import pytest
from datetime import datetime
from nemt_837p_converter import validate_filename, generate_filename


def test_valid_production_filename():
    """Test valid production filename format"""
    filename = "INB_KYPROFKZN_01152026_001.dat"
    is_valid, error = validate_filename(filename, is_test=False)
    
    assert is_valid is True
    assert error is None


def test_valid_test_filename():
    """Test valid test filename format"""
    filename = "TEST_INB_ILPROFKZN_01152026_002.dat"
    is_valid, error = validate_filename(filename, is_test=True)
    
    assert is_valid is True
    assert error is None


def test_invalid_missing_prefix():
    """Test invalid filename - missing INB_ prefix"""
    filename = "KYPROFKZN_01152026_001.dat"
    is_valid, error = validate_filename(filename, is_test=False)
    
    assert is_valid is False
    assert "Invalid filename format" in error


def test_invalid_state_code():
    """Test invalid filename - bad state code"""
    filename = "INB_XXPROFKZN_01152026_001.dat"
    is_valid, error = validate_filename(filename, is_test=False)
    
    assert is_valid is False
    assert "Invalid state code" in error


def test_invalid_date_format():
    """Test invalid filename - bad date format"""
    filename = "INB_KYPROFKZN_13352026_001.dat"  # Month 13 doesn't exist
    is_valid, error = validate_filename(filename, is_test=False)
    
    assert is_valid is False
    assert "Invalid date" in error


def test_invalid_sequence_too_short():
    """Test invalid filename - sequence too short"""
    filename = "INB_KYPROFKZN_01152026_01.dat"  # Only 2 digits
    is_valid, error = validate_filename(filename, is_test=False)

    assert is_valid is False
    assert "Invalid filename format" in error  # Rejected by regex pattern


def test_production_with_test_prefix():
    """Test production file incorrectly marked as test"""
    filename = "TEST_INB_KYPROFKZN_01152026_001.dat"
    is_valid, error = validate_filename(filename, is_test=False)  # is_test=False but has TEST_ prefix
    
    assert is_valid is False
    assert "should not have TEST_" in error


def test_test_missing_test_prefix():
    """Test file missing TEST_ prefix"""
    filename = "INB_KYPROFKZN_01152026_001.dat"
    is_valid, error = validate_filename(filename, is_test=True)  # is_test=True but no TEST_ prefix
    
    assert is_valid is False
    assert "must start with TEST_INB_" in error


def test_generate_production_filename():
    """Test generating production filename"""
    date = datetime(2026, 1, 15)
    filename = generate_filename("KY", date, sequence=1, is_test=False)
    
    assert filename == "INB_KYPROFKZN_01152026_001.dat"
    
    # Validate it
    is_valid, error = validate_filename(filename, is_test=False)
    assert is_valid is True


def test_generate_test_filename():
    """Test generating test filename"""
    date = datetime(2026, 1, 15)
    filename = generate_filename("IL", date, sequence=2, is_test=True)
    
    assert filename == "TEST_INB_ILPROFKZN_01152026_002.dat"
    
    # Validate it
    is_valid, error = validate_filename(filename, is_test=True)
    assert is_valid is True


def test_generate_filename_default_date():
    """Test generating filename with default date (today)"""
    filename = generate_filename("NY", sequence=5, is_test=False)
    
    # Should be valid
    is_valid, error = validate_filename(filename, is_test=False)
    assert is_valid is True
    
    # Should contain today's date
    today = datetime.now().strftime("%m%d%Y")
    assert today in filename


def test_generate_filename_zero_pads_sequence():
    """Test that sequence is zero-padded to 3 digits"""
    filename = generate_filename("CA", datetime(2026, 2, 1), sequence=5)
    
    assert "_005.dat" in filename


def test_all_states_valid():
    """Test that all 50 US states are recognized"""
    states = [
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
    ]
    
    date = datetime(2026, 1, 1)
    for state in states:
        filename = generate_filename(state, date, sequence=1)
        is_valid, error = validate_filename(filename, is_test=False)
        assert is_valid is True, f"State {state} should be valid"
