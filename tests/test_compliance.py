"""Tests for X12 Compliance Checker (Agent 2)"""

import pytest
from nemt_837p_converter.compliance import (
    X12ComplianceChecker, check_edi_compliance,
    ComplianceReport, ComplianceIssue, Severity
)
from nemt_837p_converter import build_837p_from_json, Config
from nemt_837p_converter.payers import get_payer_config


def test_compliance_checker_initialization():
    """Test compliance checker can be initialized"""
    checker = X12ComplianceChecker()
    assert checker is not None
    assert checker.report.is_compliant is True


def test_empty_edi_fails_parsing():
    """Test empty EDI content fails with parse error"""
    report = check_edi_compliance("")
    assert report.is_compliant is False
    assert len(report.errors) > 0
    assert any(issue.code == "PARSE_001" for issue in report.errors)


def test_valid_edi_passes_envelope_checks(valid_claim_data):
    """Test valid EDI passes envelope structure validation"""
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
    edi = build_837p_from_json(valid_claim_data, cfg)
    report = check_edi_compliance(edi)

    # Should have no envelope errors (ENV_001-004)
    env_errors = [e for e in report.errors if e.code.startswith("ENV_")]
    assert len(env_errors) == 0


def test_missing_isa_detected():
    """Test EDI without ISA segment is detected"""
    # EDI starting with GS instead of ISA
    edi = "GS*HC*TEST*RECV*20251111*1200*1*X*005010X222A1~ST*837*1~SE*2*1~GE*1*1~IEA*1*1~"
    report = check_edi_compliance(edi)

    assert report.is_compliant is False
    assert any(issue.code == "ENV_001" for issue in report.errors)


def test_missing_iea_detected():
    """Test EDI without IEA segment is detected"""
    edi = "ISA*00*          *00*          *ZZ*TEST           *ZZ*RECV           *251111*1200*^*00501*1*T*:~GS*HC*TEST*RECV*20251111*1200*1*X*005010X222A1~ST*837*1~SE*2*1~GE*1*1~"
    report = check_edi_compliance(edi)

    assert report.is_compliant is False
    assert any(issue.code == "ENV_002" for issue in report.errors)


def test_mismatched_st_se_detected():
    """Test mismatched ST/SE counts are detected"""
    edi = "ISA*00*          *00*          *ZZ*TEST           *ZZ*RECV           *251111*1200*^*00501*1*T*:~GS*HC*TEST*RECV*20251111*1200*1*X*005010X222A1~ST*837*1~ST*837*2~SE*2*1~GE*1*1~IEA*1*1~"
    report = check_edi_compliance(edi)

    assert report.is_compliant is False
    assert any(issue.code == "ENV_004" for issue in report.errors)


def test_missing_clm_detected(valid_claim_data):
    """Test EDI without CLM segment is detected"""
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

    # Create EDI without claim data
    minimal_claim = {
        "submitter": {"name": "Test", "id": "TEST"},
        "receiver": {"payer_name": "RECV"},
        "billing_provider": {
            "npi": "1234567890",
            "name": "Test Provider",
            "address": {"line1": "123 Main", "city": "City", "state": "KY", "zip": "40202"}
        },
        "subscriber": {
            "member_id": "M123",
            "name": {"last": "Doe", "first": "John"}
        },
        "claim": {
            "clm_number": "",  # Empty claim number
            "total_charge": 0,
            "from": "2025-01-01"
        },
        "services": []  # No services
    }

    # This should fail pre-submission validation, but let's test with minimal EDI
    edi = "ISA*00*          *00*          *ZZ*TEST           *ZZ*RECV           *251111*1200*^*00501*1*T*:~GS*HC*TEST*RECV*20251111*1200*1*X*005010X222A1~ST*837*1~BHT*0019*00*REF*20251111*1200*CH~NM1*41*2*Test~NM1*40*2*RECV~SE*6*1~GE*1*1~IEA*1*1~"
    report = check_edi_compliance(edi)

    # Should detect missing CLM
    assert any(issue.code == "LOOP_001" for issue in report.errors)


