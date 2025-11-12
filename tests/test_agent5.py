"""
Tests for Agent 5: Batch Processor

Tests batch processing scenarios including grouping/splitting logic
"""

import pytest
from nemt_837p_converter import (
    BatchProcessor, process_batch,
    BatchReport, BatchIssue, BatchSeverity, BatchConfig
)


@pytest.fixture
def common_data():
    """Common data for all trips in batch"""
    return {
        "billing_provider": {
            "npi": "1234567890",
            "org_name": "ABC Transport LLC",
            "address": {
                "line1": "123 Main St",
                "city": "Louisville",
                "state": "KY",
                "zip": "40202"
            }
        },
        "payer": {
            "payer_id": "87726",
            "payer_name": "UHC Community & State"
        },
        "pos": "41"
    }


@pytest.fixture
def sample_member():
    """Sample member data"""
    return {
        "member_id": "M123456789",
        "name": {"first": "John", "last": "Doe"},
        "dob": "1980-01-01",
        "sex": "M"
    }


def test_batch_report_structure():
    """Test BatchReport dataclass structure"""
    report = BatchReport(success=True)

    assert hasattr(report, 'success')
    assert hasattr(report, 'claims_generated')
    assert hasattr(report, 'trips_processed')
    assert hasattr(report, 'errors')
    assert hasattr(report, 'warnings')
    assert hasattr(report, 'info')


def test_batch_issue_structure():
    """Test BatchIssue dataclass structure"""
    issue = BatchIssue(
        severity=BatchSeverity.ERROR,
        code="BATCH_001",
        message="Test error",
        trip_indices=[0, 1]
    )

    assert issue.severity == BatchSeverity.ERROR
    assert issue.code == "BATCH_001"
    assert issue.message == "Test error"
    assert issue.trip_indices == [0, 1]


def test_empty_batch_creates_error():
    """Test that empty batch creates error"""
    processor = BatchProcessor()
    claims, report = processor.process_batch([])

    assert report.success is False
    assert len(report.errors) > 0
    assert any(e.code == "BATCH_001" for e in report.errors)
    assert len(claims) == 0


def test_scenario_1_same_provider_groups_into_one_claim(common_data, sample_member):
    """
    Scenario 1: Member takes multiple trips for same DOS and same provider
    Expected: One claim with 6 service lines
    """
    trips = [
        # Leg 1: Residence → Hospital (service + mileage)
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210", "name": {"first": "ABC", "last": "Transport"}},
            "pickup": {"addr": "Residence", "city": "Louisville", "state": "KY", "zip": "40202"},
            "dropoff": {"addr": "Hospital", "city": "Louisville", "state": "KY", "zip": "40203"},
            "service": {"hcpcs": "T2005", "modifiers": ["EH"], "charge": 50.00, "units": 1}
        },
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210", "name": {"first": "ABC", "last": "Transport"}},
            "service": {"hcpcs": "T2049", "modifiers": ["EH"], "charge": 4.00, "units": 8}
        },
        # Leg 2: Hospital → LAB
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210", "name": {"first": "ABC", "last": "Transport"}},
            "pickup": {"addr": "Hospital", "city": "Louisville", "state": "KY", "zip": "40203"},
            "dropoff": {"addr": "LAB", "city": "Louisville", "state": "KY", "zip": "40204"},
            "service": {"hcpcs": "T2005", "modifiers": ["HG"], "charge": 50.00, "units": 1}
        },
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210", "name": {"first": "ABC", "last": "Transport"}},
            "service": {"hcpcs": "T2049", "modifiers": ["HG"], "charge": 5.00, "units": 10}
        },
        # Leg 3: LAB → Residence
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210", "name": {"first": "ABC", "last": "Transport"}},
            "pickup": {"addr": "LAB", "city": "Louisville", "state": "KY", "zip": "40204"},
            "dropoff": {"addr": "Residence", "city": "Louisville", "state": "KY", "zip": "40202"},
            "service": {"hcpcs": "T2005", "modifiers": ["GR"], "charge": 50.00, "units": 1}
        },
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210", "name": {"first": "ABC", "last": "Transport"}},
            "service": {"hcpcs": "T2049", "modifiers": ["GR"], "charge": 6.00, "units": 12}
        }
    ]

    processor = BatchProcessor()
    claims, report = processor.process_batch(trips, common_data)

    assert report.success is True
    assert len(claims) == 1, "Should create exactly 1 claim for same DOS/provider"
    assert len(claims[0]["services"]) == 6, "Should have 6 service lines"
    assert claims[0]["claim"]["total_charge"] == 165.00, "Total should be sum of all charges"
    assert report.trips_processed == 6
    assert report.claims_generated == 1


