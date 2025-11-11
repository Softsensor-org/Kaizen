"""
Agent 2: X12 Compliance Checker

Validates 837P EDI files against ANSI X12 005010X222A1 specification.
Performs structural validation beyond basic field checking:
- Segment ordering within loops
- Loop hierarchy and positioning
- Required vs conditional segments
- Qualifier codes and data element positioning
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    """Compliance issue severity levels"""
    ERROR = "ERROR"  # Violates X12 spec, will cause rejection
    WARNING = "WARNING"  # Non-standard but may be accepted
    INFO = "INFO"  # Informational, best practice recommendation


@dataclass
class ComplianceIssue:
    """Single compliance violation or warning"""
    severity: Severity
    code: str  # Unique error code (e.g., "LOOP_ORDER_001")
    message: str  # Human-readable description
    segment_id: Optional[str] = None  # Segment that caused issue (e.g., "K3")
    segment_index: Optional[int] = None  # Position in EDI (0-indexed)
    loop_id: Optional[str] = None  # Loop where issue occurred (e.g., "2400")
    expected: Optional[str] = None  # Expected value or position
    actual: Optional[str] = None  # Actual value or position


@dataclass
class ComplianceReport:
    """Complete compliance validation report"""
    is_compliant: bool  # True if no errors (warnings OK)
    errors: List[ComplianceIssue] = field(default_factory=list)
    warnings: List[ComplianceIssue] = field(default_factory=list)
    info: List[ComplianceIssue] = field(default_factory=list)

    def add_issue(self, issue: ComplianceIssue):
        """Add issue to appropriate list based on severity"""
        if issue.severity == Severity.ERROR:
            self.errors.append(issue)
            self.is_compliant = False
        elif issue.severity == Severity.WARNING:
            self.warnings.append(issue)
        else:
            self.info.append(issue)

    def __str__(self):
        lines = [f"Compliance Report: {'PASS' if self.is_compliant else 'FAIL'}"]
        if self.errors:
            lines.append(f"\n{len(self.errors)} Errors:")
            for err in self.errors:
                lines.append(f"  [{err.code}] {err.message}")
                if err.segment_id:
                    lines.append(f"    Segment: {err.segment_id} (index {err.segment_index})")
                if err.expected:
                    lines.append(f"    Expected: {err.expected}")
                if err.actual:
                    lines.append(f"    Actual: {err.actual}")
        if self.warnings:
            lines.append(f"\n{len(self.warnings)} Warnings:")
            for warn in self.warnings:
                lines.append(f"  [{warn.code}] {warn.message}")
        if self.info:
            lines.append(f"\n{len(self.info)} Info:")
            for inf in self.info:
                lines.append(f"  [{inf.code}] {inf.message}")
        return "\n".join(lines)


@dataclass
class Segment:
    """Parsed X12 segment"""
    id: str  # Segment identifier (e.g., "CLM", "NM1", "K3")
    elements: List[str]  # Data elements (excluding segment ID)
    raw: str  # Original segment text
    index: int  # Position in EDI file (0-indexed)


class X12ComplianceChecker:
    """
    Agent 2: X12 Compliance Checker

    Validates 837P EDI structure against ANSI X12 005010X222A1 specification.
    Focus on NEMT-specific requirements for UHC Community & State.
    """

    def __init__(self):
        """Initialize compliance checker with X12 specification rules"""
        self.report = ComplianceReport(is_compliant=True)

    def check_edi(self, edi_content: str) -> ComplianceReport:
        """
        Validate complete EDI file

        Args:
            edi_content: Raw EDI file content (segments separated by ~)

        Returns:
            ComplianceReport with all issues found
        """
        self.report = ComplianceReport(is_compliant=True)

        # Parse EDI into segments
        segments = self._parse_segments(edi_content)
        if not segments:
            self.report.add_issue(ComplianceIssue(
                severity=Severity.ERROR,
                code="PARSE_001",
                message="Failed to parse EDI content - no segments found"
            ))
            return self.report

        # Validate envelope structure
        self._check_envelope_structure(segments)

        # Validate loop hierarchy
        self._check_loop_hierarchy(segments)

        # Validate segment ordering within loops
        self._check_segment_ordering(segments)

        # Validate NEMT-specific requirements
        self._check_nemt_requirements(segments)

        # Validate qualifiers and data elements
        self._check_qualifiers(segments)

        return self.report

    def _parse_segments(self, edi_content: str) -> List[Segment]:
        """Parse EDI content into Segment objects"""
        segments = []
        raw_segments = [s.strip() for s in edi_content.split("~") if s.strip()]

        for idx, raw in enumerate(raw_segments):
            if "*" in raw:
                parts = raw.split("*")
                seg_id = parts[0]
                elements = parts[1:]
                segments.append(Segment(
                    id=seg_id,
                    elements=elements,
                    raw=raw,
                    index=idx
                ))

        return segments

    def _check_envelope_structure(self, segments: List[Segment]):
        """Validate ISA/GS/ST/SE/GE/IEA envelope"""
        if not segments:
            return

        # Check ISA is first
        if segments[0].id != "ISA":
            self.report.add_issue(ComplianceIssue(
                severity=Severity.ERROR,
                code="ENV_001",
                message="EDI must start with ISA segment",
                segment_id=segments[0].id,
                segment_index=0,
                expected="ISA",
                actual=segments[0].id
            ))

        # Check IEA is last
        if segments[-1].id != "IEA":
            self.report.add_issue(ComplianceIssue(
                severity=Severity.ERROR,
                code="ENV_002",
                message="EDI must end with IEA segment",
                segment_id=segments[-1].id,
                segment_index=len(segments) - 1,
                expected="IEA",
                actual=segments[-1].id
            ))

        # Check GS/GE pairing
        gs_count = sum(1 for s in segments if s.id == "GS")
        ge_count = sum(1 for s in segments if s.id == "GE")
        if gs_count != ge_count:
            self.report.add_issue(ComplianceIssue(
                severity=Severity.ERROR,
                code="ENV_003",
                message=f"Mismatched GS/GE segments: {gs_count} GS vs {ge_count} GE",
                expected=f"{gs_count} GE segments",
                actual=f"{ge_count} GE segments"
            ))

        # Check ST/SE pairing
        st_count = sum(1 for s in segments if s.id == "ST")
        se_count = sum(1 for s in segments if s.id == "SE")
        if st_count != se_count:
            self.report.add_issue(ComplianceIssue(
                severity=Severity.ERROR,
                code="ENV_004",
                message=f"Mismatched ST/SE segments: {st_count} ST vs {se_count} SE",
                expected=f"{st_count} SE segments",
                actual=f"{se_count} SE segments"
            ))

    def _check_loop_hierarchy(self, segments: List[Segment]):
        """Validate proper loop hierarchy and positioning"""
        # Find key loop markers
        clm_idx = next((i for i, s in enumerate(segments) if s.id == "CLM"), None)
        lx_indices = [i for i, s in enumerate(segments) if s.id == "LX"]

        if clm_idx is None:
            self.report.add_issue(ComplianceIssue(
                severity=Severity.ERROR,
                code="LOOP_001",
                message="No CLM segment found - Loop 2300 is required"
            ))
            return

        # Check for provider loops at claim level (2310) vs service level (2420)
        self._check_provider_loop_positioning(segments, clm_idx, lx_indices)

    def _check_provider_loop_positioning(self, segments: List[Segment],
                                        clm_idx: int, lx_indices: List[int]):
        """
        Check for ambiguous provider loop positioning
        Critical issue: 2310E/F and 2420G/H use identical NM1 qualifiers
        """
        if not lx_indices:
            return  # No service lines, no service-level loops

        first_lx = lx_indices[0]

        # Find NM1 segments with PW (pickup) and 45 (dropoff) qualifiers
        nm1_pw_segments = [(i, s) for i, s in enumerate(segments)
                          if s.id == "NM1" and len(s.elements) > 0 and s.elements[0] == "PW"]
        nm1_45_segments = [(i, s) for i, s in enumerate(segments)
                          if s.id == "NM1" and len(s.elements) > 0 and s.elements[0] == "45"]

        # Check for pickup locations at both claim and service levels
        claim_level_pw = [idx for idx, seg in nm1_pw_segments if clm_idx < idx < first_lx]
        service_level_pw = [idx for idx, seg in nm1_pw_segments if idx > first_lx]

        if claim_level_pw and service_level_pw:
            self.report.add_issue(ComplianceIssue(
                severity=Severity.WARNING,
                code="LOOP_002",
                message="Pickup location (NM1*PW) present at both claim level (2310E) and service level (2420G)",
                segment_id="NM1",
                loop_id="2310E/2420G",
                expected="Pickup location at one level only",
                actual=f"Found at claim (index {claim_level_pw[0]}) and service (index {service_level_pw[0]})"
            ))

        # Check for dropoff locations at both claim and service levels
        claim_level_45 = [idx for idx, seg in nm1_45_segments if clm_idx < idx < first_lx]
        service_level_45 = [idx for idx, seg in nm1_45_segments if idx > first_lx]

        if claim_level_45 and service_level_45:
            self.report.add_issue(ComplianceIssue(
                severity=Severity.WARNING,
                code="LOOP_003",
                message="Dropoff location (NM1*45) present at both claim level (2310F) and service level (2420H)",
                segment_id="NM1",
                loop_id="2310F/2420H",
                expected="Dropoff location at one level only",
                actual=f"Found at claim (index {claim_level_45[0]}) and service (index {service_level_45[0]})"
            ))

    def _check_segment_ordering(self, segments: List[Segment]):
        """Validate segment ordering within loops"""
        # Find service line loops (marked by LX segments)
        lx_indices = [i for i, s in enumerate(segments) if s.id == "LX"]

        for lx_idx in lx_indices:
            # Find next LX or end of transaction
            next_lx = next((i for i in lx_indices if i > lx_idx), len(segments))

            # Get all segments in this service line
            line_segments = segments[lx_idx:next_lx]

            # Check K3 positioning (must be before NM1 provider loops)
            self._check_k3_positioning(line_segments, lx_idx)

    def _check_k3_positioning(self, line_segments: List[Segment], base_idx: int):
        """Validate K3 segment appears before provider loops (NM1) in 2400"""
        k3_indices = [i for i, s in enumerate(line_segments) if s.id == "K3"]
        nm1_indices = [i for i, s in enumerate(line_segments) if s.id == "NM1"]

        if not k3_indices or not nm1_indices:
            return  # No K3 or no providers, nothing to check

        # K3 should appear before any NM1 in the service line
        first_k3 = min(k3_indices)
        first_nm1 = min(nm1_indices)

        if first_k3 > first_nm1:
            self.report.add_issue(ComplianceIssue(
                severity=Severity.ERROR,
                code="ORDER_001",
                message="K3 segment must appear before provider loops (NM1) in Loop 2400",
                segment_id="K3",
                segment_index=base_idx + first_k3,
                loop_id="2400",
                expected=f"K3 before index {base_idx + first_nm1}",
                actual=f"K3 at index {base_idx + first_k3}"
            ))

    def _check_nemt_requirements(self, segments: List[Segment]):
        """Validate NEMT-specific requirements for UHC"""
        # Check for CR1 segment (required for ambulance claims)
        cr1_segments = [s for s in segments if s.id == "CR1"]
        if not cr1_segments:
            self.report.add_issue(ComplianceIssue(
                severity=Severity.WARNING,
                code="NEMT_001",
                message="No CR1 segment found - required for ambulance/NEMT claims",
                segment_id="CR1",
                loop_id="2300"
            ))

        # Check SV1 emergency indicator position (SV109)
        sv1_segments = [s for s in segments if s.id == "SV1"]
        for sv1 in sv1_segments:
            # SV1 should have at least 9 elements for emergency indicator at SV109
            if len(sv1.elements) < 9:
                self.report.add_issue(ComplianceIssue(
                    severity=Severity.WARNING,
                    code="NEMT_002",
                    message="SV1 segment has fewer than 9 elements - emergency indicator (SV109) may be missing",
                    segment_id="SV1",
                    segment_index=sv1.index,
                    loop_id="2400",
                    expected="At least 9 elements for SV109",
                    actual=f"{len(sv1.elements)} elements"
                ))

        # Check service + mileage adjacency (§2.1.11)
        self._check_service_mileage_adjacency(sv1_segments)

    def _check_service_mileage_adjacency(self, sv1_segments: List[Segment]):
        """
        Validate that mileage codes immediately follow their service codes (§2.1.11).

        NEMT claims typically have service + mileage pairs:
        - Service line (e.g., A0130, T2005)
        - Mileage line (e.g., A0425, T2049)
        """
        # Mileage HCPCS codes that must follow service codes
        MILEAGE_CODES = {
            "A0021",  # Outside state per mile
            "A0080",  # Per mile - volunteer
            "A0090",  # Per mile - individual
            "A0160",  # Per mile - case worker
            "A0200",  # Mileage per mile (UHC KY)
            "A0382",  # BLS mileage
            "A0394",  # ALS mileage
            "A0425",  # Ground mileage
            "A0435",  # Fixed wing mileage
            "A0436",  # Rotary wing mileage
            "T2049",  # Stretcher van mileage
        }

        for i, sv1 in enumerate(sv1_segments):
            if len(sv1.elements) < 1:
                continue

            # Extract HCPCS code from SV101 composite (HC:code:modifiers)
            hcpcs_composite = sv1.elements[0]
            # Parse "HC:A0130:EH" or "HC A0130 EH" format
            hcpcs_parts = hcpcs_composite.replace(":", " ").split()
            if len(hcpcs_parts) < 2:
                continue

            hcpcs_code = hcpcs_parts[1]  # Extract code (skip HC qualifier)

            # Check if this is a mileage code
            if hcpcs_code in MILEAGE_CODES:
                # Mileage code should be preceded by a service code
                if i == 0:
                    # First service line is a mileage code - ERROR
                    self.report.add_issue(ComplianceIssue(
                        severity=Severity.ERROR,
                        code="NEMT_003",
                        message=f"Mileage code {hcpcs_code} appears as first service line - must follow a service code",
                        segment_id="SV1",
                        segment_index=sv1.index,
                        loop_id="2400",
                        expected="Service code before mileage code",
                        actual=f"Mileage code {hcpcs_code} at position 1"
                    ))
                else:
                    # Check if previous line is also a mileage code
                    prev_sv1 = sv1_segments[i - 1]
                    if len(prev_sv1.elements) > 0:
                        prev_hcpcs_composite = prev_sv1.elements[0]
                        prev_hcpcs_parts = prev_hcpcs_composite.replace(":", " ").split()
                        if len(prev_hcpcs_parts) >= 2:
                            prev_hcpcs_code = prev_hcpcs_parts[1]
                            if prev_hcpcs_code in MILEAGE_CODES:
                                # Consecutive mileage codes - WARNING
                                self.report.add_issue(ComplianceIssue(
                                    severity=Severity.WARNING,
                                    code="NEMT_004",
                                    message=f"Consecutive mileage codes detected: {prev_hcpcs_code} followed by {hcpcs_code}",
                                    segment_id="SV1",
                                    segment_index=sv1.index,
                                    loop_id="2400",
                                    expected="Service code before mileage code",
                                    actual=f"Mileage code {prev_hcpcs_code} → {hcpcs_code}"
                                ))

    def _check_qualifiers(self, segments: List[Segment]):
        """Validate qualifier codes and data element positioning"""
        # Check NM1 entity type codes
        for seg in segments:
            if seg.id == "NM1" and len(seg.elements) > 0:
                qualifier = seg.elements[0]
                valid_qualifiers = {
                    "41", "40",  # Submitter, Receiver (1000A/B)
                    "85",  # Billing Provider (2000A)
                    "IL", "PR",  # Insured, Payer (2000B)
                    "DQ",  # Supervising Provider (2310D, 2420D)
                    "PW", "45",  # Pickup, Dropoff (2310E/F, 2420G/H)
                    "77", "DK", "DN"  # Other providers
                }

                if qualifier not in valid_qualifiers:
                    self.report.add_issue(ComplianceIssue(
                        severity=Severity.INFO,
                        code="QUAL_001",
                        message=f"Unusual NM1 entity qualifier: {qualifier}",
                        segment_id="NM1",
                        segment_index=seg.index,
                        expected="One of: " + ", ".join(sorted(valid_qualifiers)),
                        actual=qualifier
                    ))


def check_edi_compliance(edi_content: str) -> ComplianceReport:
    """
    Convenience function to validate EDI compliance

    Args:
        edi_content: Raw EDI file content

    Returns:
        ComplianceReport with validation results
    """
    checker = X12ComplianceChecker()
    return checker.check_edi(edi_content)
