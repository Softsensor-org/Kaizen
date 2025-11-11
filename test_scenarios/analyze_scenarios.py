"""
Analyze test scenarios for loop hierarchy verification

Generates compliance reports for each scenario to identify
loop positioning ambiguities for UHC/Availity verification.
"""

from pathlib import Path
from nemt_837p_converter.compliance import check_edi_compliance

def analyze_scenario(scenario_name: str, edi_path: Path):
    """Analyze a single scenario and generate compliance report"""
    print(f"\n{'='*80}")
    print(f"SCENARIO: {scenario_name}")
    print(f"{'='*80}")

    # Read EDI file
    with open(edi_path, 'r') as f:
        edi_content = f.read()

    # Run compliance check
    report = check_edi_compliance(edi_content)

    # Display results
    print(f"\nCompliance Status: {'✓ PASS' if report.is_compliant else '✗ FAIL'}")
    print(f"Errors: {len(report.errors)}")
    print(f"Warnings: {len(report.warnings)}")
    print(f"Info: {len(report.info)}")

    if report.errors:
        print(f"\n--- ERRORS ---")
        for err in report.errors:
            print(f"  [{err.code}] {err.message}")
            if err.segment_id:
                print(f"    Segment: {err.segment_id} (index {err.segment_index})")
            if err.loop_id:
                print(f"    Loop: {err.loop_id}")

    if report.warnings:
        print(f"\n--- WARNINGS ---")
        for warn in report.warnings:
            print(f"  [{warn.code}] {warn.message}")
            if warn.segment_id:
                print(f"    Segment: {warn.segment_id}")
            if warn.loop_id:
                print(f"    Loop: {warn.loop_id}")

    # Extract key segments for visual inspection
    print(f"\n--- KEY SEGMENTS ---")
    segments = edi_content.split('~')

    # Find CLM segment
    clm_idx = next((i for i, s in enumerate(segments) if s.startswith('CLM*')), None)

    # Find LX segments
    lx_indices = [i for i, s in enumerate(segments) if s.startswith('LX*')]

    # Find NM1 pickup/dropoff segments
    pickup_segments = [(i, s) for i, s in enumerate(segments) if s.startswith('NM1*PW*')]
    dropoff_segments = [(i, s) for i, s in enumerate(segments) if s.startswith('NM1*45*')]

    if clm_idx is not None:
        print(f"  CLM at index {clm_idx}")

        # Check for claim-level pickup/dropoff (before first LX)
        if lx_indices:
            first_lx = lx_indices[0]
            print(f"  First LX at index {first_lx}")

            claim_pickups = [idx for idx, seg in pickup_segments if clm_idx < idx < first_lx]
            claim_dropoffs = [idx for idx, seg in dropoff_segments if clm_idx < idx < first_lx]

            if claim_pickups:
                print(f"  ✓ Claim-level pickup (2310E) at index {claim_pickups[0]}")
            else:
                print(f"  ✗ No claim-level pickup (2310E)")

            if claim_dropoffs:
                print(f"  ✓ Claim-level dropoff (2310F) at index {claim_dropoffs[0]}")
            else:
                print(f"  ✗ No claim-level dropoff (2310F)")

            # Check for service-level pickup/dropoff (after each LX)
            for lx_idx in lx_indices:
                next_lx = lx_indices[lx_indices.index(lx_idx) + 1] if lx_indices.index(lx_idx) + 1 < len(lx_indices) else len(segments)

                svc_pickups = [idx for idx, seg in pickup_segments if lx_idx < idx < next_lx]
                svc_dropoffs = [idx for idx, seg in dropoff_segments if lx_idx < idx < next_lx]

                if svc_pickups:
                    print(f"  ✓ Service-level pickup (2420G) at index {svc_pickups[0]} (after LX {lx_idx})")

                if svc_dropoffs:
                    print(f"  ✓ Service-level dropoff (2420H) at index {svc_dropoffs[0]} (after LX {lx_idx})")

    return report


def main():
    """Analyze all scenarios"""
    scenarios_dir = Path(__file__).parent

    scenarios = [
        ("Scenario 1: Service-Level Only (Baseline)",
         scenarios_dir / "scenario1_service_level_only.edi"),
        ("Scenario 2: Claim-Level Only",
         scenarios_dir / "scenario2_claim_level_only.edi"),
        ("Scenario 3: Both Levels (AMBIGUOUS)",
         scenarios_dir / "scenario3_both_levels_ambiguous.edi"),
    ]

    print("LOOP HIERARCHY VERIFICATION - TEST SCENARIOS")
    print("="*80)
    print("\nThis script analyzes three test scenarios to identify loop hierarchy")
    print("ambiguities with NM1*PW (pickup) and NM1*45 (dropoff) locations.")
    print("\nScenarios:")
    print("  1. Service-level only (2420G/H) - Clean baseline")
    print("  2. Claim-level only (2310E/F) - Alternative approach")
    print("  3. Both levels present - AMBIGUOUS case requiring UHC/Availity verification")

    reports = {}
    for scenario_name, edi_path in scenarios:
        if edi_path.exists():
            reports[scenario_name] = analyze_scenario(scenario_name, edi_path)
        else:
            print(f"\n{'='*80}")
            print(f"SCENARIO: {scenario_name}")
            print(f"{'='*80}")
            print(f"ERROR: EDI file not found: {edi_path}")

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    for scenario_name, report in reports.items():
        status = "✓ PASS" if report.is_compliant else "✗ FAIL"
        warnings_note = f" ({len(report.warnings)} warnings)" if report.warnings else ""
        print(f"{status}{warnings_note}: {scenario_name}")

    print("\n--- KEY FINDINGS ---")
    print("Scenario 1 (Service-Level Only):")
    print("  - Uses 2420G/H for pickup/dropoff at service line level")
    print("  - No claim-level locations (2310E/F)")
    print("  - ✓ Clean, unambiguous structure")

    print("\nScenario 2 (Claim-Level Only):")
    print("  - Uses 2310E/F for pickup/dropoff at claim level")
    print("  - No service-level locations (2420G/H)")
    print("  - ✓ Clean, alternative structure")

    print("\nScenario 3 (Both Levels - AMBIGUOUS):")
    print("  - Uses BOTH 2310E/F (claim) AND 2420G/H (service)")
    print("  - ⚠️ Identical NM1 qualifiers at different levels")
    print("  - ⚠️ Requires UHC/Availity clarification on precedence")

    if "Scenario 3: Both Levels (AMBIGUOUS)" in reports:
        report = reports["Scenario 3: Both Levels (AMBIGUOUS)"]
        if report.warnings:
            ambiguity_warnings = [w for w in report.warnings if w.code in ("LOOP_002", "LOOP_003")]
            if ambiguity_warnings:
                print(f"\n  Agent 2 detected {len(ambiguity_warnings)} ambiguity warnings")
                for warn in ambiguity_warnings:
                    print(f"    - {warn.message}")

    print("\n--- NEXT STEPS ---")
    print("1. Review EDI files in test_scenarios/ directory")
    print("2. Submit to UHC/Availity staging environment")
    print("3. Monitor for acceptance/rejection")
    print("4. If rejected, analyze rejection codes")
    print("5. Update LOOP_HIERARCHY_ANALYSIS.md with findings")
    print("6. Implement fixes based on payer guidance")


if __name__ == "__main__":
    main()
