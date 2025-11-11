# SPDX-License-Identifier: MIT
"""
Claim Enrichment Agent - Auto-populate optional fields and defaults
"""
import copy
from typing import Dict, Any


class ClaimEnrichmentAgent:
    """
    Enriches claim JSON with default values and cascaded data.

    Responsibilities:
    - Set default values for optional fields
    - Cascade data from claim to service level
    - Auto-populate missing timestamps
    - Normalize data formats
    """

    def __init__(self, defaults: Dict[str, Any] = None):
        """
        Initialize enrichment agent with custom defaults.

        Args:
            defaults: Custom default values (optional)
        """
        self.defaults = defaults or {
            "pos": "41",  # Default Place of Service: Ambulance Land
            "frequency_code": "1",  # Default: Original claim
            "usage_indicator": "T",  # Default: Test mode
        }

    def enrich(self, claim_json: dict, in_place: bool = False) -> dict:
        """
        Enrich claim JSON with defaults and cascaded data.

        Args:
            claim_json: Input claim JSON
            in_place: Modify in place (default: False, returns copy)

        Returns:
            Enriched claim JSON
        """
        if not in_place:
            claim_json = copy.deepcopy(claim_json)

        # Enrich claim level
        self._enrich_claim(claim_json)

        # Enrich services
        self._enrich_services(claim_json)

        # Cascade data from claim to services
        self._cascade_data(claim_json)

        return claim_json

    def _enrich_claim(self, claim_json: dict):
        """Enrich claim-level data"""
        clm = claim_json.get("claim", {})

        # Set default POS if missing
        if not clm.get("pos"):
            clm["pos"] = self.defaults.get("pos", "41")

        # Set default frequency_code if missing and no adjustment_type
        if not clm.get("frequency_code") and not clm.get("adjustment_type"):
            clm["frequency_code"] = self.defaults.get("frequency_code", "1")

        # Set "to" date same as "from" if missing
        if clm.get("from") and not clm.get("to"):
            clm["to"] = clm["from"]

        # Set default ICD10 if missing (for testing only)
        if not clm.get("icd10"):
            clm["icd10"] = []

        # Ensure ambulance dict exists if ambulance data present
        if clm.get("ambulance") is None and any(
            clm.get(k) for k in ["patient_weight_lbs", "transport_code", "transport_reason"]
        ):
            clm["ambulance"] = {}

    def _enrich_services(self, claim_json: dict):
        """Enrich service-level data"""
        services = claim_json.get("services", [])
        claim_from = claim_json.get("claim", {}).get("from")
        claim_pos = claim_json.get("claim", {}).get("pos", self.defaults.get("pos", "41"))

        for svc in services:
            # Set DOS same as claim.from if missing
            if not svc.get("dos") and claim_from:
                svc["dos"] = claim_from

            # Set POS same as claim.pos if missing
            if not svc.get("pos"):
                svc["pos"] = claim_pos

            # Set default units to 1 if missing
            if not svc.get("units"):
                svc["units"] = 1

            # Set default emergency to False if missing
            if svc.get("emergency") is None:
                svc["emergency"] = False

            # Ensure modifiers is a list
            if svc.get("modifiers") and not isinstance(svc["modifiers"], list):
                svc["modifiers"] = [svc["modifiers"]]

    def _cascade_data(self, claim_json: dict):
        """Cascade data from claim level to service level"""
        clm = claim_json.get("claim", {})
        amb = clm.get("ambulance", {})
        services = claim_json.get("services", [])

        # Cascade trip_number from claim to services if missing
        claim_trip_number = amb.get("trip_number")
        if claim_trip_number is not None:
            for svc in services:
                if svc.get("trip_number") is None:
                    svc["trip_number"] = claim_trip_number

        # Cascade payment_status from claim to services if missing
        claim_payment_status = clm.get("payment_status")
        if claim_payment_status:
            for svc in services:
                if not svc.get("payment_status"):
                    svc["payment_status"] = claim_payment_status

        # Cascade pickup/dropoff from claim ambulance to services if missing
        claim_pickup = amb.get("pickup")
        claim_dropoff = amb.get("dropoff")

        for svc in services:
            if not svc.get("pickup") and claim_pickup:
                svc["pickup"] = claim_pickup
            if not svc.get("dropoff") and claim_dropoff:
                svc["dropoff"] = claim_dropoff


def enrich_claim(claim_json: dict, defaults: Dict[str, Any] = None, in_place: bool = False) -> dict:
    """
    Convenience function to enrich a claim.

    Args:
        claim_json: Input claim JSON
        defaults: Custom default values (optional)
        in_place: Modify in place (default: False)

    Returns:
        Enriched claim JSON

    Example:
        >>> from nemt_837p_converter import enrich_claim
        >>> enriched = enrich_claim(claim_data)
    """
    agent = ClaimEnrichmentAgent(defaults=defaults)
    return agent.enrich(claim_json, in_place=in_place)