def test_k3_after_nm1_detected_as_error(valid_claim_data):
    """Test K3 segment after NM1 providers is detected as ordering error"""
    # Manually create EDI with K3 after NM1 (wrong order)
    edi_parts = [
        "ISA*00*          *00*          *ZZ*TEST           *ZZ*RECV           *251111*1200*^*00501*1*T*:~",
        "GS*HC*TEST*RECV*20251111*1200*1*X*005010X222A1~",
        "ST*837*1~",
        "BHT*0019*00*CLM001*20251111*1200*CH~",
        "NM1*41*2*Submitter~",
        "NM1*40*2*Receiver~",
        "HL*1**20*1~",
        "NM1*85*2*Provider*****XX*1234567890~",
        "HL*2*1*22*0~",
        "SBR*P*18~",
        "NM1*IL*1*Doe*John~",
        "NM1*PR*2*Payer~",
        "CLM*CLM001*100.00~",
        "LX*1~",
        "SV1*HC A0130*100.00*UN*1***41**N~",
        "NM1*DQ*1*Smith*Alex~",  # Provider BEFORE K3 (wrong!)
        "K3*PYMS-P~",  # K3 AFTER NM1 (wrong order!)
        "SE*17*1~",
        "GE*1*1~",
        "IEA*1*1~"
    ]
    edi = "".join(edi_parts)

    report = check_edi_compliance(edi)

    # Should detect K3 ordering error
    k3_errors = [e for e in report.errors if e.code == "ORDER_001"]
    assert len(k3_errors) > 0
    assert any("K3" in e.message and "before" in e.message for e in k3_errors)


def test_duplicate_pickup_locations_warning(valid_claim_data):
    """Test duplicate pickup locations at claim and service levels generates warning"""
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

    # Modify claim to have pickup at both levels
    claim_with_dupes = valid_claim_data.copy()
    claim_with_dupes["claim"]["ambulance"] = {
        "pickup": {"addr": "Claim Level Pickup", "city": "City1", "state": "KY", "zip": "40201"}
    }
    claim_with_dupes["services"][0]["pickup"] = {
        "addr": "Service Level Pickup", "city": "City2", "state": "KY", "zip": "40202"
    }

    edi = build_837p_from_json(claim_with_dupes, cfg)
    report = check_edi_compliance(edi)

    # Should have warning about duplicate pickup locations
    dup_warnings = [w for w in report.warnings if w.code == "LOOP_002"]
    assert len(dup_warnings) > 0
    assert any("NM1*PW" in w.message and "2310E" in w.message and "2420G" in w.message
              for w in dup_warnings)


def test_duplicate_dropoff_locations_warning(valid_claim_data):
    """Test duplicate dropoff locations at claim and service levels generates warning"""
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

    # Modify claim to have dropoff at both levels
    claim_with_dupes = valid_claim_data.copy()
    claim_with_dupes["claim"]["ambulance"] = {
        "dropoff": {"addr": "Claim Level Dropoff", "city": "City1", "state": "KY", "zip": "40201"}
    }
    claim_with_dupes["services"][0]["dropoff"] = {
        "addr": "Service Level Dropoff", "city": "City2", "state": "KY", "zip": "40202"
    }

    edi = build_837p_from_json(claim_with_dupes, cfg)
    report = check_edi_compliance(edi)

    # Should have warning about duplicate dropoff locations
    dup_warnings = [w for w in report.warnings if w.code == "LOOP_003"]
    assert len(dup_warnings) > 0
    assert any("NM1*45" in w.message and "2310F" in w.message and "2420H" in w.message
              for w in dup_warnings)


def test_missing_cr1_warning():
    """Test missing CR1 segment generates NEMT warning"""
    # Manually create EDI without CR1
    edi_parts = [
        "ISA*00*          *00*          *ZZ*TEST           *ZZ*RECV           *251111*1200*^*00501*1*T*:~",
        "GS*HC*TEST*RECV*20251111*1200*1*X*005010X222A1~",
        "ST*837*1~",
        "BHT*0019*00*CLM001*20251111*1200*CH~",
        "NM1*41*2*Submitter~",
        "NM1*40*2*Receiver~",
        "HL*1**20*1~",
        "NM1*85*2*Provider*****XX*1234567890~",
        "HL*2*1*22*0~",
        "SBR*P*18~",
        "NM1*IL*1*Doe*John~",
        "NM1*PR*2*Payer~",
        "CLM*CLM001*100.00~",
        # No CR1 segment here!
        "LX*1~",
        "SV1*HC A0130*100.00*UN*1***41**N~",
        "SE*14*1~",
        "GE*1*1~",
        "IEA*1*1~"
    ]
    edi = "".join(edi_parts)

    report = check_edi_compliance(edi)

    # Should have warning about missing CR1
    cr1_warnings = [w for w in report.warnings if w.code == "NEMT_001"]
    assert len(cr1_warnings) > 0
    assert any("CR1" in w.message for w in cr1_warnings)


