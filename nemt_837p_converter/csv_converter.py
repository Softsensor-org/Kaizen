"""
CSV to JSON Converter for NEMT 837P Claims

Converts CSV files with trip/claim data to the JSON format expected by the EDI builder.
"""

import csv
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import io


def parse_csv_to_json(csv_content: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Parse CSV content and convert to JSON format for EDI generation.

    CSV Format:
    - Header row required with column names
    - Each row represents a service line (trip)
    - Multiple rows with same member_id will be grouped into services array

    Required CSV Columns:
    - member_id, member_first, member_last, member_dob, member_gender
    - dos (date of service), hcpcs, charge, units
    - billing_npi, billing_name
    - payer_name, payer_id

    Optional CSV Columns:
    - member_address, member_city, member_state, member_zip
    - rendering_npi, rendering_first, rendering_last
    - supervising_npi, supervising_first, supervising_last
    - pickup_addr, pickup_city, pickup_state, pickup_zip
    - dropoff_addr, dropoff_city, dropoff_state, dropoff_zip
    - transport_code, transport_reason, patient_weight
    - trip_number, modifiers (comma-separated)
    - authorization_number, network_indicator
    - group_id, sub_group_id, class_id, plan_id, product_id

    Args:
        csv_content: CSV file content as string
        config: Optional configuration dict with defaults

    Returns:
        JSON dict ready for build_837p_from_json()
    """
    config = config or {}

    # Parse CSV
    csv_file = io.StringIO(csv_content)
    reader = csv.DictReader(csv_file)
    rows = list(reader)

    if not rows:
        raise ValueError("CSV file is empty or has no data rows")

    # Use first row for claim-level data
    first_row = rows[0]

    # Build subscriber info
    subscriber = {
        "member_id": first_row.get("member_id", "").strip(),
        "name": {
            "last": first_row.get("member_last", "").strip(),
            "first": first_row.get("member_first", "").strip(),
        },
        "dob": first_row.get("member_dob", "").strip(),
        "gender": first_row.get("member_gender", "M").strip().upper()
    }

    # Add subscriber address if provided
    if first_row.get("member_address"):
        subscriber["address"] = {
            "line1": first_row.get("member_address", "").strip(),
            "city": first_row.get("member_city", "").strip(),
            "state": first_row.get("member_state", "").strip(),
            "zip": first_row.get("member_zip", "").strip()
        }

    # Build billing provider
    billing_provider = {
        "npi": first_row.get("billing_npi", "").strip(),
        "name": first_row.get("billing_name", "").strip(),
        "taxonomy": first_row.get("billing_taxonomy", "343900000X").strip(),
        "address": {
            "line1": first_row.get("billing_address", "123 Main St").strip(),
            "city": first_row.get("billing_city", "City").strip(),
            "state": first_row.get("billing_state", "KY").strip(),
            "zip": first_row.get("billing_zip", "40202").strip()
        }
    }

    # Build payer/receiver
    receiver = {
        "payer_name": first_row.get("payer_name", "").strip(),
        "payer_id": first_row.get("payer_id", "").strip()
    }

    # Build claim-level data
    claim_data = {
        "clm_number": first_row.get("claim_number", f"CLM-{first_row.get('member_id', 'UNK')}-001").strip(),
        "from": first_row.get("dos", datetime.now().strftime("%Y-%m-%d")).strip(),
        "pos": first_row.get("pos", "41").strip(),
        "frequency": first_row.get("frequency", "1").strip(),
    }

    # Calculate total charge from all service rows
    total_charge = sum(float(row.get("charge", 0)) for row in rows)
    claim_data["total_charge"] = total_charge

    # Phase 3: Payment/lifecycle fields with defaults
    claim_data["payment_status"] = first_row.get("payment_status", "P").strip() if first_row.get("payment_status") else "P"
    claim_data["submission_channel"] = first_row.get("submission_channel", "ELECTRONIC").strip() if first_row.get("submission_channel") else "ELECTRONIC"

    # Portal tracking fields
    claim_data["subscriber_internal_id"] = first_row.get("subscriber_internal_id") or first_row.get("member_id", "")
    claim_data["ip_address"] = first_row.get("ip_address", "192.168.1.100")
    claim_data["user_id"] = first_row.get("user_id", "PORTAL_USER_001")

    # Calculate lifecycle dates relative to DOS if not in CSV
    dos_str = first_row.get("dos", "")
    if dos_str:
        try:
            dos_date = datetime.strptime(dos_str.strip(), "%Y-%m-%d")
            claim_data["received_date"] = first_row.get("received_date", (dos_date + timedelta(days=1)).strftime("%Y-%m-%d"))
            claim_data["adjudication_date"] = first_row.get("adjudication_date", (dos_date + timedelta(days=4)).strftime("%Y-%m-%d"))
            claim_data["paid_date"] = first_row.get("paid_date", (dos_date + timedelta(days=9)).strftime("%Y-%m-%d"))
        except:
            pass  # Skip date calculation if DOS is invalid

    # Financial amounts - use total charge as allowed amount by default
    claim_data["allowed_amount"] = float(first_row.get("allowed_amount", total_charge)) if first_row.get("allowed_amount") else total_charge
    claim_data["not_covered_amount"] = float(first_row.get("not_covered_amount", 0)) if first_row.get("not_covered_amount") else 0.0
    claim_data["patient_paid_amount"] = float(first_row.get("patient_paid_amount", 0)) if first_row.get("patient_paid_amount") else 0.0

    # Add member group if provided
    if first_row.get("group_id"):
        claim_data["member_group"] = {
            "group_id": first_row.get("group_id", "").strip(),
            "sub_group_id": first_row.get("sub_group_id", "").strip(),
            "class_id": first_row.get("class_id", "").strip(),
            "plan_id": first_row.get("plan_id", "").strip(),
            "product_id": first_row.get("product_id", "").strip()
        }

    # Add ambulance/transport data if provided
    if first_row.get("transport_code") or first_row.get("patient_weight"):
        ambulance = {}
        if first_row.get("transport_code"):
            ambulance["transport_code"] = first_row.get("transport_code").strip()
        if first_row.get("transport_reason"):
            ambulance["transport_reason"] = first_row.get("transport_reason").strip()
        if first_row.get("patient_weight"):
            ambulance["patient_weight_lbs"] = float(first_row.get("patient_weight"))
            ambulance["weight_unit"] = "LB"
        if first_row.get("trip_number"):
            ambulance["trip_number"] = int(first_row.get("trip_number"))

        # Claim-level pickup/dropoff
        if first_row.get("pickup_addr"):
            ambulance["pickup"] = {
                "addr": first_row.get("pickup_addr", "").strip(),
                "city": first_row.get("pickup_city", "").strip(),
                "state": first_row.get("pickup_state", "").strip(),
                "zip": first_row.get("pickup_zip", "").strip()
            }
        if first_row.get("dropoff_addr"):
            ambulance["dropoff"] = {
                "addr": first_row.get("dropoff_addr", "").strip(),
                "city": first_row.get("dropoff_city", "").strip(),
                "state": first_row.get("dropoff_state", "").strip(),
                "zip": first_row.get("dropoff_zip", "").strip()
            }

        claim_data["ambulance"] = ambulance

    # Add authorization if provided
    if first_row.get("authorization_number"):
        claim_data["authorization_number"] = first_row.get("authorization_number").strip()

    # Add network indicator if provided
    if first_row.get("network_indicator"):
        claim_data["network_indicator"] = first_row.get("network_indicator").strip()

    # Add rendering network indicator if rendering provider exists
    if first_row.get("rendering_npi"):
        claim_data["rendering_network_indicator"] = first_row.get("rendering_network_indicator", first_row.get("network_indicator", "I")).strip()

    # Add claim-level supervising provider if provided
    if first_row.get("supervising_npi"):
        claim_data["supervising_provider"] = {
            "npi": first_row.get("supervising_npi").strip(),
            "last": first_row.get("supervising_last", "").strip(),
            "first": first_row.get("supervising_first", "").strip()
        }

    # Build rendering provider if provided
    rendering_provider = None
    if first_row.get("rendering_npi"):
        rendering_provider = {
            "npi": first_row.get("rendering_npi").strip(),
            "last": first_row.get("rendering_last", "").strip(),
            "first": first_row.get("rendering_first", "").strip()
        }

    # Build services array from all rows
    services = []
    for row in rows:
        service = {
            "hcpcs": row.get("hcpcs", "").strip(),
            "charge": float(row.get("charge", 0)),
            "units": float(row.get("units", 1)),
        }

        # Add modifiers if provided
        if row.get("modifiers"):
            modifiers = [m.strip() for m in row.get("modifiers", "").split(",") if m.strip()]
            if modifiers:
                service["modifiers"] = modifiers

        # Add DOS if different from claim-level
        if row.get("dos") and row.get("dos") != first_row.get("dos"):
            service["dos"] = row.get("dos").strip()

        # Service-level pickup/dropoff (overrides claim-level)
        if row.get("service_pickup_addr"):
            service["pickup"] = {
                "addr": row.get("service_pickup_addr", "").strip(),
                "city": row.get("service_pickup_city", "").strip(),
                "state": row.get("service_pickup_state", "").strip(),
                "zip": row.get("service_pickup_zip", "").strip()
            }
        if row.get("service_dropoff_addr"):
            service["dropoff"] = {
                "addr": row.get("service_dropoff_addr", "").strip(),
                "city": row.get("service_dropoff_city", "").strip(),
                "state": row.get("service_dropoff_state", "").strip(),
                "zip": row.get("service_dropoff_zip", "").strip()
            }

        # Service-level trip number
        if row.get("service_trip_number"):
            service["trip_number"] = int(row.get("service_trip_number"))

        # Phase 3: Service-level payment status
        service["payment_status"] = row.get("payment_status", "P").strip() if row.get("payment_status") else "P"

        services.append(service)

    # Build complete JSON structure
    result = {
        "submitter": {
            "name": config.get("submitter_name", "Kaizen Health"),
            "id": config.get("submitter_id", "KAIZEN01"),
            "contact": config.get("submitter_contact", "Claims Department"),
            "phone": config.get("submitter_phone", "5555551234")
        },
        "receiver": receiver,
        "billing_provider": billing_provider,
        "subscriber": subscriber,
        "claim": claim_data,
        "services": services
    }

    # Add rendering provider if provided
    if rendering_provider:
        result["rendering_provider"] = rendering_provider

    return result


def convert_csv_file(csv_path: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Load CSV file and convert to JSON format.

    Args:
        csv_path: Path to CSV file
        config: Optional configuration dict

    Returns:
        JSON dict ready for build_837p_from_json()
    """
    with open(csv_path, 'r', encoding='utf-8') as f:
        csv_content = f.read()

    return parse_csv_to_json(csv_content, config)