def test_scenario_2_different_providers_creates_separate_claims(common_data, sample_member):
    """
    Scenario 2: Member takes multiple trips for same DOS and different providers
    Expected: 3 separate claims (one per provider)
    """
    trips = [
        # CAB Transport - Leg 1
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "1111111111", "name": {"first": "CAB", "last": "Transport"}},
            "service": {"hcpcs": "T2005", "modifiers": ["EH"], "charge": 50.00, "units": 1}
        },
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "1111111111", "name": {"first": "CAB", "last": "Transport"}},
            "service": {"hcpcs": "T2049", "modifiers": ["EH"], "charge": 4.00, "units": 8}
        },
        # ABC Transport - Leg 2
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "2222222222", "name": {"first": "ABC", "last": "Transport"}},
            "service": {"hcpcs": "T2006", "modifiers": ["HG"], "charge": 60.00, "units": 1}
        },
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "2222222222", "name": {"first": "ABC", "last": "Transport"}},
            "service": {"hcpcs": "T2049", "modifiers": ["HG"], "charge": 5.00, "units": 10}
        },
        # DEF Transport - Leg 3
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "3333333333", "name": {"first": "DEF", "last": "Transport"}},
            "service": {"hcpcs": "T2005", "modifiers": ["GR"], "charge": 50.00, "units": 1}
        },
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "3333333333", "name": {"first": "DEF", "last": "Transport"}},
            "service": {"hcpcs": "T2049", "modifiers": ["GR"], "charge": 6.00, "units": 12}
        }
    ]

    processor = BatchProcessor()
    claims, report = processor.process_batch(trips, common_data)

    assert report.success is True
    assert len(claims) == 3, "Should create 3 separate claims for 3 different providers"
    assert all(len(c["services"]) == 2 for c in claims), "Each claim should have 2 service lines"
    assert report.trips_processed == 6
    assert report.claims_generated == 3

    # Verify each claim has different rendering provider
    npis = [c["rendering_provider"]["npi"] for c in claims]
    assert len(set(npis)) == 3, "Should have 3 distinct provider NPIs"


def test_submission_channel_aggregation_electronic_wins(common_data, sample_member):
    """Test that ELECTRONIC submission channel takes priority over PAPER"""
    trips = [
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210"},
            "service": {"hcpcs": "T2005", "charge": 50.00, "units": 1},
            "submission_channel": "PAPER"
        },
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210"},
            "service": {"hcpcs": "T2049", "charge": 4.00, "units": 8},
            "submission_channel": "ELECTRONIC"
        },
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210"},
            "service": {"hcpcs": "T2005", "charge": 50.00, "units": 1},
            "submission_channel": "PAPER"
        }
    ]

    processor = BatchProcessor()
    claims, report = processor.process_batch(trips, common_data)

    assert len(claims) == 1
    assert claims[0]["claim"]["submission_channel"] == "ELECTRONIC", \
        "If any trip is ELECTRONIC, entire claim should be ELECTRONIC"


def test_submission_channel_aggregation_all_paper(common_data, sample_member):
    """Test that all PAPER submissions result in PAPER claim"""
    trips = [
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210"},
            "service": {"hcpcs": "T2005", "charge": 50.00, "units": 1},
            "submission_channel": "PAPER"
        },
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210"},
            "service": {"hcpcs": "T2049", "charge": 4.00, "units": 8},
            "submission_channel": "PAPER"
        }
    ]

    processor = BatchProcessor()
    claims, report = processor.process_batch(trips, common_data)

    assert len(claims) == 1
    assert claims[0]["claim"]["submission_channel"] == "PAPER"


def test_duplicate_claim_validation_detects_duplicates(common_data, sample_member):
    """Test that duplicate claims are detected per NEMIS criteria (§2.1.10)"""
    # Create two trips that would generate claims with same CLM01, CLM05-3, REF*F8 (original_claim_number)
    trips = [
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210"},
            "service": {"hcpcs": "T2005", "charge": 50.00, "units": 1},
            "original_claim_number": "ORIG-001",  # Per §2.1.10, REF*F8 is original claim number
            "frequency_code": "7"  # Replacement claim
        },
        {
            "dos": "2026-01-02",
            "member": sample_member,
            "rendering_provider": {"npi": "8888888888"},  # Different provider → separate claim
            "service": {"hcpcs": "T2005", "charge": 50.00, "units": 1},
            "original_claim_number": "ORIG-001",  # Same original claim number
            "frequency_code": "7"  # Same frequency (replacement)
        }
    ]

    config = BatchConfig(claim_number_prefix="TEST")
    processor = BatchProcessor(config)

    # Manually force same claim numbers to trigger duplicate detection
    claims, report = processor.process_batch(trips, common_data)

    # Override claim numbers to simulate duplicates
    claims[0]["claim"]["clm_number"] = "TESTDUP001"
    claims[1]["claim"]["clm_number"] = "TESTDUP001"

    # Re-validate
    processor._validate_duplicates(claims)

    dup_errors = [e for e in processor.report.errors if e.code == "BATCH_010"]
    assert len(dup_errors) > 0, "Should detect duplicate claims per NEMIS criteria"


