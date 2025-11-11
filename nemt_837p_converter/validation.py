"""
Agent 1: Pre-Submission Validator

Validates claim JSON data before EDI generation.
Performs field validation, format checking, code value verification,
and business rule validation with structured reporting.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import re
from datetime import datetime

from .codes import (
    POS_CODES, NEMT_HCPCS_CODES, HCPCS_MODIFIERS, FREQUENCY_CODES,
    TRANSPORT_CODES, TRANSPORT_REASON_CODES, WEIGHT_UNITS, GENDER_CODES,
    TRIP_TYPES, TRIP_LEGS, NETWORK_INDICATORS, SUBMISSION_CHANNELS,
    PAYMENT_STATUS_CODES, STATE_CODES, validate_code
)


class ValidationSeverity(Enum):
    """Validation issue severity levels"""
    ERROR = "ERROR"  # Must fix before submission
    WARNING = "WARNING"  # Should fix, may cause issues
    INFO = "INFO"  # Informational, best practice


@dataclass
class ValidationIssue:
    """Single validation issue"""
    severity: ValidationSeverity
    code: str  # Unique error code (e.g., "VAL_001")
    message: str  # Human-readable description
    field_path: str  # JSON path to field (e.g., "claim.clm_number")
    expected: Optional[str] = None  # Expected value or format
    actual: Optional[Any] = None  # Actual value provided


@dataclass
class ValidationReport:
    """Complete pre-submission validation report"""
    is_valid: bool  # True if no errors (warnings OK)
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    info: List[ValidationIssue] = field(default_factory=list)

    def add_issue(self, issue: ValidationIssue):
        """Add issue to appropriate list based on severity"""
        if issue.severity == ValidationSeverity.ERROR:
            self.errors.append(issue)
            self.is_valid = False
        elif issue.severity == ValidationSeverity.WARNING:
            self.warnings.append(issue)
        else:
            self.info.append(issue)

    def __str__(self):
        lines = [f"Validation Report: {'PASS' if self.is_valid else 'FAIL'}"]
        if self.errors:
            lines.append(f"\n{len(self.errors)} Errors:")
            for err in self.errors:
                lines.append(f"  [{err.code}] {err.field_path}: {err.message}")
                if err.expected:
                    lines.append(f"    Expected: {err.expected}")
                if err.actual is not None:
                    lines.append(f"    Actual: {err.actual}")
        if self.warnings:
            lines.append(f"\n{len(self.warnings)} Warnings:")
            for warn in self.warnings:
                lines.append(f"  [{warn.code}] {warn.field_path}: {warn.message}")
        if self.info:
            lines.append(f"\n{len(self.info)} Info:")
            for inf in self.info:
                lines.append(f"  [{inf.code}] {inf.field_path}: {inf.message}")
        return "\n".join(lines)


class PreSubmissionValidator:
    """
    Agent 1: Pre-Submission Validator

    Validates claim JSON before EDI generation.
    Refactored from builder.py with structured reporting.
    """

    def __init__(self):
        """Initialize validator"""
        self.report = ValidationReport(is_valid=True)

    def validate_claim(self, claim_json: dict) -> ValidationReport:
        """
        Validate complete claim JSON

        Args:
            claim_json: Claim data dictionary

        Returns:
            ValidationReport with all issues found
        """
        self.report = ValidationReport(is_valid=True)

        # Validate all sections
        self._validate_billing_provider(claim_json.get("billing_provider", {}))
        self._validate_subscriber(claim_json.get("subscriber", {}))
        self._validate_claim(claim_json.get("claim", {}))
        self._validate_services(claim_json.get("services", []))

        # Cross-field validations
        self._validate_claim_total(claim_json)

        return self.report

    def _validate_billing_provider(self, bp: dict):
        """Validate billing provider data"""
        # NPI - required, 10 digits
        if not bp.get("npi"):
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_001",
                message="billing_provider.npi is required",
                field_path="billing_provider.npi"
            ))
        elif not re.match(r'^\d{10}$', str(bp["npi"])):
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_002",
                message="billing_provider.npi must be 10 digits",
                field_path="billing_provider.npi",
                expected="10 digits",
                actual=bp["npi"]
            ))

        # Name - required, max 60 chars
        if not bp.get("name"):
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_003",
                message="billing_provider.name is required",
                field_path="billing_provider.name"
            ))
        elif len(bp["name"]) > 60:
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_004",
                message="billing_provider.name exceeds 60 characters",
                field_path="billing_provider.name",
                expected="Max 60 characters",
                actual=f"{len(bp['name'])} characters"
            ))

        # Address - required
        addr = bp.get("address", {})
        if not addr.get("line1"):
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_005",
                message="billing_provider.address.line1 is required",
                field_path="billing_provider.address.line1"
            ))
        elif len(addr["line1"]) > 55:
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_006",
                message="billing_provider.address.line1 exceeds 55 characters",
                field_path="billing_provider.address.line1",
                expected="Max 55 characters",
                actual=f"{len(addr['line1'])} characters"
            ))

        # City - required, max 30 chars
        if not addr.get("city"):
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_007",
                message="billing_provider.address.city is required",
                field_path="billing_provider.address.city"
            ))
        elif len(addr["city"]) > 30:
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_008",
                message="billing_provider.address.city exceeds 30 characters",
                field_path="billing_provider.address.city",
                expected="Max 30 characters",
                actual=f"{len(addr['city'])} characters"
            ))

        # State - required, valid US state
        if not addr.get("state"):
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_009",
                message="billing_provider.address.state is required",
                field_path="billing_provider.address.state"
            ))
        elif addr["state"] not in STATE_CODES:
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_010",
                message="billing_provider.address.state is not a valid US state code",
                field_path="billing_provider.address.state",
                expected="Valid US state code",
                actual=addr["state"]
            ))

        # ZIP - required, format 12345 or 12345-6789
        if not addr.get("zip"):
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_011",
                message="billing_provider.address.zip is required",
                field_path="billing_provider.address.zip"
            ))
        elif not re.match(r'^\d{5}(-\d{4})?$', addr["zip"]):
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_012",
                message="billing_provider.address.zip must be format 12345 or 12345-6789",
                field_path="billing_provider.address.zip",
                expected="Format: 12345 or 12345-6789",
                actual=addr["zip"]
            ))

        # Tax ID - optional, 9 digits
        if bp.get("tax_id") and not re.match(r'^\d{9}$', bp["tax_id"]):
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_013",
                message="billing_provider.tax_id must be 9 digits",
                field_path="billing_provider.tax_id",
                expected="9 digits",
                actual=bp["tax_id"]
            ))

    def _validate_subscriber(self, sub: dict):
        """Validate subscriber data"""
        # Member ID - required, max 80 chars
        if not sub.get("member_id"):
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_020",
                message="subscriber.member_id is required",
                field_path="subscriber.member_id"
            ))
        elif len(sub["member_id"]) > 80:
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_021",
                message="subscriber.member_id exceeds 80 characters",
                field_path="subscriber.member_id",
                expected="Max 80 characters",
                actual=f"{len(sub['member_id'])} characters"
            ))

        # Name - required
        name = sub.get("name", {})
        if not name.get("last"):
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_022",
                message="subscriber.name.last is required",
                field_path="subscriber.name.last"
            ))
        elif len(name["last"]) > 60:
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_023",
                message="subscriber.name.last exceeds 60 characters",
                field_path="subscriber.name.last",
                expected="Max 60 characters",
                actual=f"{len(name['last'])} characters"
            ))

        if not name.get("first"):
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_024",
                message="subscriber.name.first is required",
                field_path="subscriber.name.first"
            ))
        elif len(name["first"]) > 35:
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_025",
                message="subscriber.name.first exceeds 35 characters",
                field_path="subscriber.name.first",
                expected="Max 35 characters",
                actual=f"{len(name['first'])} characters"
            ))

        # DOB - optional, format YYYY-MM-DD
        if sub.get("dob") and not re.match(r'^\d{4}-\d{2}-\d{2}$', sub["dob"]):
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_026",
                message="subscriber.dob must be format YYYY-MM-DD",
                field_path="subscriber.dob",
                expected="Format: YYYY-MM-DD",
                actual=sub["dob"]
            ))

        # Gender - optional, F/M/U
        if sub.get("sex"):
            err = validate_code(sub["sex"], GENDER_CODES, "subscriber.sex")
            if err:
                self.report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="VAL_027",
                    message=err,
                    field_path="subscriber.sex",
                    expected="F, M, or U",
                    actual=sub["sex"]
                ))

    def _validate_claim(self, clm: dict):
        """Validate claim-level data"""
        # Claim number - required, max 30 chars
        if not clm.get("clm_number"):
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_030",
                message="claim.clm_number is required",
                field_path="claim.clm_number"
            ))
        elif len(clm["clm_number"]) > 30:
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_031",
                message="claim.clm_number exceeds 30 characters",
                field_path="claim.clm_number",
                expected="Max 30 characters",
                actual=f"{len(clm['clm_number'])} characters"
            ))

        # Total charge - required, must be > 0 (except void claims)
        if clm.get("total_charge") is None:
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_032",
                message="claim.total_charge is required",
                field_path="claim.total_charge"
            ))
        elif clm.get("total_charge") == 0 and clm.get("frequency_code") != "8":
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_033",
                message="claim.total_charge must be > 0 (or use frequency_code=8 for void claims)",
                field_path="claim.total_charge",
                expected="> 0",
                actual=clm.get("total_charge")
            ))

        # From date - required, format YYYY-MM-DD
        if not clm.get("from"):
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_034",
                message="claim.from is required",
                field_path="claim.from"
            ))
        elif not re.match(r'^\d{4}-\d{2}-\d{2}$', clm["from"]):
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_035",
                message="claim.from must be format YYYY-MM-DD",
                field_path="claim.from",
                expected="Format: YYYY-MM-DD",
                actual=clm["from"]
            ))

        # To date - optional, format YYYY-MM-DD
        if clm.get("to") and not re.match(r'^\d{4}-\d{2}-\d{2}$', clm["to"]):
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_036",
                message="claim.to must be format YYYY-MM-DD",
                field_path="claim.to",
                expected="Format: YYYY-MM-DD",
                actual=clm["to"]
            ))

        # POS - optional, valid code
        if clm.get("pos"):
            err = validate_code(clm["pos"], POS_CODES, "claim.pos")
            if err:
                self.report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="VAL_037",
                    message=err,
                    field_path="claim.pos",
                    expected="Valid POS code",
                    actual=clm["pos"]
                ))

        # Frequency code - optional, valid code
        if clm.get("frequency_code"):
            err = validate_code(clm["frequency_code"], FREQUENCY_CODES, "claim.frequency_code")
            if err:
                self.report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="VAL_038",
                    message=err,
                    field_path="claim.frequency_code",
                    expected="1, 6, 7, or 8",
                    actual=clm["frequency_code"]
                ))

    def _validate_services(self, services: List[dict]):
        """Validate service line data"""
        if not services:
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VAL_040",
                message="At least one service is required",
                field_path="services"
            ))
            return

        for i, svc in enumerate(services):
            # HCPCS - required, max 5 chars
            if not svc.get("hcpcs"):
                self.report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="VAL_041",
                    message="services[].hcpcs is required",
                    field_path=f"services[{i}].hcpcs"
                ))
            elif len(svc["hcpcs"]) > 5:
                self.report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="VAL_042",
                    message="services[].hcpcs exceeds 5 characters",
                    field_path=f"services[{i}].hcpcs",
                    expected="Max 5 characters",
                    actual=svc["hcpcs"]
                ))

            # Charge - required
            if svc.get("charge") is None:
                self.report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="VAL_043",
                    message="services[].charge is required",
                    field_path=f"services[{i}].charge"
                ))

            # Modifiers - max 4, each 2 chars
            mods = svc.get("modifiers", [])
            if len(mods) > 4:
                self.report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="VAL_044",
                    message="services[].modifiers limited to 4 modifiers",
                    field_path=f"services[{i}].modifiers",
                    expected="Max 4 modifiers",
                    actual=f"{len(mods)} modifiers"
                ))
            for mod in mods:
                if len(mod) != 2:
                    self.report.add_issue(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="VAL_045",
                        message="Modifier must be 2 characters",
                        field_path=f"services[{i}].modifiers",
                        expected="2 characters",
                        actual=mod
                    ))

    def _validate_claim_total(self, claim_json: dict):
        """Validate claim total matches sum of service charges"""
        clm = claim_json.get("claim", {})
        services = claim_json.get("services", [])

        if not clm.get("total_charge") or not services:
            return  # Already reported as errors

        # Calculate sum of service charges
        service_total = sum(float(svc.get("charge", 0)) for svc in services)
        claim_total = float(clm["total_charge"])

        # Allow small floating point difference
        if abs(service_total - claim_total) > 0.01:
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="VAL_050",
                message="claim.total_charge does not match sum of service charges",
                field_path="claim.total_charge",
                expected=f"${service_total:.2f}",
                actual=f"${claim_total:.2f}"
            ))


def validate_claim_json(claim_json: dict) -> ValidationReport:
    """
    Convenience function to validate claim JSON

    Args:
        claim_json: Claim data dictionary

    Returns:
        ValidationReport with validation results
    """
    validator = PreSubmissionValidator()
    return validator.validate_claim(claim_json)
