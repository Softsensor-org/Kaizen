"""Tests for loop hierarchy validation"""

import pytest
from nemt_837p_converter import build_837p_from_json, Config, check_edi_compliance
from nemt_837p_converter.payers import get_payer_config


def test_service_level_pickup_dropoff_only(valid_claim_data):
    """Test claim with pickup/dropoff only at service level (2420G/H)"""
    cfg = Config(
        sender_qual="ZZ",
        sender_id="TEST",
        receiver_qual="ZZ",
        receiver_id="RECV",
        usage_indicator="T",
        gs_sender_code="TEST",
        gs_receiver_code="RECV",
        payer_config=get_payer_config("UHC_CS")
    )

    # Add pickup/dropoff at service level only
    claim = valid_claim_data.copy()
    claim["services"][0]["pickup"] = {"addr": "123 Main", "city": "City", "state": "KY", "zip": "40202"}
    claim["services"][0]["dropoff"] = {"addr": "456 Oak", "city": "Town", "state": "KY", "zip": "40203"}

    # Ensure NO claim-level pickup/dropoff
    if "ambulance" in claim["claim"]:
        claim["claim"]["ambulance"].pop("pickup", None)
        claim["claim"]["ambulance"].pop("dropoff", None)

    edi = build_837p_from_json(claim, cfg)
    report = check_edi_compliance(edi)

    # Should have no warnings about duplicate locations
    duplicate_warnings = [w for w in report.warnings if w.code in ("LOOP_002", "LOOP_003")]
    assert len(duplicate_warnings) == 0, "Service-level only should have no duplicate location warnings"


def test_claim_level_pickup_dropoff_only(valid_claim_data):
    """Test claim with pickup/dropoff only at claim level (2310E/F)"""
    cfg = Config(
        sender_qual="ZZ",
        sender_id="TEST",
        receiver_qual="ZZ",
        receiver_id="RECV",
        usage_indicator="T",
        gs_sender_code="TEST",
        gs_receiver_code="RECV",
        payer_config=get_payer_config("UHC_CS")
    )

    # Add pickup/dropoff at claim level only
    claim = valid_claim_data.copy()
    if "ambulance" not in claim["claim"]:
        claim["claim"]["ambulance"] = {}
    claim["claim"]["ambulance"]["pickup"] = {"addr": "123 Main", "city": "City", "state": "KY", "zip": "40202"}
    claim["claim"]["ambulance"]["dropoff"] = {"addr": "456 Oak", "city": "Town", "state": "KY", "zip": "40203"}

    # Ensure NO service-level pickup/dropoff
    for svc in claim["services"]:
        svc.pop("pickup", None)
        svc.pop("dropoff", None)

    edi = build_837p_from_json(claim, cfg)
    report = check_edi_compliance(edi)

    # Should have no warnings about duplicate locations
    duplicate_warnings = [w for w in report.warnings if w.code in ("LOOP_002", "LOOP_003")]
    assert len(duplicate_warnings) == 0, "Claim-level only should have no duplicate location warnings"


