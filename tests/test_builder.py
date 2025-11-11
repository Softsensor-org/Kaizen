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

    # Should have proper CR1 segment (updated format with extra field for trip number)
    assert "CR1*LB*165****A*DH" in edi


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


def test_trip_number_zero_padding(valid_claim_data):
    """T036: Test that trip numbers are zero-padded to 9 digits per Kaizen requirements"""
    valid_claim_data["claim"]["ambulance"] = {
        "trip_number": 123,  # Should become 000000123
        "patient_weight_lbs": 150,
        "weight_unit": "LB",
        "transport_code": "A",
        "transport_reason": "DH"
    }
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    edi = build_837p_from_json(valid_claim_data, cfg)

    # Check CR1 segment has zero-padded trip number
    assert "CR1*LB*150****A*DH*000000123~" in edi

    # Check NTE segment also has zero-padded trip number
    assert "TRIPNUM-000000123" in edi


def test_driver_license_rendering_provider(valid_claim_data):
    """T035a: Test REF*0B segment for rendering provider driver's license"""
    valid_claim_data["rendering_provider"] = {
        "npi": "1234567890",
        "last": "Smith",
        "first": "John",
        "driver_license": "DL123456789"
    }
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    edi = build_837p_from_json(valid_claim_data, cfg)

    # Check rendering provider NM1 and REF*0B segments
    assert "NM1*82*1*Smith*John****XX*1234567890~" in edi
    assert "REF*0B*DL123456789~" in edi


def test_driver_license_supervising_provider_claim_level(valid_claim_data):
    """T035b: Test REF*0B segment for supervising provider driver's license (claim level)"""
    valid_claim_data["claim"]["supervising_provider"] = {
        "npi": "9876543210",
        "last": "Johnson",
        "first": "Mary",
        "driver_license": "DL987654321"
    }
    valid_claim_data["claim"]["ambulance"] = {"trip_number": 1}
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    edi = build_837p_from_json(valid_claim_data, cfg)

    # Check supervising provider NM1 and REF*0B segments
    assert "NM1*DQ*1*Johnson*Mary****XX*9876543210~" in edi
    assert "REF*0B*DL987654321~" in edi


def test_driver_license_supervising_provider_service_level(valid_claim_data):
    """T035c: Test REF*0B segment for supervising provider driver's license (service level)"""
    valid_claim_data["services"][0]["supervising_provider"] = {
        "npi": "1112223334",
        "last": "Davis",
        "first": "Robert",
        "driver_license": "DL111222333"
    }
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    edi = build_837p_from_json(valid_claim_data, cfg)

    # Check service-level supervising provider NM1 and REF*0B segments
    assert "NM1*DQ*1*Davis*Robert****XX*1112223334~" in edi
    assert "REF*0B*DL111222333~" in edi


def test_date_tracking_k3_segments(valid_claim_data):
    """T032: Test K3 segments with DREC/DADJ/PAIDDT date tracking"""
    valid_claim_data["claim"]["receipt_date"] = "2025-01-15"
    valid_claim_data["claim"]["adjudication_date"] = "2025-01-20"
    valid_claim_data["claim"]["paid_date"] = "2025-01-22"
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    edi = build_837p_from_json(valid_claim_data, cfg)

    # Check K3 segment with date tracking
    assert "K3*DREC-20250115;DADJ-20250120;PAIDDT-20250122~" in edi


def test_provider_address_k3_segments(valid_claim_data):
    """T033: Test K3 segments with rendering provider address"""
    valid_claim_data["rendering_provider"] = {
        "npi": "1234567890",
        "last": "Smith",
        "first": "John",
        "address_line1": "123 Main Street",
        "address_line2": "Suite 100",
        "city": "Louisville",
        "state": "KY",
        "zip": "40202"
    }
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    edi = build_837p_from_json(valid_claim_data, cfg)

    # Check K3 segments with provider address
    assert "K3*AL1-123 Main Street;AL2-Suite 100~" in edi
    assert "K3*CY-Louisville;ST-KY;ZIP-40202~" in edi


def test_provider_address_k3_segments_partial(valid_claim_data):
    """T033b: Test K3 segments with partial rendering provider address (no address_line2)"""
    valid_claim_data["rendering_provider"] = {
        "npi": "1234567890",
        "last": "Smith",
        "first": "John",
        "address_line1": "456 Oak Avenue",
        "city": "Lexington",
        "state": "KY",
        "zip": "40507"
    }
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    edi = build_837p_from_json(valid_claim_data, cfg)

    # Check K3 segments with provider address (only AL1, no AL2)
    assert "K3*AL1-456 Oak Avenue~" in edi
    assert "K3*CY-Lexington;ST-KY;ZIP-40507~" in edi


def test_atypical_provider_without_npi(valid_claim_data):
    """Test rendering provider with atypical ID but no NPI"""
    valid_claim_data["rendering_provider"] = {
        "last": "Brown",
        "first": "Alice",
        "atypical_id": "STATE123456",
        "driver_license": "DL456789012"
    }
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    edi = build_837p_from_json(valid_claim_data, cfg)

    # Check rendering provider NM1 without NPI qualifier
    assert "NM1*82*1*Brown*Alice~" in edi
    # Check REF*G2 for atypical provider ID
    assert "REF*G2*STATE123456~" in edi
    # Check REF*0B for driver's license
    assert "REF*0B*DL456789012~" in edi


def test_all_kaizen_enhancements_together(valid_claim_data):
    """Integration test: All Kaizen enhancements in one claim"""
    valid_claim_data["claim"]["receipt_date"] = "2025-01-10"
    valid_claim_data["claim"]["adjudication_date"] = "2025-01-15"
    valid_claim_data["claim"]["paid_date"] = "2025-01-18"
    valid_claim_data["claim"]["ambulance"] = {
        "trip_number": 42,
        "patient_weight_lbs": 175,
        "weight_unit": "LB",
        "transport_code": "A",
        "transport_reason": "DH"
    }
    valid_claim_data["claim"]["supervising_provider"] = {
        "npi": "5555555555",
        "last": "Wilson",
        "first": "Sarah",
        "driver_license": "DL555555555"
    }
    valid_claim_data["rendering_provider"] = {
        "npi": "1111111111",
        "last": "Taylor",
        "first": "James",
        "driver_license": "DL111111111",
        "address_line1": "789 Elm Street",
        "city": "Frankfort",
        "state": "KY",
        "zip": "40601"
    }
    valid_claim_data["claim"]["member_group"] = {
        "group_id": "KYCD",
        "sub_group_id": "KY11",
        "class_id": "KYRA",
        "plan_id": "KYBG"
    }
    cfg = Config(sender_id="TEST", receiver_id="TEST", gs_sender_code="TEST", gs_receiver_code="TEST")

    edi = build_837p_from_json(valid_claim_data, cfg)

    # Verify all Kaizen enhancements are present
    # 1. Date tracking K3
    assert "K3*DREC-20250110;DADJ-20250115;PAIDDT-20250118~" in edi
    # 2. Provider address K3
    assert "K3*AL1-789 Elm Street~" in edi
    assert "K3*CY-Frankfort;ST-KY;ZIP-40601~" in edi
    # 3. Member group NTE
    assert "NTE*ADD*GRP-KYCD;SGR-KY11;CLS-KYRA;PLN-KYBG" in edi
    # 4. Zero-padded trip number in CR1
    assert "CR1*LB*175****A*DH*000000042~" in edi
    # 5. Driver's licenses
    assert "REF*0B*DL111111111~" in edi  # Rendering provider
    assert "REF*0B*DL555555555~" in edi  # Supervising provider
