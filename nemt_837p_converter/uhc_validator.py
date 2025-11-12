"""
Agent 3: UHC Business Rule Validator

Validates UHC Community & State specific business rules for NEMT claims.
Goes beyond standard X12 validation to enforce payer-specific requirements.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class UHCRuleSeverity(Enum):
    """UHC business rule violation severity"""
    ERROR = "ERROR"  # Will cause claim rejection
    WARNING = "WARNING"  # May cause claim delay or denial
    INFO = "INFO"  # Best practice recommendation


@dataclass
class UHCRuleViolation:
    """Single UHC business rule violation"""
    severity: UHCRuleSeverity
    code: str  # Unique rule code (e.g., "UHC_001")
    message: str  # Human-readable description
    rule_name: str  # Business rule name
    field_path: Optional[str] = None  # JSON path to field
    expected: Optional[str] = None  # Expected value or condition
    actual: Optional[Any] = None  # Actual value found


@dataclass
class UHCReport:
    """Complete UHC business rule validation report"""
    is_compliant: bool  # True if no errors (warnings OK)
    errors: List[UHCRuleViolation] = field(default_factory=list)
    warnings: List[UHCRuleViolation] = field(default_factory=list)
    info: List[UHCRuleViolation] = field(default_factory=list)

    def add_violation(self, violation: UHCRuleViolation):
        """Add violation to appropriate list based on severity"""
        if violation.severity == UHCRuleSeverity.ERROR:
            self.errors.append(violation)
            self.is_compliant = False
        elif violation.severity == UHCRuleSeverity.WARNING:
            self.warnings.append(violation)
        else:
            self.info.append(violation)

    def __str__(self):
        lines = [f"UHC Business Rules Report: {'PASS' if self.is_compliant else 'FAIL'}"]
        if self.errors:
            lines.append(f"\n{len(self.errors)} Errors:")
            for err in self.errors:
                lines.append(f"  [{err.code}] {err.rule_name}")
                lines.append(f"    {err.message}")
                if err.field_path:
                    lines.append(f"    Field: {err.field_path}")
                if err.expected:
                    lines.append(f"    Expected: {err.expected}")
                if err.actual is not None:
                    lines.append(f"    Actual: {err.actual}")
        if self.warnings:
            lines.append(f"\n{len(self.warnings)} Warnings:")
            for warn in self.warnings:
                lines.append(f"  [{warn.code}] {warn.rule_name}")
                lines.append(f"    {warn.message}")
        if self.info:
            lines.append(f"\n{len(self.info)} Info:")
            for inf in self.info:
                lines.append(f"  [{inf.code}] {inf.rule_name}")
                lines.append(f"    {inf.message}")
        return "\n".join(lines)


class UHCBusinessRuleValidator:
    """
    Agent 3: UHC Business Rule Validator

    Validates UHC Community & State specific business rules for NEMT claims.
    """

    def __init__(self):
        """Initialize UHC validator"""
        self.report = UHCReport(is_compliant=True)

    def validate_claim(self, claim_json: dict) -> UHCReport:
        """
        Validate claim against UHC business rules

        Args:
            claim_json: Claim data dictionary

        Returns:
            UHCReport with all violations found
        """
        self.report = UHCReport(is_compliant=True)

        # Validate NEMT-specific requirements
        self._validate_nemt_requirements(claim_json)

        # Validate K3 segments
        self._validate_k3_segments(claim_json)

        # Validate member group structure
        self._validate_member_group(claim_json)

        # Validate ambulance data
        self._validate_ambulance_data(claim_json)

        # Validate trip details
        self._validate_trip_details(claim_json)

        # Validate authorization
        self._validate_authorization(claim_json)

        # Validate supervising provider requirements
        self._validate_supervising_provider(claim_json)

        return self.report

    def _validate_nemt_requirements(self, claim_json: dict):
        """Validate NEMT-specific requirements"""
        clm = claim_json.get("claim", {})
        services = claim_json.get("services", [])

        # Check for NEMT HCPCS codes
        nemt_codes = {"A0130", "A0140", "A0160", "A0170", "A0180", "A0190", "A0200",
                     "A0210", "A0225", "A0380", "A0382", "A0384", "A0390", "A0392",
                     "A0394", "A0396", "A0398", "A0420", "A0422", "A0424", "A0425",
                     "A0426", "A0427", "A0428", "A0429", "A0430", "A0431", "A0432",
                     "A0433", "A0434", "A0435", "A0436"}

        has_nemt_code = any(svc.get("hcpcs") in nemt_codes for svc in services)

        # If NEMT codes present, require ambulance data
        if has_nemt_code and not clm.get("ambulance"):
            self.report.add_violation(UHCRuleViolation(
                severity=UHCRuleSeverity.ERROR,
                code="UHC_001",
                message="NEMT claims with ambulance HCPCS codes must include ambulance data",
                rule_name="NEMT Ambulance Data Required",
                field_path="claim.ambulance",
                expected="Ambulance data with transport information",
                actual="Missing"
            ))

    def _validate_k3_segments(self, claim_json: dict):
        """Validate K3 segment requirements"""
        clm = claim_json.get("claim", {})

        # UHC requires PYMS K3 for adjudicated claims
        if clm.get("payment_status"):
            if clm["payment_status"] not in ("P", "D"):
                self.report.add_violation(UHCRuleViolation(
                    severity=UHCRuleSeverity.WARNING,
                    code="UHC_002",
                    message="Payment status should be P (Paid) or D (Denied) for UHC claims",
                    rule_name="Payment Status Values",
                    field_path="claim.payment_status",
                    expected="P or D",
                    actual=clm["payment_status"]
                ))

        # Network indicator required for UHC
        if not clm.get("rendering_network_indicator"):
            self.report.add_violation(UHCRuleViolation(
                severity=UHCRuleSeverity.WARNING,
                code="UHC_003",
                message="Network indicator (I/O) recommended for UHC claims",
                rule_name="Network Indicator Recommended",
                field_path="claim.rendering_network_indicator",
                expected="I (in-network) or O (out-of-network)",
                actual="Missing"
            ))

        # Submission channel tracking
        if not clm.get("submission_channel"):
            self.report.add_violation(UHCRuleViolation(
                severity=UHCRuleSeverity.INFO,
                code="UHC_004",
                message="Submission channel (ELECTRONIC/PAPER) helps with UHC tracking",
                rule_name="Submission Channel Tracking",
                field_path="claim.submission_channel",
                expected="ELECTRONIC or PAPER",
                actual="Missing"
            ))

    def _validate_member_group(self, claim_json: dict):
        """Validate member group structure for UHC Kentucky"""
        clm = claim_json.get("claim", {})
        group = clm.get("member_group", {})

        # UHC Kentucky requires specific group structure
        required_fields = ["group_id", "plan_id"]
        missing_fields = [f for f in required_fields if not group.get(f)]

        if missing_fields:
            self.report.add_violation(UHCRuleViolation(
                severity=UHCRuleSeverity.WARNING,
                code="UHC_005",
                message=f"UHC Kentucky claims should include member group details: {', '.join(missing_fields)}",
                rule_name="Member Group Structure",
                field_path="claim.member_group",
                expected=f"group_id, plan_id required",
                actual=f"Missing: {', '.join(missing_fields)}"
            ))

    def _validate_ambulance_data(self, claim_json: dict):
        """Validate ambulance transport data"""
        clm = claim_json.get("claim", {})
        amb = clm.get("ambulance", {})

        if not amb:
            return  # No ambulance data to validate

        # CR1 required fields for UHC
        if not amb.get("weight_unit") or not amb.get("patient_weight_lbs"):
            self.report.add_violation(UHCRuleViolation(
                severity=UHCRuleSeverity.WARNING,
                code="UHC_006",
                message="Patient weight information recommended for ambulance claims",
                rule_name="Patient Weight Required",
                field_path="claim.ambulance.patient_weight_lbs",
                expected="Weight in pounds or kilograms",
                actual="Missing"
            ))

        # Transport code and reason required
        if not amb.get("transport_code"):
            self.report.add_violation(UHCRuleViolation(
                severity=UHCRuleSeverity.ERROR,
                code="UHC_007",
                message="Transport code (A/B/C/D/E) required for ambulance claims",
                rule_name="Transport Code Required",
                field_path="claim.ambulance.transport_code",
                expected="A, B, C, D, or E",
                actual="Missing"
            ))

        if not amb.get("transport_reason"):
            self.report.add_violation(UHCRuleViolation(
                severity=UHCRuleSeverity.ERROR,
                code="UHC_008",
                message="Transport reason required for ambulance claims",
                rule_name="Transport Reason Required",
                field_path="claim.ambulance.transport_reason",
                expected="A, B, C, D, DH, or E",
                actual="Missing"
            ))

        # Trip number required for UHC tracking
        if not amb.get("trip_number"):
            self.report.add_violation(UHCRuleViolation(
                severity=UHCRuleSeverity.WARNING,
                code="UHC_009",
                message="Trip number recommended for UHC NEMT tracking",
                rule_name="Trip Number Tracking",
                field_path="claim.ambulance.trip_number",
                expected="Unique trip identifier",
                actual="Missing"
            ))

    def _validate_trip_details(self, claim_json: dict):
        """Validate trip-specific details at service level"""
        services = claim_json.get("services", [])

        for i, svc in enumerate(services):
            # Trip type validation
            if svc.get("trip_type"):
                valid_types = ["I", "R", "B"]
                if svc["trip_type"] not in valid_types:
                    self.report.add_violation(UHCRuleViolation(
                        severity=UHCRuleSeverity.ERROR,
                        code="UHC_010",
                        message="Invalid trip type for NEMT service",
                        rule_name="Trip Type Validation",
                        field_path=f"services[{i}].trip_type",
                        expected="I (Initial), R (Return), or B (Both)",
                        actual=svc["trip_type"]
                    ))

            # Trip leg validation
            if svc.get("trip_leg"):
                valid_legs = ["A", "B"]
                if svc["trip_leg"] not in valid_legs:
                    self.report.add_violation(UHCRuleViolation(
                        severity=UHCRuleSeverity.ERROR,
                        code="UHC_011",
                        message="Invalid trip leg for NEMT service",
                        rule_name="Trip Leg Validation",
                        field_path=f"services[{i}].trip_leg",
                        expected="A or B",
                        actual=svc["trip_leg"]
                    ))

            # Pickup/dropoff location validation
            if not svc.get("pickup") and not svc.get("dropoff"):
                # Check if claim-level locations exist
                clm = claim_json.get("claim", {})
                amb = clm.get("ambulance", {})
                if not amb.get("pickup") and not amb.get("dropoff"):
                    self.report.add_violation(UHCRuleViolation(
                        severity=UHCRuleSeverity.WARNING,
                        code="UHC_012",
                        message="Pickup or dropoff location recommended for NEMT service",
                        rule_name="Location Information",
                        field_path=f"services[{i}].pickup/dropoff",
                        expected="Pickup and/or dropoff location",
                        actual="Missing at both claim and service levels"
                    ))

    def _validate_authorization(self, claim_json: dict):
        """Validate authorization requirements"""
        clm = claim_json.get("claim", {})

        # UHC typically requires authorization for NEMT
        if not clm.get("auth_number"):
            self.report.add_violation(UHCRuleViolation(
                severity=UHCRuleSeverity.WARNING,
                code="UHC_013",
                message="Authorization number recommended for UHC NEMT claims",
                rule_name="Authorization Required",
                field_path="claim.auth_number",
                expected="Prior authorization number",
                actual="Missing"
            ))

        # Patient account number for tracking
        if not clm.get("patient_account"):
            self.report.add_violation(UHCRuleViolation(
                severity=UHCRuleSeverity.INFO,
                code="UHC_014",
                message="Patient account number helps with claim tracking",
                rule_name="Patient Account Tracking",
                field_path="claim.patient_account",
                expected="Provider's patient account number",
                actual="Missing"
            ))

    def _validate_supervising_provider(self, claim_json: dict):
        """Validate supervising provider requirements per §2.1.1"""
        services = claim_json.get("services", [])
        clm = claim_json.get("claim", {})

        # HCPCS codes that require supervising provider per §2.1.1
        codes_requiring_supervising = {
            "A0090", "A0110", "A0120", "A0140", "A0160", "A0170",
            "A0180", "A0190", "A0200", "A0210", "A0100", "T2001"
        }

        # Check each service line
        for idx, svc in enumerate(services):
            hcpcs = svc.get("hcpcs", "")
            if hcpcs in codes_requiring_supervising:
                # Check for supervising provider at service level or claim level
                has_supervising = (
                    svc.get("supervising_provider") or
                    clm.get("supervising_provider")
                )

                if not has_supervising:
                    self.report.add_violation(UHCRuleViolation(
                        severity=UHCRuleSeverity.ERROR,
                        code="UHC_020",
                        message=f"HCPCS code {hcpcs} requires supervising or attendant provider per §2.1.1",
                        rule_name="Supervising Provider Required",
                        field_path=f"services[{idx}].supervising_provider",
                        expected="Supervising provider data (NPI, name)",
                        actual="Missing"
                    ))


def validate_uhc_business_rules(claim_json: dict) -> UHCReport:
    """
    Convenience function to validate UHC business rules

    Args:
        claim_json: Claim data dictionary

    Returns:
        UHCReport with validation results
    """
    validator = UHCBusinessRuleValidator()
    return validator.validate_claim(claim_json)