def test_both_levels_generates_warnings(valid_claim_data):
    """Test claim with pickup/dropoff at BOTH claim and service levels generates warnings"""
    cfg = Config(
        sender_qual="ZZ",
        sender_id="TEST",
        receiver_qual="ZZ",
        receiver_id="RECV",
        usage_indicator="T",
        gs_sender_code="TEST",
        gs_receiver_code="RECV",
        payer_config=get_payer_config("UHC_CS"),
        use_cr1_locations=False  # Use legacy NTE mode to test duplicate loop detection
    )

    # Add pickup/dropoff at BOTH levels
    claim = valid_claim_data.copy()

    # Claim level
    if "ambulance" not in claim["claim"]:
        claim["claim"]["ambulance"] = {}
    claim["claim"]["ambulance"]["pickup"] = {"addr": "Claim Pickup", "city": "City1", "state": "KY", "zip": "40201"}
    claim["claim"]["ambulance"]["dropoff"] = {"addr": "Claim Dropoff", "city": "City2", "state": "KY", "zip": "40202"}

    # Service level
    claim["services"][0]["pickup"] = {"addr": "Service Pickup", "city": "City3", "state": "KY", "zip": "40203"}
    claim["services"][0]["dropoff"] = {"addr": "Service Dropoff", "city": "City4", "state": "KY", "zip": "40204"}

    edi = build_837p_from_json(claim, cfg)
    report = check_edi_compliance(edi)

    # Should have warnings about duplicate locations
    duplicate_warnings = [w for w in report.warnings if w.code in ("LOOP_002", "LOOP_003")]
    assert len(duplicate_warnings) > 0, "Both levels should generate duplicate location warnings"

    # Should have both pickup and dropoff warnings
    pickup_warning = any(w.code == "LOOP_002" for w in duplicate_warnings)
    dropoff_warning = any(w.code == "LOOP_003" for w in duplicate_warnings)
    assert pickup_warning, "Should have warning for duplicate pickup (LOOP_002)"
    assert dropoff_warning, "Should have warning for duplicate dropoff (LOOP_003)"


def test_claim_level_supervising_provider(valid_claim_data):
    """Test supervising provider at claim level (2310D)"""
    cfg = Config(
        sender_qual="ZZ",
        sender_id="TEST",
        receiver_qual="ZZ",
        receiver_id="RECV",
        usage_indicator="T",
        gs_sender_code="TEST",
        gs_receiver_code="RECV",
        payer_config=get_payer_config("UHC_CS")
    )

    claim = valid_claim_data.copy()
    claim["claim"]["supervising_provider"] = {"last": "Smith", "first": "John"}

    # Remove service-level supervising provider
    for svc in claim["services"]:
        svc.pop("supervising_provider", None)

    edi = build_837p_from_json(claim, cfg)

    # Should contain NM1*DQ before first LX
    segments = edi.split("~")
    clm_idx = next((i for i, s in enumerate(segments) if s.startswith("CLM*")), None)
    lx_idx = next((i for i, s in enumerate(segments) if s.startswith("LX*")), None)

    assert clm_idx is not None, "Should have CLM segment"
    assert lx_idx is not None, "Should have LX segment"

    # Find NM1*DQ between CLM and LX (claim-level supervising provider - 2310D)
    nm1_dq_segments = [i for i, s in enumerate(segments) if s.startswith("NM1*DQ*") and clm_idx < i < lx_idx]
    assert len(nm1_dq_segments) > 0, "Should have NM1*DQ at claim level (2310D)"


def test_service_level_supervising_provider(valid_claim_data):
    """Test supervising provider at service level (2420D)"""
    cfg = Config(
        sender_qual="ZZ",
        sender_id="TEST",
        receiver_qual="ZZ",
        receiver_id="RECV",
        usage_indicator="T",
        gs_sender_code="TEST",
        gs_receiver_code="RECV",
        payer_config=get_payer_config("UHC_CS")
    )

    claim = valid_claim_data.copy()

    # Remove claim-level supervising provider
    if "supervising_provider" in claim["claim"]:
        claim["claim"].pop("supervising_provider")

    # Add service-level supervising provider
    claim["services"][0]["supervising_provider"] = {"last": "Jones", "first": "Jane"}

    edi = build_837p_from_json(claim, cfg)

    # Should contain NM1*DQ after first LX
    segments = edi.split("~")
    lx_idx = next((i for i, s in enumerate(segments) if s.startswith("LX*")), None)

    assert lx_idx is not None, "Should have LX segment"

    # Find NM1*DQ after LX (service-level supervising provider - 2420D)
    nm1_dq_segments = [i for i, s in enumerate(segments) if s.startswith("NM1*DQ*") and i > lx_idx]
    assert len(nm1_dq_segments) > 0, "Should have NM1*DQ at service level (2420D)"


