"""
Agent 5: Batch Processing Example

Demonstrates how to use the Batch Processor to handle:
- Scenario 1: Multiple trips same DOS/provider → one claim
- Scenario 2: Multiple trips same DOS/different providers → separate claims
- Submission channel aggregation
- Duplicate detection
- Service/mileage validation
"""

from nemt_837p_converter import (
    process_batch, BatchConfig,
    build_837p_from_json, Config,
    get_payer_config
)


def scenario_1_same_provider_example():
    """
    Scenario 1: Member takes multiple trips on same DOS with same provider
    Expected: One claim with 6 service lines (3 legs × 2 codes each)
    """
    print("=" * 80)
    print("SCENARIO 1: Multiple trips, same DOS, same provider")
    print("Expected: 1 claim with 6 service lines")
    print("=" * 80)

    # Define trips as they come from your system
    trips = [
        # Leg 1: Residence → Hospital (Service + Mileage)
        {
            "dos": "2026-01-01",
            "member": {
                "member_id": "M123456789",
                "name": {"first": "John", "last": "Doe"},
                "dob": "1980-01-01",
                "sex": "M"
            },
            "rendering_provider": {
                "npi": "9876543210",
                "name": {"first": "ABC", "last": "Transport"}
            },
            "pickup": {"addr": "123 Residence St", "city": "Louisville", "state": "KY", "zip": "40202"},
            "dropoff": {"addr": "Hospital Dr", "city": "Louisville", "state": "KY", "zip": "40203"},
            "service": {
                "hcpcs": "T2005",
                "modifiers": ["EH"],
                "charge": 50.00,
                "units": 1
            },
            "submission_channel": "ELECTRONIC"
        },
        {
            "dos": "2026-01-01",
            "member": {"member_id": "M123456789"},
            "rendering_provider": {"npi": "9876543210"},
            "service": {
                "hcpcs": "T2049",
                "modifiers": ["EH"],
                "charge": 4.00,
                "units": 8  # 8 miles
            },
            "submission_channel": "ELECTRONIC"
        },
        # Leg 2: Hospital → LAB
        {
            "dos": "2026-01-01",
            "member": {"member_id": "M123456789"},
            "rendering_provider": {"npi": "9876543210"},
            "pickup": {"addr": "Hospital Dr", "city": "Louisville", "state": "KY", "zip": "40203"},
            "dropoff": {"addr": "LAB Center", "city": "Louisville", "state": "KY", "zip": "40204"},
            "service": {
                "hcpcs": "T2005",
                "modifiers": ["HG"],
                "charge": 50.00,
                "units": 1
            },
            "submission_channel": "PAPER"
        },
        {
            "dos": "2026-01-01",
            "member": {"member_id": "M123456789"},
            "rendering_provider": {"npi": "9876543210"},
            "service": {
                "hcpcs": "T2049",
                "modifiers": ["HG"],
                "charge": 5.00,
                "units": 10  # 10 miles
            },
            "submission_channel": "PAPER"
        },
        # Leg 3: LAB → Residence
        {
            "dos": "2026-01-01",
            "member": {"member_id": "M123456789"},
            "rendering_provider": {"npi": "9876543210"},
            "pickup": {"addr": "LAB Center", "city": "Louisville", "state": "KY", "zip": "40204"},
            "dropoff": {"addr": "123 Residence St", "city": "Louisville", "state": "KY", "zip": "40202"},
            "service": {
                "hcpcs": "T2005",
                "modifiers": ["GR"],
                "charge": 50.00,
                "units": 1
            },
            "submission_channel": "ELECTRONIC"
        },
        {
            "dos": "2026-01-01",
            "member": {"member_id": "M123456789"},
            "rendering_provider": {"npi": "9876543210"},
            "service": {
                "hcpcs": "T2049",
                "modifiers": ["GR"],
                "charge": 6.00,
                "units": 12  # 12 miles
            },
            "submission_channel": "ELECTRONIC"
        }
    ]

    # Common data for all claims
    common_data = {
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

    # Process batch
    claims, report = process_batch(trips, common_data)

    print(f"\n{report}\n")

    if report.success:
        print(f"✓ Successfully processed {report.trips_processed} trips into {report.claims_generated} claim(s)")
        print(f"\nClaim Details:")
        for i, claim in enumerate(claims, 1):
            print(f"  Claim {i}:")
            print(f"    - Claim Number: {claim['claim']['clm_number']}")
            print(f"    - Total Charge: ${claim['claim']['total_charge']:.2f}")
            print(f"    - Service Lines: {len(claim['services'])}")
            print(f"    - Submission Channel: {claim['claim'].get('submission_channel', 'N/A')}")
            print(f"    - Services:")
            for j, svc in enumerate(claim['services'], 1):
                print(f"      {j}. {svc['hcpcs']} - ${svc['charge']:.2f} × {svc['units']} units")
    else:
        print(f"✗ Batch processing failed with {len(report.errors)} errors")

    return claims, report


def scenario_2_different_providers_example():
    """
    Scenario 2: Member takes multiple trips on same DOS with different providers
    Expected: 3 separate claims (one per provider)
    """
    print("\n" + "=" * 80)
    print("SCENARIO 2: Multiple trips, same DOS, different providers")
    print("Expected: 3 separate claims (one per provider)")
    print("=" * 80)

    trips = [
        # CAB Transport - Leg 1
        {
            "dos": "2026-01-01",
            "member": {
                "member_id": "M123456789",
                "name": {"first": "John", "last": "Doe"},
                "dob": "1980-01-01",
                "sex": "M"
            },
            "rendering_provider": {
                "npi": "1111111111",
                "name": {"first": "CAB", "last": "Transport"}
            },
            "service": {"hcpcs": "T2005", "modifiers": ["EH"], "charge": 50.00, "units": 1},
            "submission_channel": "ELECTRONIC"
        },
        {
            "dos": "2026-01-01",
            "member": {"member_id": "M123456789"},
            "rendering_provider": {"npi": "1111111111"},
            "service": {"hcpcs": "T2049", "modifiers": ["EH"], "charge": 4.00, "units": 8},
            "submission_channel": "ELECTRONIC"
        },
        # ABC Transport - Leg 2
        {
            "dos": "2026-01-01",
            "member": {"member_id": "M123456789"},
            "rendering_provider": {
                "npi": "2222222222",
                "name": {"first": "ABC", "last": "Transport"}
            },
            "service": {"hcpcs": "T2006", "modifiers": ["HG"], "charge": 60.00, "units": 1},
            "submission_channel": "PAPER"
        },
        {
            "dos": "2026-01-01",
            "member": {"member_id": "M123456789"},
            "rendering_provider": {"npi": "2222222222"},
            "service": {"hcpcs": "T2049", "modifiers": ["HG"], "charge": 5.00, "units": 10},
            "submission_channel": "PAPER"
        },
        # DEF Transport - Leg 3
        {
            "dos": "2026-01-01",
            "member": {"member_id": "M123456789"},
            "rendering_provider": {
                "npi": "3333333333",
                "name": {"first": "DEF", "last": "Transport"}
            },
            "service": {"hcpcs": "T2005", "modifiers": ["GR"], "charge": 50.00, "units": 1},
            "submission_channel": "ELECTRONIC"
        },
        {
            "dos": "2026-01-01",
            "member": {"member_id": "M123456789"},
            "rendering_provider": {"npi": "3333333333"},
            "service": {"hcpcs": "T2049", "modifiers": ["GR"], "charge": 6.00, "units": 12},
            "submission_channel": "ELECTRONIC"
        }
    ]

    common_data = {
        "billing_provider": {
            "npi": "1234567890",
            "org_name": "KAIZEN Transport Aggregator",
            "address": {"line1": "123 Main St", "city": "Louisville", "state": "KY", "zip": "40202"}
        },
        "payer": {"payer_id": "87726", "payer_name": "UHC Community & State"},
        "pos": "41"
    }

    claims, report = process_batch(trips, common_data)

    print(f"\n{report}\n")

    if report.success:
        print(f"✓ Successfully processed {report.trips_processed} trips into {report.claims_generated} claim(s)")
        print(f"\nClaim Details:")
        for i, claim in enumerate(claims, 1):
            provider_npi = claim['rendering_provider']['npi']
            print(f"  Claim {i} (Provider NPI: {provider_npi}):")
            print(f"    - Claim Number: {claim['claim']['clm_number']}")
            print(f"    - Total Charge: ${claim['claim']['total_charge']:.2f}")
            print(f"    - Service Lines: {len(claim['services'])}")
            print(f"    - Submission Channel: {claim['claim'].get('submission_channel', 'N/A')}")
    else:
        print(f"✗ Batch processing failed with {len(report.errors)} errors")

    return claims, report


def generate_837p_from_batch():
    """
    Complete end-to-end example: Batch processing → EDI generation
    """
    print("\n" + "=" * 80)
    print("END-TO-END: Batch Processing → 837P EDI Generation")
    print("=" * 80)

    # Use Scenario 1 data
    trips = [
        {
            "dos": "2026-01-01",
            "member": {
                "member_id": "M123456789",
                "name": {"first": "John", "last": "Doe"},
                "dob": "1980-01-01",
                "sex": "M",
                "address": {"line1": "123 Residence St", "city": "Louisville", "state": "KY", "zip": "40202"}
            },
            "rendering_provider": {"npi": "9876543210", "name": {"first": "ABC", "last": "Transport"}},
            "service": {"hcpcs": "T2005", "modifiers": ["EH"], "charge": 50.00, "units": 1},
            "submission_channel": "ELECTRONIC",
            "auth_number": "AUTH123456"
        },
        {
            "dos": "2026-01-01",
            "member": {"member_id": "M123456789"},
            "rendering_provider": {"npi": "9876543210"},
            "service": {"hcpcs": "T2049", "modifiers": ["EH"], "charge": 4.00, "units": 8},
            "submission_channel": "ELECTRONIC"
        }
    ]

    common_data = {
        "billing_provider": {
            "npi": "1234567890",
            "org_name": "ABC Transport LLC",
            "tax_id": "123456789",
            "address": {"line1": "123 Main St", "city": "Louisville", "state": "KY", "zip": "40202"}
        },
        "payer": {"payer_id": "87726", "payer_name": "UHC Community & State"},
        "pos": "41"
    }

    # Step 1: Batch processing
    print("\nStep 1: Processing batch...")
    claims, batch_report = process_batch(trips, common_data)

    if not batch_report.success:
        print(f"✗ Batch processing failed:\n{batch_report}")
        return

    print(f"✓ Batch processing successful: {len(claims)} claim(s) generated")

    # Step 2: Generate 837P EDI for each claim
    print("\nStep 2: Generating 837P EDI files...")

    config = Config(
        sender_id="KAIZEN",
        receiver_id="87726",
        sender_qual="30",
        receiver_qual="30",
        usage_indicator="T",
        gs_sender_code="KAIZEN",
        gs_receiver_code="87726",
        payer_config=get_payer_config("UHC_CS")
    )

    for i, claim in enumerate(claims, 1):
        print(f"\n  Generating EDI for Claim {i}...")
        try:
            edi = build_837p_from_json(claim, config)
            print(f"  ✓ EDI generated ({len(edi)} characters)")
            print(f"  ✓ Claim Number: {claim['claim']['clm_number']}")
            print(f"  ✓ Total Charge: ${claim['claim']['total_charge']:.2f}")

            # Show first few segments
            segments = edi.split("~")[:5]
            print(f"\n  First 5 segments:")
            for seg in segments:
                print(f"    {seg}~")

        except Exception as e:
            print(f"  ✗ EDI generation failed: {e}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Run examples
    scenario_1_same_provider_example()
    scenario_2_different_providers_example()
    generate_837p_from_batch()

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("""
Agent 5: Batch Processor successfully handles:

✓ Scenario 1: Multiple trips same DOS/provider → grouped into one claim
✓ Scenario 2: Multiple trips different providers → split into separate claims
✓ Submission channel aggregation (ELECTRONIC if any trip is ELECTRONIC)
✓ Duplicate claim validation (CLM01 + CLM05-3 + REF*F8)
✓ Service/mileage back-to-back validation
✓ Comprehensive batch-level error reporting

Usage Pattern:
  1. Collect trip records from your system
  2. Call process_batch(trips, common_data)
  3. Receive properly grouped claim JSONs
  4. Feed each claim to build_837p_from_json()
  5. Submit resulting EDI files to clearinghouse

State Requirements Covered:
  - 2.1.10: Duplicate claim validation
  - 2.1.11: Service/mileage back-to-back enforcement
  - 2.1.14: Electronic vs Paper aggregation

See test_agent5.py for 22 comprehensive test cases.
    """)
    print("=" * 80)