def test_sv1_short_elements_warning():
    """Test SV1 with fewer than 9 elements generates warning"""
    edi_parts = [
        "ISA*00*          *00*          *ZZ*TEST           *ZZ*RECV           *251111*1200*^*00501*1*T*:~",
        "GS*HC*TEST*RECV*20251111*1200*1*X*005010X222A1~",
        "ST*837*1~",
        "BHT*0019*00*CLM001*20251111*1200*CH~",
        "NM1*41*2*Submitter~",
        "NM1*40*2*Receiver~",
        "HL*1**20*1~",
        "NM1*85*2*Provider*****XX*1234567890~",
        "HL*2*1*22*0~",
        "SBR*P*18~",
        "NM1*IL*1*Doe*John~",
        "NM1*PR*2*Payer~",
        "CLM*CLM001*100.00~",
        "LX*1~",
        "SV1*HC A0130*100.00*UN*1~",  # Only 4 elements (missing POS, emergency, etc.)
        "SE*14*1~",
        "GE*1*1~",
        "IEA*1*1~"
    ]
    edi = "".join(edi_parts)

    report = check_edi_compliance(edi)

    # Should have warning about short SV1
    sv1_warnings = [w for w in report.warnings if w.code == "NEMT_002"]
    assert len(sv1_warnings) > 0
    assert any("SV1" in w.message and "9 elements" in w.message for w in sv1_warnings)


def test_compliance_report_str_format():
    """Test ComplianceReport string formatting"""
    report = ComplianceReport(is_compliant=False)
    report.add_issue(ComplianceIssue(
        severity=Severity.ERROR,
        code="TEST_001",
        message="Test error message",
        segment_id="CLM",
        expected="Expected value",
        actual="Actual value"
    ))
    report.add_issue(ComplianceIssue(
        severity=Severity.WARNING,
        code="TEST_002",
        message="Test warning message"
    ))

    report_str = str(report)
    assert "FAIL" in report_str
    assert "TEST_001" in report_str
    assert "TEST_002" in report_str
    assert "Test error message" in report_str
    assert "Test warning message" in report_str


def test_valid_claim_compliance(valid_claim_data):
    """Test that a properly structured valid claim passes compliance checks"""
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
    edi = build_837p_from_json(valid_claim_data, cfg)
    report = check_edi_compliance(edi)

    # Valid claim should have no critical errors
    assert len(report.errors) == 0
    # May have warnings (e.g., missing CR1 if not an ambulance claim)
    # But should be compliant overall if no errors
    if len(report.errors) == 0:
        assert report.is_compliant is True

def test_service_mileage_correct_order():
    """Test service + mileage in correct order passes validation"""
    edi_parts = [
        "ISA*00*          *00*          *ZZ*TEST           *ZZ*RECV           *251111*1200*^*00501*1*T*:~",
        "GS*HC*TEST*RECV*20251111*1200*1*X*005010X222A1~",
        "ST*837*1~",
        "BHT*0019*00*CLM001*20251111*1200*CH~",
        "NM1*41*2*Submitter~",
        "NM1*40*2*Receiver~",
        "HL*1**20*1~",
        "NM1*85*2*Provider*****XX*1234567890~",
        "HL*2*1*22*0~",
        "SBR*P*18~",
        "NM1*IL*1*Doe*John~",
        "NM1*PR*2*Payer~",
        "CLM*CLM001*150.00~",
        "CR1*LB*150*A*1*A*DH~",
        "LX*1~",
        "SV1*HC A0130 EH*100.00*UN*1***41**N~",  # Service code
        "LX*2~",
        "SV1*HC A0425 EH*50.00*UN*10***41**N~",  # Mileage code (correct order)
        "SE*17*1~",
        "GE*1*1~",
        "IEA*1*1~"
    ]
    edi = "".join(edi_parts)
    report = check_edi_compliance(edi)

    # Should have no NEMT_003 or NEMT_004 errors
    mileage_errors = [e for e in report.errors if e.code in ["NEMT_003", "NEMT_004"]]
    mileage_warnings = [w for w in report.warnings if w.code in ["NEMT_003", "NEMT_004"]]
    assert len(mileage_errors) == 0
    assert len(mileage_warnings) == 0