def test_k3_before_provider_loops(valid_claim_data):
    """Test K3 segment appears before NM1 provider loops in service line"""
    cfg = Config(
        sender_qual="ZZ",
        sender_id="TEST",
        receiver_qual="ZZ",
        receiver_id="RECV",
        usage_indicator="T",
        gs_sender_code="TEST",
        gs_receiver_code="RECV",
        payer_config=get_payer_config("UHC_CS")
    )

    claim = valid_claim_data.copy()
    claim["services"][0]["payment_status"] = "P"
    claim["services"][0]["supervising_provider"] = {"last": "Smith", "first": "John"}

    edi = build_837p_from_json(claim, cfg)
    report = check_edi_compliance(edi)

    # Should have no errors about K3 ordering
    k3_errors = [e for e in report.errors if e.code == "ORDER_001"]
    assert len(k3_errors) == 0, "K3 should be before NM1 provider loops"

    # Verify positioning in EDI
    segments = edi.split("~")
    lx_indices = [i for i, s in enumerate(segments) if s.startswith("LX*")]

    for lx_idx in lx_indices:
        # Find next LX or end
        next_lx = next((i for i in lx_indices if i > lx_idx), len(segments))

        # Find K3 and NM1 in this service line
        k3_indices = [i for i, s in enumerate(segments) if s.startswith("K3*") and lx_idx < i < next_lx]
        nm1_indices = [i for i, s in enumerate(segments) if s.startswith("NM1*") and lx_idx < i < next_lx]

        if k3_indices and nm1_indices:
            first_k3 = min(k3_indices)
            first_nm1 = min(nm1_indices)
            assert first_k3 < first_nm1, f"K3 at {first_k3} should be before NM1 at {first_nm1}"


def test_loop_2400_segments_before_2420(valid_claim_data):
    """Test that 2400 level segments (SV1, DTP, NTE, K3) appear before 2420 provider loops"""
    cfg = Config(
        sender_qual="ZZ",
        sender_id="TEST",
        receiver_qual="ZZ",
        receiver_id="RECV",
        usage_indicator="T",
        gs_sender_code="TEST",
        gs_receiver_code="RECV",
        payer_config=get_payer_config("UHC_CS")
    )

    claim = valid_claim_data.copy()
    claim["services"][0]["payment_status"] = "P"
    claim["services"][0]["pickup"] = {"addr": "123 Main", "city": "City", "state": "KY", "zip": "40202"}

    edi = build_837p_from_json(claim, cfg)
    segments = edi.split("~")

    lx_idx = next((i for i, s in enumerate(segments) if s.startswith("LX*")), None)
    assert lx_idx is not None

    # Find indices of key segments after LX
    sv1_idx = next((i for i, s in enumerate(segments) if s.startswith("SV1*") and i > lx_idx), None)
    k3_idx = next((i for i, s in enumerate(segments) if s.startswith("K3*") and i > lx_idx), None)
    nm1_pw_idx = next((i for i, s in enumerate(segments) if s.startswith("NM1*PW*") and i > lx_idx), None)

    assert sv1_idx is not None, "Should have SV1 segment"

    # If K3 exists, it should be before any NM1
    if k3_idx and nm1_pw_idx:
        assert k3_idx < nm1_pw_idx, "K3 (2400 level) should be before NM1*PW (2420 level)"


