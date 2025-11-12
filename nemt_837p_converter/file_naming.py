"""
File Naming Convention Validator per §2.2

Validates and generates proper file names for Kaizen vendor submissions.
"""

import re
from datetime import datetime
from typing import Optional, Tuple


def validate_filename(filename: str, is_test: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Validate filename against Kaizen vendor requirements per §2.2
    
    Args:
        filename: The filename to validate
        is_test: Whether this is a test file (adds TEST_ prefix)
    
    Returns:
        Tuple of (is_valid, error_message)
        
    Format:
        Production: INB_<GeoState>PROFKZN_mmddyyyy_seq.dat
        Test: TEST_INB_<GeoState>PROFKZN_mmddyyyy_seq.dat
        
    Examples:
        - INB_KYPROFKZN_01152026_001.dat (valid production)
        - TEST_INB_ILPROFKZN_01152026_002.dat (valid test)
    """
    expected_prefix = "TEST_INB_" if is_test else "INB_"

    # Pattern: (TEST_)?INB_<ST>PROFKZN_MMDDYYYY_SEQ.dat
    pattern = r"^(TEST_)?INB_([A-Z]{2})PROFKZN_(\d{8})_(\d{3,})\.dat$"

    match = re.match(pattern, filename, re.IGNORECASE)

    if not match:
        return False, (
            f"Invalid filename format. Expected: {expected_prefix}<GeoState>PROFKZN_mmddyyyy_seq.dat\n"
            f"Example: {expected_prefix}KYPROFKZN_01152026_001.dat"
        )

    # Validate prefix
    has_test_prefix = match.group(1) is not None
    if is_test and not has_test_prefix:
        return False, "Test files must start with TEST_INB_"
    if not is_test and has_test_prefix:
        return False, "Production files should not have TEST_ prefix"
    
    # Validate state code (group 2)
    state = match.group(2).upper()
    valid_states = {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
    }
    if state not in valid_states:
        return False, f"Invalid state code: {state}"
    
    # Validate date format (group 3) - mmddyyyy
    date_str = match.group(3)
    try:
        date = datetime.strptime(date_str, "%m%d%Y")
        # Check if date is reasonable (not in far past or future)
        current_year = datetime.now().year
        if date.year < 2020 or date.year > current_year + 2:
            return False, f"Date year {date.year} seems unreasonable. Expected range: 2020-{current_year + 2}"
    except ValueError:
        return False, f"Invalid date: {date_str}. Expected format: mmddyyyy"
    
    # Validate sequence (group 4) - 3-4 digits
    seq = match.group(4)
    if len(seq) < 3:
        return False, f"Sequence number {seq} must be at least 3 digits (e.g., 001)"
    
    return True, None


def generate_filename(
    state_code: str,
    date: Optional[datetime] = None,
    sequence: int = 1,
    is_test: bool = False
) -> str:
    """
    Generate a properly formatted filename per §2.2
    
    Args:
        state_code: Two-letter state code (e.g., "KY", "IL")
        date: Date for filename (defaults to today)
        sequence: Sequence number (defaults to 1)
        is_test: Whether this is a test file
    
    Returns:
        Properly formatted filename
        
    Example:
        >>> generate_filename("KY", datetime(2026, 1, 15), 1, is_test=False)
        'INB_KYPROFKZN_01152026_001.dat'
    """
    if date is None:
        date = datetime.now()
    
    date_str = date.strftime("%m%d%Y")
    seq_str = f"{sequence:03d}"  # Zero-pad to 3 digits minimum
    state = state_code.upper()
    
    prefix = "TEST_INB_" if is_test else "INB_"
    
    return f"{prefix}{state}PROFKZN_{date_str}_{seq_str}.dat"