def test_mileage_first_generates_error():
    """Test mileage code as first service line generates error"""
    edi_parts = [
        "ISA*00*          *00*          *ZZ*TEST           *ZZ*RECV           *251111*1200*^*00501*1*T*:~",
        "GS*HC*TEST*RECV*20251111*1200*1*X*005010X222A1~",
        "ST*837*1~",
        "BHT*0019*00*CLM001*20251111*1200*CH~",
        "NM1*41*2*Submitter~",
        "NM1*40*2*Receiver~",
        "HL*1**20*1~",
        "NM1*85*2*Provider*****XX*1234567890~",
        "HL*2*1*22*0~",
        "SBR*P*18~",
        "NM1*IL*1*Doe*John~",
        "NM1*PR*2*Payer~",
        "CLM*CLM001*50.00~",
        "CR1*LB*150*A*1*A*DH~",
        "LX*1~",
        "SV1*HC A0425 EH*50.00*UN*10***41**N~",  # Mileage code FIRST (error!)
        "SE*15*1~",
        "GE*1*1~",
        "IEA*1*1~"
    ]
    edi = "".join(edi_parts)
    report = check_edi_compliance(edi)

    # Should have NEMT_003 error
    mileage_errors = [e for e in report.errors if e.code == "NEMT_003"]
    assert len(mileage_errors) > 0
    assert any("A0425" in e.message and "first service line" in e.message for e in mileage_errors)


def test_consecutive_mileage_generates_warning():
    """Test consecutive mileage codes generate warning"""
    edi_parts = [
        "ISA*00*          *00*          *ZZ*TEST           *ZZ*RECV           *251111*1200*^*00501*1*T*:~",
        "GS*HC*TEST*RECV*20251111*1200*1*X*005010X222A1~",
        "ST*837*1~",
        "BHT*0019*00*CLM001*20251111*1200*CH~",
        "NM1*41*2*Submitter~",
        "NM1*40*2*Receiver~",
        "HL*1**20*1~",
        "NM1*85*2*Provider*****XX*1234567890~",
        "HL*2*1*22*0~",
        "SBR*P*18~",
        "NM1*IL*1*Doe*John~",
        "NM1*PR*2*Payer~",
        "CLM*CLM001*150.00~",
        "CR1*LB*150*A*1*A*DH~",
        "LX*1~",
        "SV1*HC A0130 EH*100.00*UN*1***41**N~",  # Service code
        "LX*2~",
        "SV1*HC A0425 EH*25.00*UN*5***41**N~",  # Mileage code
        "LX*3~",
        "SV1*HC T2049 EH*25.00*UN*5***41**N~",  # Another mileage code (warning!)
        "SE*18*1~",
        "GE*1*1~",
        "IEA*1*1~"
    ]
    edi = "".join(edi_parts)
    report = check_edi_compliance(edi)

    # Should have NEMT_004 warning
    mileage_warnings = [w for w in report.warnings if w.code == "NEMT_004"]
    assert len(mileage_warnings) > 0
    assert any("Consecutive mileage" in w.message and "A0425" in w.message and "T2049" in w.message
              for w in mileage_warnings)


def test_t2049_mileage_validation():
    """Test T2049 stretcher van mileage code validation"""
    edi_parts = [
        "ISA*00*          *00*          *ZZ*TEST           *ZZ*RECV           *251111*1200*^*00501*1*T*:~",
        "GS*HC*TEST*RECV*20251111*1200*1*X*005010X222A1~",
        "ST*837*1~",
        "BHT*0019*00*CLM001*20251111*1200*CH~",
        "NM1*41*2*Submitter~",
        "NM1*40*2*Receiver~",
        "HL*1**20*1~",
        "NM1*85*2*Provider*****XX*1234567890~",
        "HL*2*1*22*0~",
        "SBR*P*18~",
        "NM1*IL*1*Doe*John~",
        "NM1*PR*2*Payer~",
        "CLM*CLM001*90.00~",
        "CR1*LB*150*A*1*A*DH~",
        "LX*1~",
        "SV1*HC T2005 EH*50.00*UN*1***41**N~",  # Service: Stretcher van
        "LX*2~",
        "SV1*HC T2049 EH*40.00*UN*10***41**N~",  # Mileage: Stretcher van mileage
        "SE*17*1~",
        "GE*1*1~",
        "IEA*1*1~"
    ]
    edi = "".join(edi_parts)
    report = check_edi_compliance(edi)

    # T2049 following T2005 should be valid
    mileage_errors = [e for e in report.errors if e.code in ["NEMT_003", "NEMT_004"]]
    assert len(mileage_errors) == 0