def test_loop_2420_before_2430(valid_claim_data):
    """Test that 2420 provider loops appear before 2430 adjudication"""
    cfg = Config(
        sender_qual="ZZ",
        sender_id="TEST",
        receiver_qual="ZZ",
        receiver_id="RECV",
        usage_indicator="T",
        gs_sender_code="TEST",
        gs_receiver_code="RECV",
        payer_config=get_payer_config("UHC_CS")
    )

    claim = valid_claim_data.copy()
    claim["services"][0]["pickup"] = {"addr": "123 Main", "city": "City", "state": "KY", "zip": "40202"}
    claim["services"][0]["adjudication"] = [
        {"paid_amount": 50.00, "paid_units": 1, "cas": [{"group": "CO", "reason": "97", "amount": 10.00}]}
    ]

    edi = build_837p_from_json(claim, cfg)
    segments = edi.split("~")

    lx_idx = next((i for i, s in enumerate(segments) if s.startswith("LX*")), None)
    nm1_pw_idx = next((i for i, s in enumerate(segments) if s.startswith("NM1*PW*") and i > lx_idx), None)
    svd_idx = next((i for i, s in enumerate(segments) if s.startswith("SVD*") and i > lx_idx), None)

    if nm1_pw_idx and svd_idx:
        assert nm1_pw_idx < svd_idx, "NM1*PW (2420) should be before SVD (2430)"


def test_multiple_service_lines_hierarchy(valid_claim_data):
    """Test loop hierarchy with multiple service lines"""
    cfg = Config(
        sender_qual="ZZ",
        sender_id="TEST",
        receiver_qual="ZZ",
        receiver_id="RECV",
        usage_indicator="T",
        gs_sender_code="TEST",
        gs_receiver_code="RECV",
        payer_config=get_payer_config("UHC_CS")
    )

    claim = valid_claim_data.copy()

    # Add second service
    claim["services"].append({
        "hcpcs": "A0200",
        "modifiers": ["EH"],
        "charge": 25.00,
        "units": 10,
        "payment_status": "P",
        "pickup": {"addr": "456 Oak", "city": "Town", "state": "KY", "zip": "40203"},
        "dropoff": {"addr": "789 Elm", "city": "Village", "state": "KY", "zip": "40204"}
    })

    edi = build_837p_from_json(claim, cfg)
    segments = edi.split("~")

    # Should have 2 LX segments
    lx_indices = [i for i, s in enumerate(segments) if s.startswith("LX*")]
    assert len(lx_indices) == 2, "Should have 2 service lines"

    # Each service should have its own provider loops
    for lx_idx in lx_indices:
        next_lx = next((i for i in lx_indices if i > lx_idx), len(segments))

        # Check for SV1 in this service line
        sv1_count = sum(1 for i, s in enumerate(segments) if s.startswith("SV1*") and lx_idx < i < next_lx)
        assert sv1_count == 1, f"Each service line should have exactly 1 SV1 segment"


def test_loop_hierarchy_with_all_providers(valid_claim_data):
    """Test complete loop hierarchy with supervising, pickup, and dropoff providers"""
    cfg = Config(
        sender_qual="ZZ",
        sender_id="TEST",
        receiver_qual="ZZ",
        receiver_id="RECV",
        usage_indicator="T",
        gs_sender_code="TEST",
        gs_receiver_code="RECV",
        payer_config=get_payer_config("UHC_CS")
    )

    claim = valid_claim_data.copy()
    claim["services"][0]["supervising_provider"] = {"last": "Smith", "first": "John"}
    claim["services"][0]["pickup"] = {"addr": "123 Main", "city": "City", "state": "KY", "zip": "40202"}
    claim["services"][0]["dropoff"] = {"addr": "456 Oak", "city": "Town", "state": "KY", "zip": "40203"}
    claim["services"][0]["payment_status"] = "P"

    edi = build_837p_from_json(claim, cfg)
    segments = edi.split("~")

    lx_idx = next((i for i, s in enumerate(segments) if s.startswith("LX*")), None)

    # Find all provider segments after LX
    after_lx = [s for i, s in enumerate(segments) if i > lx_idx]

    # Should have supervising (DQ), pickup (PW), and dropoff (45)
    has_supervising = any(s.startswith("NM1*DQ*") for s in after_lx)
    has_pickup = any(s.startswith("NM1*PW*") for s in after_lx)
    has_dropoff = any(s.startswith("NM1*45*") for s in after_lx)

    assert has_supervising, "Should have supervising provider (2420D)"
    assert has_pickup, "Should have pickup location (2420G)"
    assert has_dropoff, "Should have dropoff location (2420H)"
