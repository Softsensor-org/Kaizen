# SPDX-License-Identifier: MIT
"""
Tests for EDI builder functionality
"""
import pytest
from nemt_837p_converter import build_837p_from_json, Config
from nemt_837p_converter import get_payer_config


def test_build_generates_valid_edi_structure(valid_claim_data):
    """Test that EDI generation creates proper segment structure"""
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    edi = build_837p_from_json(valid_claim_data, cfg)

    # Check required segments exist
    assert edi.startswith("ISA")
    assert "GS*HC" in edi
    assert "ST*837" in edi
    assert "BHT*0019" in edi
    assert "CLM*" in edi
    assert "SE*" in edi
    assert "GE*" in edi
    assert edi.endswith("IEA*1*000000001~")


def test_original_claim_has_frequency_1(valid_claim_data):
    """Test that original claim has frequency code 1"""
    valid_claim_data["claim"]["frequency_code"] = "1"
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    edi = build_837p_from_json(valid_claim_data, cfg)

    # CLM05-3 should be 1
    assert "41:B:1*" in edi or "41 B 1*" in edi


def test_replacement_claim_has_frequency_7(replacement_claim_data):
    """Test that replacement claim has frequency code 7"""
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    edi = build_837p_from_json(replacement_claim_data, cfg)

    # CLM05-3 should be 7
    assert "41:B:7*" in edi or "41 B 7*" in edi


def test_void_claim_has_frequency_8(void_claim_data):
    """Test that void claim has frequency code 8"""
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    edi = build_837p_from_json(void_claim_data, cfg)

    # CLM05-3 should be 8
    assert "41:B:8*" in edi or "41 B 8*" in edi


def test_payer_config_in_edi(valid_claim_data):
    """Test that payer configuration is used in EDI"""
    payer_config = get_payer_config(payer_key="UHC_CS")
    cfg = Config(
        sender_id="TEST",
        receiver_id="TEST",
        gs_sender_code="TEST",
        gs_receiver_code="TEST",
        payer_config=payer_config
    )

    edi = build_837p_from_json(valid_claim_data, cfg)

    # Should contain payer ID and name
    assert "87726" in edi
    assert "UNITED HEALTHCARE COMMUNITY" in edi


def test_cr1_segment_proper_format(valid_claim_data):
    """Test that CR1 segment has proper format (not invalid CR109/CR110)"""
    valid_claim_data["claim"]["ambulance"] = {
        "weight_unit": "LB",
        "patient_weight_lbs": 165,
        "transport_code": "A",
        "transport_reason": "DH"
    }
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    edi = build_837p_from_json(valid_claim_data, cfg)

    # Should have proper CR1 segment
    assert "CR1*LB*165***A*DH" in edi


def test_trip_details_in_nte_not_cr1(valid_claim_data):
    """Test that trip details are in NTE segments, not CR1"""
    valid_claim_data["claim"]["ambulance"] = {
        "trip_number": 123,
        "special_needs": False
    }
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    edi = build_837p_from_json(valid_claim_data, cfg)

    # Trip details should be in NTE segments
    assert "NTE*ADD*TRIPNUM-" in edi
    assert "SPECNEED-" in edi


def test_service_level_nte_segments(valid_claim_data):
    """Test that service-level trip details are in NTE segments"""
    valid_claim_data["services"][0].update({
        "trip_type": "I",
        "trip_leg": "A",
        "pickup_loc_code": "RE",
        "pickup_time": "1100"
    })
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    edi = build_837p_from_json(valid_claim_data, cfg)

    # Service-level details in NTE
    assert "NTE*ADD*PULOC-RE" in edi
    assert "PUTIME-1100" in edi
    assert "TRIPTYPE-I" in edi
    assert "TRIPLEG-A" in edi


def test_k3_segments_present(valid_claim_data):
    """Test that custom K3 segments are generated"""
    valid_claim_data["claim"]["payment_status"] = "P"
    valid_claim_data["claim"]["rendering_network_indicator"] = "I"
    valid_claim_data["claim"]["submission_channel"] = "ELECTRONIC"
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    edi = build_837p_from_json(valid_claim_data, cfg)

    assert "K3*PYMS-P" in edi
    assert "K3*SNWK-I" in edi
    assert "K3*TRPN-ASPUFEELEC" in edi


def test_member_group_in_nte(valid_claim_data):
    """Test that member group structure is in NTE segment"""
    valid_claim_data["claim"]["member_group"] = {
        "group_id": "GRP001",
        "sub_group_id": "SUB001",
        "class_id": "CLS001",
        "plan_id": "PLN001",
        "product_id": "PRD001"
    }
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    edi = build_837p_from_json(valid_claim_data, cfg)

    assert "NTE*ADD*GRP-GRP001" in edi
    assert "SGR-SUB001" in edi
    assert "CLS-CLS001" in edi
    assert "PLN-PLN001" in edi
    assert "PRD-PRD001" in edi


def test_example_claim_generates_valid_edi(example_claim_data):
    """Test that example claim from examples/claim_kaizen.json generates valid EDI"""
    if example_claim_data is None:
        pytest.skip("Example claim file not found")

    cfg = Config(
        sender_id="KAIZENKZN01",
        receiver_id="030240928",
        gs_sender_code="KAIZENKZN01",
        gs_receiver_code="030240928"
    )

    edi = build_837p_from_json(example_claim_data, cfg)

    # Basic structure checks
    assert edi.startswith("ISA")
    assert "ST*837" in edi
    assert "CLM*" in edi
    assert edi.endswith("~")
