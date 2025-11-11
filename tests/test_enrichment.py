# SPDX-License-Identifier: MIT
"""
Tests for claim enrichment functionality
"""
import pytest
from nemt_837p_converter import ClaimEnrichmentAgent, enrich_claim


def test_enrich_adds_default_pos(minimal_claim_data):
    """Test that enrichment adds default POS code"""
    assert "pos" not in minimal_claim_data["claim"]

    enriched = enrich_claim(minimal_claim_data)

    assert enriched["claim"]["pos"] == "41"


def test_enrich_adds_default_frequency_code(minimal_claim_data):
    """Test that enrichment adds default frequency code"""
    assert "frequency_code" not in minimal_claim_data["claim"]

    enriched = enrich_claim(minimal_claim_data)

    assert enriched["claim"]["frequency_code"] == "1"


def test_enrich_adds_to_date(minimal_claim_data):
    """Test that enrichment adds 'to' date same as 'from' if missing"""
    assert "to" not in minimal_claim_data["claim"]

    enriched = enrich_claim(minimal_claim_data)

    assert enriched["claim"]["to"] == minimal_claim_data["claim"]["from"]


def test_enrich_adds_service_dos(minimal_claim_data):
    """Test that enrichment adds DOS to services from claim.from"""
    assert "dos" not in minimal_claim_data["services"][0]

    enriched = enrich_claim(minimal_claim_data)

    assert enriched["services"][0]["dos"] == minimal_claim_data["claim"]["from"]


def test_enrich_adds_service_pos(minimal_claim_data):
    """Test that enrichment adds POS to services from claim.pos"""
    enriched = enrich_claim(minimal_claim_data)

    assert enriched["services"][0]["pos"] == "41"


def test_enrich_adds_default_units(minimal_claim_data):
    """Test that enrichment adds default units=1"""
    assert "units" not in minimal_claim_data["services"][0]

    enriched = enrich_claim(minimal_claim_data)

    assert enriched["services"][0]["units"] == 1


def test_enrich_adds_default_emergency_false(minimal_claim_data):
    """Test that enrichment adds default emergency=False"""
    assert "emergency" not in minimal_claim_data["services"][0]

    enriched = enrich_claim(minimal_claim_data)

    assert enriched["services"][0]["emergency"] is False


def test_enrich_cascades_trip_number(valid_claim_data):
    """Test that enrichment cascades trip_number from claim to services"""
    valid_claim_data["claim"]["ambulance"] = {"trip_number": 123}
    assert "trip_number" not in valid_claim_data["services"][0]

    enriched = enrich_claim(valid_claim_data)

    assert enriched["services"][0]["trip_number"] == 123


def test_enrich_does_not_override_service_trip_number(valid_claim_data):
    """Test that service-level trip_number takes precedence"""
    valid_claim_data["claim"]["ambulance"] = {"trip_number": 123}
    valid_claim_data["services"][0]["trip_number"] = 456

    enriched = enrich_claim(valid_claim_data)

    assert enriched["services"][0]["trip_number"] == 456


def test_enrich_cascades_payment_status(valid_claim_data):
    """Test that enrichment cascades payment_status from claim to services"""
    valid_claim_data["claim"]["payment_status"] = "P"
    assert "payment_status" not in valid_claim_data["services"][0]

    enriched = enrich_claim(valid_claim_data)

    assert enriched["services"][0]["payment_status"] == "P"


def test_enrich_cascades_pickup_dropoff(valid_claim_data):
    """Test that enrichment cascades pickup/dropoff from claim to services"""
    valid_claim_data["claim"]["ambulance"] = {
        "pickup": {"addr": "123 Start St", "city": "Start", "state": "NY", "zip": "12345"},
        "dropoff": {"addr": "456 End St", "city": "End", "state": "NY", "zip": "54321"}
    }

    enriched = enrich_claim(valid_claim_data)

    assert enriched["services"][0]["pickup"] == valid_claim_data["claim"]["ambulance"]["pickup"]
    assert enriched["services"][0]["dropoff"] == valid_claim_data["claim"]["ambulance"]["dropoff"]


def test_enrich_does_not_modify_original(minimal_claim_data):
    """Test that enrichment doesn't modify original data by default"""
    original_pos = minimal_claim_data["claim"].get("pos")

    enriched = enrich_claim(minimal_claim_data)

    # Original should not be modified
    assert minimal_claim_data["claim"].get("pos") == original_pos
    # Enriched should have default
    assert enriched["claim"]["pos"] == "41"


def test_enrich_in_place_modifies_original(minimal_claim_data):
    """Test that in_place=True modifies original data"""
    enriched = enrich_claim(minimal_claim_data, in_place=True)

    # Both should have the default
    assert minimal_claim_data["claim"]["pos"] == "41"
    assert enriched["claim"]["pos"] == "41"
    # They should be the same object
    assert enriched is minimal_claim_data


def test_enrich_with_custom_defaults(minimal_claim_data):
    """Test enrichment with custom default values"""
    custom_defaults = {
        "pos": "42",  # Ambulance Air/Water
        "frequency_code": "7"  # Replacement
    }

    enriched = enrich_claim(minimal_claim_data, defaults=custom_defaults)

    assert enriched["claim"]["pos"] == "42"
    assert enriched["claim"]["frequency_code"] == "7"


def test_enrichment_agent_reuse():
    """Test that ClaimEnrichmentAgent can be reused"""
    agent = ClaimEnrichmentAgent(defaults={"pos": "42"})

    claim1 = {"claim": {}, "services": []}
    claim2 = {"claim": {}, "services": []}

    enriched1 = agent.enrich(claim1)
    enriched2 = agent.enrich(claim2)

    assert enriched1["claim"]["pos"] == "42"
    assert enriched2["claim"]["pos"] == "42"
