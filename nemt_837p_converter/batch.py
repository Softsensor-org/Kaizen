"""
Agent 5: Batch Processor

Handles batch-level processing for NEMT claims:
- Automatic grouping/splitting based on state requirements
- Scenario 1: Multiple trips same DOS/provider → one claim, multiple service lines
- Scenario 2: Multiple trips same DOS/different providers → separate claims
- Duplicate claim validation
- Submission channel aggregation
"""

from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import hashlib


class BatchSeverity(Enum):
    """Batch processing issue severity"""
    ERROR = "ERROR"  # Will cause batch rejection
    WARNING = "WARNING"  # May cause issues
    INFO = "INFO"  # Informational


@dataclass
class BatchIssue:
    """Single batch processing issue"""
    severity: BatchSeverity
    code: str  # Unique code (e.g., "BATCH_001")
    message: str  # Human-readable description
    trip_indices: List[int] = field(default_factory=list)  # Trip record indices affected
    field_path: Optional[str] = None


@dataclass
class BatchReport:
    """Batch processing report"""
    success: bool  # True if batch can be submitted
    claims_generated: int = 0  # Number of claims created
    trips_processed: int = 0  # Number of trip records processed
    errors: List[BatchIssue] = field(default_factory=list)
    warnings: List[BatchIssue] = field(default_factory=list)
    info: List[BatchIssue] = field(default_factory=list)

    def add_issue(self, issue: BatchIssue):
        """Add issue to appropriate list based on severity"""
        if issue.severity == BatchSeverity.ERROR:
            self.errors.append(issue)
            self.success = False
        elif issue.severity == BatchSeverity.WARNING:
            self.warnings.append(issue)
        else:
            self.info.append(issue)

    def __str__(self):
        lines = [f"Batch Processing Report: {'SUCCESS' if self.success else 'FAILED'}"]
        lines.append(f"Claims Generated: {self.claims_generated}")
        lines.append(f"Trips Processed: {self.trips_processed}")

        if self.errors:
            lines.append(f"\n{len(self.errors)} Errors:")
            for err in self.errors:
                lines.append(f"  [{err.code}] {err.message}")
                if err.trip_indices:
                    lines.append(f"    Affected trips: {err.trip_indices}")

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
class BatchConfig:
    """Configuration for batch processing"""
    claim_number_prefix: str = "CLM"  # Prefix for auto-generated claim numbers
    validate_duplicates: bool = True  # Check for duplicate claims
    enforce_back_to_back_mileage: bool = True  # Enforce mileage after service
    auto_aggregate_submission_channel: bool = True  # ELECTRONIC if any trip is ELECTRONIC
    frequency_code_default: str = "1"  # Default frequency code (1=original)