def test_mileage_back_to_back_validation_correct_order(common_data, sample_member):
    """Test that service→mileage ordering is validated correctly"""
    trips = [
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210"},
            "service": {"hcpcs": "T2005", "charge": 50.00, "units": 1}
        },
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210"},
            "service": {"hcpcs": "T2049", "charge": 4.00, "units": 8}  # Mileage follows service
        }
    ]

    processor = BatchProcessor()
    claims, report = processor.process_batch(trips, common_data)

    # Should have INFO message about correct ordering
    info_msgs = [i for i in report.info if i.code == "BATCH_101"]
    assert len(info_msgs) > 0, "Should note correct service→mileage ordering"


def test_mileage_back_to_back_validation_mileage_first_warning(common_data, sample_member):
    """Test warning when mileage code appears first"""
    trips = [
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210"},
            "service": {"hcpcs": "T2049", "charge": 4.00, "units": 8}  # Mileage FIRST (wrong)
        },
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210"},
            "service": {"hcpcs": "T2005", "charge": 50.00, "units": 1}
        }
    ]

    processor = BatchProcessor()
    claims, report = processor.process_batch(trips, common_data)

    warnings = [w for w in report.warnings if w.code == "BATCH_011"]
    assert len(warnings) > 0, "Should warn about mileage appearing first"


def test_mileage_back_to_back_validation_consecutive_mileage_warning(common_data, sample_member):
    """Test warning for consecutive mileage codes"""
    trips = [
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210"},
            "service": {"hcpcs": "T2049", "charge": 4.00, "units": 8}  # Mileage
        },
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210"},
            "service": {"hcpcs": "A0380", "charge": 5.00, "units": 10}  # Another mileage (wrong)
        }
    ]

    processor = BatchProcessor()
    claims, report = processor.process_batch(trips, common_data)

    warnings = [w for w in report.warnings if w.code == "BATCH_012"]
    assert len(warnings) > 0, "Should warn about consecutive mileage codes"


def test_missing_dos_creates_error(common_data, sample_member):
    """Test that missing DOS field creates error"""
    trips = [
        {
            # Missing "dos"
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210"},
            "service": {"hcpcs": "T2005", "charge": 50.00, "units": 1}
        }
    ]

    processor = BatchProcessor()
    claims, report = processor.process_batch(trips, common_data)

    assert report.success is False
    errors = [e for e in report.errors if e.code == "BATCH_002"]
    assert len(errors) > 0


def test_missing_member_creates_error(common_data):
    """Test that missing member field creates error"""
    trips = [
        {
            "dos": "2026-01-01",
            # Missing "member"
            "rendering_provider": {"npi": "9876543210"},
            "service": {"hcpcs": "T2005", "charge": 50.00, "units": 1}
        }
    ]

    processor = BatchProcessor()
    claims, report = processor.process_batch(trips, common_data)

    assert report.success is False
    errors = [e for e in report.errors if e.code == "BATCH_003"]
    assert len(errors) > 0


def test_missing_service_creates_error(common_data, sample_member):
    """Test that missing service field creates error"""
    trips = [
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210"}
            # Missing "service"
        }
    ]

    processor = BatchProcessor()
    claims, report = processor.process_batch(trips, common_data)

    assert report.success is False
    errors = [e for e in report.errors if e.code == "BATCH_004"]
    assert len(errors) > 0


def test_missing_hcpcs_creates_error(common_data, sample_member):
    """Test that missing service.hcpcs creates error"""
    trips = [
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210"},
            "service": {
                # Missing "hcpcs"
                "charge": 50.00,
                "units": 1
            }
        }
    ]

    processor = BatchProcessor()
    claims, report = processor.process_batch(trips, common_data)

    assert report.success is False
    errors = [e for e in report.errors if e.code == "BATCH_005"]
    assert len(errors) > 0