class BatchProcessor:
    """
    Agent 5: Batch Processor

    Processes batches of trip records and groups them into claims according to
    state/provider requirements.
    """

    def __init__(self, config: Optional[BatchConfig] = None):
        """Initialize batch processor"""
        self.config = config or BatchConfig()
        self.report = BatchReport(success=True)

    def process_batch(self, trips: List[Dict[str, Any]],
                     common_data: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], BatchReport]:
        """
        Process batch of trip records into properly grouped claims

        Args:
            trips: List of trip record dictionaries
            common_data: Common data to apply to all claims (billing provider, payer, etc.)

        Returns:
            Tuple of (claims list, batch report)
        """
        self.report = BatchReport(success=True)
        self.report.trips_processed = len(trips)

        if not trips:
            self.report.add_issue(BatchIssue(
                severity=BatchSeverity.ERROR,
                code="BATCH_001",
                message="No trips provided in batch"
            ))
            return [], self.report

        # Validate trip records
        if not self._validate_trips(trips):
            return [], self.report

        # Group trips by DOS + Member + Rendering Provider (Scenario 1 & 2)
        grouped_trips = self._group_trips(trips)

        # Generate claims from groups
        claims = self._generate_claims(grouped_trips, common_data or {})

        # Validate for duplicates
        if self.config.validate_duplicates:
            self._validate_duplicates(claims)

        # Validate service/mileage back-to-back
        if self.config.enforce_back_to_back_mileage:
            self._validate_mileage_ordering(claims)

        self.report.claims_generated = len(claims)

        return claims, self.report

    def _validate_trips(self, trips: List[Dict[str, Any]]) -> bool:
        """Validate trip records have required fields"""
        for i, trip in enumerate(trips):
            # Required fields
            if not trip.get("dos"):
                self.report.add_issue(BatchIssue(
                    severity=BatchSeverity.ERROR,
                    code="BATCH_002",
                    message=f"Trip {i}: Missing required field 'dos'",
                    trip_indices=[i],
                    field_path="dos"
                ))

            if not trip.get("member"):
                self.report.add_issue(BatchIssue(
                    severity=BatchSeverity.ERROR,
                    code="BATCH_003",
                    message=f"Trip {i}: Missing required field 'member'",
                    trip_indices=[i],
                    field_path="member"
                ))

            if not trip.get("service"):
                self.report.add_issue(BatchIssue(
                    severity=BatchSeverity.ERROR,
                    code="BATCH_004",
                    message=f"Trip {i}: Missing required field 'service'",
                    trip_indices=[i],
                    field_path="service"
                ))
            elif not trip["service"].get("hcpcs"):
                self.report.add_issue(BatchIssue(
                    severity=BatchSeverity.ERROR,
                    code="BATCH_005",
                    message=f"Trip {i}: Missing required field 'service.hcpcs'",
                    trip_indices=[i],
                    field_path="service.hcpcs"
                ))

        return self.report.success

    def _group_trips(self, trips: List[Dict[str, Any]]) -> Dict[Tuple, List[Tuple[int, Dict]]]:
        """
        Group trips by (DOS, Member ID, Rendering Provider NPI, Billing Provider NPI)

        Implements:
        - Scenario 1: Same DOS + same provider → one claim with multiple service lines
        - Scenario 2: Same DOS + different providers → separate claims

        Returns:
            Dict mapping group key to list of (trip_index, trip) tuples
        """
        groups = defaultdict(list)

        for i, trip in enumerate(trips):
            # Extract grouping key
            dos = trip.get("dos", "")
            member_id = trip.get("member", {}).get("member_id", "")
            rendering_npi = trip.get("rendering_provider", {}).get("npi", "")
            billing_npi = trip.get("billing_provider", {}).get("npi", "")

            group_key = (dos, member_id, rendering_npi, billing_npi)
            groups[group_key].append((i, trip))

        # Log grouping info
        for group_key, group_trips in groups.items():
            dos, member_id, rendering_npi, billing_npi = group_key
            if len(group_trips) > 1:
                trip_indices = [idx for idx, _ in group_trips]
                self.report.add_issue(BatchIssue(
                    severity=BatchSeverity.INFO,
                    code="BATCH_100",
                    message=f"Grouped {len(group_trips)} trips into one claim (DOS={dos}, Member={member_id}, Provider={rendering_npi})",
                    trip_indices=trip_indices
                ))

        return groups

    def _generate_claims(self, grouped_trips: Dict[Tuple, List[Tuple[int, Dict]]],
                        common_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate claim JSONs from grouped trips"""
        claims = []
        claim_counter = 1

        for group_key, group_trips in grouped_trips.items():
            dos, member_id, rendering_npi, billing_npi = group_key

            # Get first trip as template
            first_idx, first_trip = group_trips[0]

            # Build claim structure
            claim = {
                "billing_provider": first_trip.get("billing_provider") or common_data.get("billing_provider", {}),
                "subscriber": first_trip.get("member") or first_trip.get("subscriber", {}),
                "payer": first_trip.get("payer") or common_data.get("payer", {}),
                "claim": {
                    "clm_number": self._generate_claim_number(claim_counter),
                    "total_charge": 0.0,
                    "pos": first_trip.get("pos") or common_data.get("pos", "41"),
                    "frequency_code": first_trip.get("frequency_code", self.config.frequency_code_default),
                    "from": dos,
                    "to": dos,
                },
                "services": []
            }

            # Aggregate submission channels (any ELECTRONIC → ELECTRONIC)
            submission_channels = set()

            # Add all trips as service lines
            for trip_idx, trip in group_trips:
                service = trip["service"].copy()

                # Add service-level fields from trip
                if trip.get("pickup"):
                    service["pickup"] = trip["pickup"]
                if trip.get("dropoff"):
                    service["dropoff"] = trip["dropoff"]
                if trip.get("dos"):
                    service["dos"] = trip["dos"]
                if trip.get("trip_type"):
                    service["trip_type"] = trip["trip_type"]
                if trip.get("trip_leg"):
                    service["trip_leg"] = trip["trip_leg"]
                if trip.get("payment_status"):
                    service["payment_status"] = trip["payment_status"]
                if trip.get("adjudication"):
                    service["adjudication"] = trip["adjudication"]
                if trip.get("supervising_provider"):
                    service["supervising_provider"] = trip["supervising_provider"]
                if trip.get("emergency") is not None:
                    service["emergency"] = trip["emergency"]

                claim["services"].append(service)
                claim["claim"]["total_charge"] += float(service.get("charge", 0.0))

                # Track submission channel
                if trip.get("submission_channel"):
                    submission_channels.add(trip["submission_channel"])

            # Aggregate submission channel
            if self.config.auto_aggregate_submission_channel and submission_channels:
                # If any trip is ELECTRONIC, mark entire claim as ELECTRONIC
                if "ELECTRONIC" in submission_channels:
                    claim["claim"]["submission_channel"] = "ELECTRONIC"
                else:
                    # All PAPER or other
                    claim["claim"]["submission_channel"] = list(submission_channels)[0]

            # Copy claim-level fields from first trip if available
            if first_trip.get("ambulance"):
                claim["claim"]["ambulance"] = first_trip["ambulance"].copy()
            if first_trip.get("auth_number"):
                claim["claim"]["auth_number"] = first_trip["auth_number"]
            if first_trip.get("patient_account"):
                claim["claim"]["patient_account"] = first_trip["patient_account"]
            if first_trip.get("rendering_network_indicator"):
                claim["claim"]["rendering_network_indicator"] = first_trip["rendering_network_indicator"]
            if first_trip.get("member_group"):
                claim["claim"]["member_group"] = first_trip["member_group"]
            if first_trip.get("ip_address"):
                claim["claim"]["ip_address"] = first_trip["ip_address"]
            if first_trip.get("user_id"):
                claim["claim"]["user_id"] = first_trip["user_id"]
            if first_trip.get("subscriber_internal_id"):
                claim["claim"]["subscriber_internal_id"] = first_trip["subscriber_internal_id"]

            # Phase 3: Payment/lifecycle fields
            if first_trip.get("payment_status"):
                claim["claim"]["payment_status"] = first_trip["payment_status"]
            if first_trip.get("received_date"):
                claim["claim"]["received_date"] = first_trip["received_date"]
            if first_trip.get("receipt_date"):  # Alternate field name
                claim["claim"]["receipt_date"] = first_trip["receipt_date"]
            if first_trip.get("adjudication_date"):
                claim["claim"]["adjudication_date"] = first_trip["adjudication_date"]
            if first_trip.get("paid_date"):
                claim["claim"]["paid_date"] = first_trip["paid_date"]
            if first_trip.get("allowed_amount") is not None:
                claim["claim"]["allowed_amount"] = first_trip["allowed_amount"]
            if first_trip.get("not_covered_amount") is not None:
                claim["claim"]["not_covered_amount"] = first_trip["not_covered_amount"]
            if first_trip.get("patient_paid_amount") is not None:
                claim["claim"]["patient_paid_amount"] = first_trip["patient_paid_amount"]

            # Rendering provider (if different from billing)
            if first_trip.get("rendering_provider"):
                claim["rendering_provider"] = first_trip["rendering_provider"]

            claims.append(claim)
            claim_counter += 1

        return claims

    def _generate_claim_number(self, counter: int) -> str:
        """Generate unique claim number"""
        import time
        timestamp = str(int(time.time()))[-6:]  # Last 6 digits of timestamp
        return f"{self.config.claim_number_prefix}{timestamp}{counter:04d}"

    def _validate_duplicates(self, claims: List[Dict[str, Any]]):
        """
        Validate for duplicate claims using NEMIS criteria per §2.1.10:
        - CLM01 (claim number)
        - CLM05-3 (frequency code)
        - REF*F8 (original claim number for adjustments)
        """
        seen_combinations: Set[Tuple[str, str, str]] = set()

        for i, claim in enumerate(claims):
            clm_number = claim.get("claim", {}).get("clm_number", "")
            freq_code = claim.get("claim", {}).get("frequency_code", "1")  # Default to "1" (original)
            original_claim = claim.get("claim", {}).get("original_claim_number", "")  # Per §2.1.10, REF*F8 is original claim number

            combo = (clm_number, freq_code, original_claim)

            if combo in seen_combinations:
                self.report.add_issue(BatchIssue(
                    severity=BatchSeverity.ERROR,
                    code="BATCH_010",
                    message=f"Duplicate claim detected per NEMIS criteria (§2.1.10): CLM01={clm_number}, CLM05-3={freq_code}, REF*F8={original_claim}",
                    field_path=f"claims[{i}]"
                ))

            seen_combinations.add(combo)

    def _validate_mileage_ordering(self, claims: List[Dict[str, Any]]):
        """
        Validate service/mileage code back-to-back ordering

        Mileage codes (A0380, A0390, A0425, A0435) must immediately follow
        their corresponding service codes
        """
        mileage_codes = {"A0380", "A0390", "A0425", "A0435", "T2049"}

        for claim_idx, claim in enumerate(claims):
            services = claim.get("services", [])

            for i, svc in enumerate(services):
                hcpcs = svc.get("hcpcs", "")

                # If this is a mileage code, check that previous service was NOT a mileage code
                if hcpcs in mileage_codes:
                    if i == 0:
                        self.report.add_issue(BatchIssue(
                            severity=BatchSeverity.WARNING,
                            code="BATCH_011",
                            message=f"Claim {claim_idx}: Mileage code {hcpcs} appears first (should follow service code)",
                            field_path=f"claims[{claim_idx}].services[{i}]"
                        ))
                    else:
                        prev_hcpcs = services[i-1].get("hcpcs", "")
                        if prev_hcpcs in mileage_codes:
                            self.report.add_issue(BatchIssue(
                                severity=BatchSeverity.WARNING,
                                code="BATCH_012",
                                message=f"Claim {claim_idx}: Consecutive mileage codes ({prev_hcpcs}, {hcpcs}) - should be service then mileage",
                                field_path=f"claims[{claim_idx}].services[{i}]"
                            ))

                # If this is a service code, check if next is mileage
                elif i < len(services) - 1:
                    next_hcpcs = services[i+1].get("hcpcs", "")
                    # Info: service followed by mileage (correct pattern)
                    if next_hcpcs in mileage_codes:
                        self.report.add_issue(BatchIssue(
                            severity=BatchSeverity.INFO,
                            code="BATCH_101",
                            message=f"Claim {claim_idx}: Service {hcpcs} correctly followed by mileage {next_hcpcs}",
                            field_path=f"claims[{claim_idx}].services[{i}]"
                        ))


def process_batch(trips: List[Dict[str, Any]],
                 common_data: Optional[Dict[str, Any]] = None,
                 config: Optional[BatchConfig] = None) -> Tuple[List[Dict[str, Any]], BatchReport]:
    """
    Convenience function to process batch of trips

    Args:
        trips: List of trip record dictionaries
        common_data: Common data to apply to all claims
        config: Batch processing configuration

    Returns:
        Tuple of (claims list, batch report)
    """
    processor = BatchProcessor(config)
    return processor.process_batch(trips, common_data)