def test_claim_level_fields_copied_from_first_trip(common_data, sample_member):
    """Test that claim-level fields are copied from first trip"""
    trips = [
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210"},
            "service": {"hcpcs": "T2005", "charge": 50.00, "units": 1},
            "auth_number": "AUTH123",
            "patient_account": "PA456",
            "rendering_network_indicator": "I",
            "member_group": {"group_id": "GRP001", "plan_id": "PLN001"},
            "ip_address": "192.168.1.1",
            "user_id": "USER123",
            "subscriber_internal_id": "SUB789",
            "ambulance": {"transport_code": "A", "transport_reason": "A"}
        }
    ]

    processor = BatchProcessor()
    claims, report = processor.process_batch(trips, common_data)

    assert len(claims) == 1
    claim = claims[0]["claim"]
    assert claim.get("auth_number") == "AUTH123"
    assert claim.get("patient_account") == "PA456"
    assert claim.get("rendering_network_indicator") == "I"
    assert claim.get("member_group") == {"group_id": "GRP001", "plan_id": "PLN001"}
    assert claim.get("ip_address") == "192.168.1.1"
    assert claim.get("user_id") == "USER123"
    assert claim.get("subscriber_internal_id") == "SUB789"
    assert claim.get("ambulance") == {"transport_code": "A", "transport_reason": "A"}


def test_service_level_fields_preserved(common_data, sample_member):
    """Test that service-level fields are preserved"""
    trips = [
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210"},
            "service": {"hcpcs": "T2005", "charge": 50.00, "units": 1},
            "pickup": {"addr": "123 Main", "city": "Louisville", "state": "KY", "zip": "40202"},
            "dropoff": {"addr": "456 Oak", "city": "Louisville", "state": "KY", "zip": "40203"},
            "trip_type": "I",
            "trip_leg": "A",
            "payment_status": "P",
            "emergency": True,
            "supervising_provider": {"last": "Smith", "first": "John"}
        }
    ]

    processor = BatchProcessor()
    claims, report = processor.process_batch(trips, common_data)

    assert len(claims) == 1
    svc = claims[0]["services"][0]
    assert svc.get("pickup") == {"addr": "123 Main", "city": "Louisville", "state": "KY", "zip": "40202"}
    assert svc.get("dropoff") == {"addr": "456 Oak", "city": "Louisville", "state": "KY", "zip": "40203"}
    assert svc.get("trip_type") == "I"
    assert svc.get("trip_leg") == "A"
    assert svc.get("payment_status") == "P"
    assert svc.get("emergency") is True
    assert svc.get("supervising_provider") == {"last": "Smith", "first": "John"}


def test_convenience_function(common_data, sample_member):
    """Test process_batch convenience function"""
    trips = [
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210"},
            "service": {"hcpcs": "T2005", "charge": 50.00, "units": 1}
        }
    ]

    claims, report = process_batch(trips, common_data)

    assert isinstance(report, BatchReport)
    assert len(claims) == 1
    assert report.success is True


def test_batch_config_options():
    """Test BatchConfig customization"""
    config = BatchConfig(
        claim_number_prefix="CUSTOM",
        validate_duplicates=False,
        enforce_back_to_back_mileage=False,
        auto_aggregate_submission_channel=False,
        frequency_code_default="6"
    )

    assert config.claim_number_prefix == "CUSTOM"
    assert config.validate_duplicates is False
    assert config.enforce_back_to_back_mileage is False
    assert config.auto_aggregate_submission_channel is False
    assert config.frequency_code_default == "6"


def test_report_string_representation(common_data, sample_member):
    """Test BatchReport __str__ method"""
    trips = [
        {
            "dos": "2026-01-01",
            # Missing member - will create error
            "rendering_provider": {"npi": "9876543210"},
            "service": {"hcpcs": "T2005", "charge": 50.00, "units": 1}
        }
    ]

    processor = BatchProcessor()
    claims, report = processor.process_batch(trips, common_data)

    report_str = str(report)
    assert "FAILED" in report_str or "Error" in report_str
    assert "Claims Generated:" in report_str
    assert "Trips Processed:" in report_str


def test_grouping_info_messages(common_data, sample_member):
    """Test that grouping generates INFO messages"""
    trips = [
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210"},
            "service": {"hcpcs": "T2005", "charge": 50.00, "units": 1}
        },
        {
            "dos": "2026-01-01",
            "member": sample_member,
            "rendering_provider": {"npi": "9876543210"},
            "service": {"hcpcs": "T2049", "charge": 4.00, "units": 8}
        }
    ]

    processor = BatchProcessor()
    claims, report = processor.process_batch(trips, common_data)

    # Should have INFO about grouping
    grouping_info = [i for i in report.info if i.code == "BATCH_100"]
    assert len(grouping_info) > 0
    assert "Grouped" in grouping_info[0].message


def test_severity_enum_values():
    """Test BatchSeverity enum values"""
    assert BatchSeverity.ERROR.value == "ERROR"
    assert BatchSeverity.WARNING.value == "WARNING"
    assert BatchSeverity.INFO.value == "INFO"
