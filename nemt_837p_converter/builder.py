# SPDX-License-Identifier: MIT
import datetime
import re
from .x12 import X12Writer, ControlNumbers
from .codes import (
    POS_CODES, NEMT_HCPCS_CODES, HCPCS_MODIFIERS, FREQUENCY_CODES,
    TRANSPORT_CODES, TRANSPORT_REASON_CODES, WEIGHT_UNITS, GENDER_CODES,
    TRIP_TYPES, TRIP_LEGS, NETWORK_INDICATORS, SUBMISSION_CHANNELS,
    PAYMENT_STATUS_CODES, validate_code, validate_state, validate_zip
)
from .payers import get_payer_config
from .validation import validate_claim_json as _validate_with_agent1, ValidationReport

class ValidationError(Exception):
    """Raised when input JSON validation fails"""
    pass

def validate_claim_json(claim_json: dict):
    """
    Validate required fields, formats, and code values in claim JSON

    Uses Agent 1 (Pre-Submission Validator) with backward-compatible exception raising.

    Raises:
        ValidationError: If validation fails with error-level issues
    """
    # Use Agent 1 for validation
    report = _validate_with_agent1(claim_json)

    # Convert ValidationReport errors to exception for backward compatibility
    if not report.is_valid:
        error_messages = [f"{err.field_path}: {err.message}" for err in report.errors]
        raise ValidationError("; ".join(error_messages))

class Config:
    def __init__(self, sender_qual="ZZ", sender_id="SENDERID", receiver_qual="ZZ", receiver_id="RECEIVERID",
                 usage_indicator="T", gs_sender_code="SENDER", gs_receiver_code="RECEIVER", component_sep=":",
                 payer_config=None, use_cr1_locations=True):
        self.sender_qual = sender_qual
        self.sender_id = sender_id
        self.receiver_qual = receiver_qual
        self.receiver_id = receiver_id
        self.usage_indicator = usage_indicator
        self.gs_sender_code = gs_sender_code
        self.gs_receiver_code = gs_receiver_code
        self.component_sep = component_sep
        self.payer_config = payer_config  # PayerConfig object for payer-specific settings
        self.use_cr1_locations = use_cr1_locations  # Per §2.1.8: Use CR109/CR110 for pickup/dropoff in CR1 (DEFAULT per Kaizen vendor spec)

def _fmt_d8(s):
    if not s: return None
    return s.replace("-", "")

def _pos(value):
    v = str(value).zfill(2)
    return v[-2:]

def _yesno(v):
    if v is None: return ""
    return "Y" if str(v).lower() in ("y","yes","true","1") else "N"

def build_837p_from_json(claim_json: dict, cfg: Config, cn: ControlNumbers = None) -> str:
    # Validate input before processing
    validate_claim_json(claim_json)

    if cn is None: cn = ControlNumbers()
    w = X12Writer(component_sep=cfg.component_sep)
    now = datetime.datetime.now()

    # Get payer configuration
    recv = claim_json["receiver"]
    if cfg.payer_config:
        payer = cfg.payer_config
    else:
        # Get payer config from receiver data, or use default
        payer = get_payer_config(
            payer_id=recv.get("payer_id"),
            payer_name=recv.get("payer_name")
        )

    isa_cn = cn.next_isa(); gs_cn = cn.next_gs(); st_cn = cn.next_st()
    w.build_ISA(cfg.sender_qual, cfg.sender_id, cfg.receiver_qual, cfg.receiver_id, cfg.usage_indicator, isa_cn, now, now, "00501")
    w.build_GS("HC", cfg.gs_sender_code, cfg.gs_receiver_code, now, now, gs_cn, "005010X222A1")
    st_index = len(w._segments) + 1
    w.build_ST(control_number=st_cn, impl_guide_version="005010X222A1")

    clm = claim_json["claim"]

    # Transaction Set Header
    # BHT - Beginning of Hierarchical Transaction
    w.segment("BHT", "0019", "00", (clm.get("clm_number") or "REF")[:30], now.strftime("%Y%m%d"), now.strftime("%H%M"), "CH")

    # Loop 1000A - Submitter Name
    subm = claim_json["submitter"]
    w.segment("NM1", "41", "2", subm.get("name",""), "", "", "", "", subm.get("id_qualifier","ZZ"), subm.get("id") or subm.get("sender_id",""))
    if subm.get("contact_name") or subm.get("contact_phone"):
        w.segment("PER", "IC", subm.get("contact_name",""), "TE", subm.get("contact_phone",""))

    # Loop 1000B - Receiver Name
    w.segment("NM1", "40", "2", payer.payer_name or recv.get("payer_name","RECEIVER"), "", "", "", "", "46", cfg.receiver_id)

    # Loop 2000A - Billing Provider Hierarchical Level
    w.segment("HL", "1", "", "20", "1")
    bp = claim_json["billing_provider"]
    w.segment("NM1", "85", "2", bp["name"], "", "", "", "", "XX", bp["npi"])
    w.segment("N3", bp["address"]["line1"])
    w.segment("N4", bp["address"]["city"], bp["address"]["state"], bp["address"]["zip"])
    if bp.get("tax_id"): w.segment("REF", "EI", bp["tax_id"])
    if bp.get("taxonomy"): w.segment("PRV", "BI", "PXC", bp["taxonomy"])

    # Loop 2000B - Subscriber Hierarchical Level
    w.segment("HL", "2", "1", "22", "0")
    sbr_rel = "18" if claim_json["subscriber"].get("relationship","self") == "self" else "01"
    w.segment("SBR", "P", sbr_rel, "", "", "", "", "", "MC")

    subr = claim_json["subscriber"]
    w.segment("NM1", "IL", "1", subr["name"]["last"], subr["name"]["first"], "", "", "", "MI", subr["member_id"])
    if "address" in subr:
        w.segment("N3", subr["address"]["line1"])
        w.segment("N4", subr["address"]["city"], subr["address"]["state"], subr["address"]["zip"])
    if subr.get("dob") or subr.get("sex"):
        w.segment("DMG", "D8", _fmt_d8(subr.get("dob","")), subr.get("sex",""))
    w.segment("NM1", "PR", "2", payer.payer_name, "", "", "", "", payer.default_qualifier, payer.payer_id)

    # Loop 2300 - Claim Information
    pos = _pos(clm.get("pos","41"))
    freq = clm.get("frequency_code") or ("8" if clm.get("adjustment_type")=="void" else ("7" if clm.get("adjustment_type")=="replacement" else "1"))
    clm05 = w.composite(pos, "B", freq)
    w.segment("CLM", clm.get("clm_number",""), f"{float(clm.get('total_charge',0.0)):.2f}", "", "", clm05, "Y", "A", "Y", "Y", "P", "OA")

    from_d = clm.get("from"); to_d = clm.get("to") or from_d
    if from_d and to_d:
        if from_d == to_d: w.segment("DTP", "434", "D8", _fmt_d8(from_d))
        else: w.segment("DTP", "434", "RD8", f"{_fmt_d8(from_d)}-{_fmt_d8(to_d)}")

    icds = clm.get("icd10", [])
    if icds:
        comps = [w.composite("ABK", icds[0])] + [w.composite("ABF", x) for x in icds[1:]]
        w.segment("HI", *comps)

    if clm.get("auth_number"): w.segment("REF", "G1", clm["auth_number"])
    if clm.get("tracking_number"): w.segment("REF", "D9", clm["tracking_number"])
    if clm.get("patient_account"): w.segment("REF", "F8", clm["patient_account"])

    # Per §2.1.6: Adjustment Reporting - REF*F8 with original claim number for void/replacement
    if freq in ("7", "8") and clm.get("original_claim_number"):
        w.segment("REF", "F8", clm["original_claim_number"])

    # Per §2.1.7: Payment Date Reporting
    if clm.get("receipt_date"):
        w.segment("DTP", "050", "D8", _fmt_d8(clm["receipt_date"]))  # Date of Receipt
    if clm.get("adjudication_date"):
        w.segment("DTP", "036", "D8", _fmt_d8(clm["adjudication_date"]))  # Date of Adjudication
    if clm.get("paid_date"):
        w.segment("DTP", "573", "D8", _fmt_d8(clm["paid_date"]))  # Date of Payment

    # Per §2.1.7: Payment Amount Reporting
    if clm.get("allowed_amount") is not None:
        w.segment("AMT", "D", f"{float(clm['allowed_amount']):.2f}")  # Approved/Allowed Amount
    if clm.get("not_covered_amount") is not None:
        w.segment("AMT", "A8", f"{float(clm['not_covered_amount']):.2f}")  # Not Covered Amount
    if clm.get("patient_amount_paid") is not None:
        w.segment("AMT", "F5", f"{float(clm['patient_amount_paid']):.2f}")  # Patient Amount Paid

    # Coordination of Benefits (COB) - Other Payer Amounts
    if clm.get("other_payer_paid_amount") is not None:
        w.segment("AMT", "EAF", f"{float(clm['other_payer_paid_amount']):.2f}")  # Other Payer - Primary/Secondary Amount Paid
    if clm.get("other_payer_allowed_amount") is not None:
        w.segment("AMT", "B6", f"{float(clm['other_payer_allowed_amount']):.2f}")  # Other Payer - Allowed Amount
    if clm.get("other_payer_coverage_amount") is not None:
        w.segment("AMT", "AU", f"{float(clm['other_payer_coverage_amount']):.2f}")  # Other Payer - Coverage Amount
    if clm.get("patient_responsibility_amount") is not None:
        w.segment("AMT", "F2", f"{float(clm['patient_responsibility_amount']):.2f}")  # Patient Responsibility Amount

    # Per §2.1.5: Adjustment Reason Codes - CAS segments at claim level
    # Auto-generate CAS for denied claims if not provided
    cas_segments = clm.get("cas_segments", [])
    if clm.get("payment_status") == "D" and not cas_segments:
        # Auto-generate denial CAS segment
        # CO*45 = "Charge exceeds fee schedule/maximum allowable or contracted/legislated fee arrangement"
        # This is a common denial reason code
        total_charge = clm.get("total_charge", 0)
        cas_segments = [{
            "group_code": "CO",  # Contractual Obligation
            "reason_code": "45",  # Charge exceeds maximum allowable
            "amount": total_charge,
            "quantity": ""
        }]

    if cas_segments:
        for cas in cas_segments:
            # CAS format: CAS*group_code*reason_code*amount*quantity~
            w.segment("CAS", cas.get("group_code"), cas.get("reason_code"),
                     f"{float(cas.get('amount', 0)):.2f}" if cas.get("amount") else "",
                     str(cas.get("quantity", "")) if cas.get("quantity") else "")

    # Per §2.1.4: Denied Claims - MOA segment for RARC codes
    if clm.get("remittance_advice_code"):
        w.segment("MOA", "", clm["remittance_advice_code"])
    elif clm.get("payment_status") == "D":
        # Auto-generate MOA for denied claims if not provided
        # MA130 = "Your claim/service(s) has been denied"
        w.segment("MOA", "", "MA130")

    # K3 occurrences: PYMS; SUB/IPAD/USER; SNWK; TRPN-ASPUFE*; DREC/DADJ/PAIDDT
    if clm.get("payment_status") in ("P","D"): w.segment("K3", f"PYMS-{clm['payment_status']}")
    if clm.get("subscriber_internal_id") or clm.get("ip_address") or clm.get("user_id"):
        parts = []
        if clm.get("subscriber_internal_id"): parts.append(f"SUB-{clm['subscriber_internal_id']}")
        if clm.get("ip_address"): parts.append(f"IPAD-{clm['ip_address']}")
        if clm.get("user_id"): parts.append(f"USER-{clm['user_id']}")
        w.segment("K3", ";".join(parts))
    if clm.get("rendering_network_indicator"): w.segment("K3", f"SNWK-{clm['rendering_network_indicator']}")
    if clm.get("submission_channel") in ("ELECTRONIC","PAPER"):
        tag = "ASPUFEELEC" if clm["submission_channel"]=="ELECTRONIC" else "ASPUFEPAPER"
        w.segment("K3", f"TRPN-{tag}")

    # K3 - Date tracking (Kaizen requirement: DREC/DADJ/PAIDDT)
    if clm.get("receipt_date") or clm.get("adjudication_date") or clm.get("paid_date"):
        date_parts = []
        if clm.get("receipt_date"): date_parts.append(f"DREC-{_fmt_d8(clm['receipt_date'])}")
        if clm.get("adjudication_date"): date_parts.append(f"DADJ-{_fmt_d8(clm['adjudication_date'])}")
        if clm.get("paid_date"): date_parts.append(f"PAIDDT-{_fmt_d8(clm['paid_date'])}")
        w.segment("K3", ";".join(date_parts))

    # K3 - Rendering Provider Address (Kaizen requirement: AL1/AL2 and CY/ST/ZIP)
    rend = claim_json.get("rendering_provider", {})
    if rend.get("address_line1") or rend.get("addr"):
        addr1 = rend.get("address_line1") or rend.get("addr", "")
        addr2 = rend.get("address_line2", "")
        if addr1 or addr2:
            addr_parts = []
            if addr1: addr_parts.append(f"AL1-{addr1}")
            if addr2: addr_parts.append(f"AL2-{addr2}")
            w.segment("K3", ";".join(addr_parts))

        # K3 - Rendering Provider City/State/Zip
        if rend.get("city") or rend.get("state") or rend.get("zip"):
            location_parts = []
            if rend.get("city"): location_parts.append(f"CY-{rend['city']}")
            if rend.get("state"): location_parts.append(f"ST-{rend['state']}")
            if rend.get("zip"): location_parts.append(f"ZIP-{rend['zip']}")
            w.segment("K3", ";".join(location_parts))

    # NTE member group structure (MANDATORY per §2.1.2 - validation ensures it exists)
    group = clm.get("member_group", {})
    nte = [
        f"GRP-{group.get('group_id','')}",
        f"SGR-{group.get('sub_group_id','')}",
        f"CLS-{group.get('class_id','')}",
        f"PLN-{group.get('plan_id','')}",
        f"PRD-{group.get('product_id','')}"
    ]
    w.segment("NTE", "ADD", ";".join(nte))

    # Ambulance/NEMT claim-level CR1
    amb = clm.get("ambulance", {})
    if amb:
        # CR1: Ambulance Transport Information
        # Two modes supported:
        # 1. NTE Mode (default): CR1 with 8 elements + separate NTE segments + Loop 2310E/F
        # 2. CR109/CR110 Mode (§2.1.8): CR1 with 10 elements including pickup/dropoff locations

        trip_num = str(amb.get("trip_number", "")).zfill(9) if amb.get("trip_number") else ""

        if cfg.use_cr1_locations:
            # Per §2.1.8: CR1 format with CR109/CR110 locations
            # CR1*unit*weight*transport_reason**transport_code*reason_desc*qty*qty*CR109*CR110

            # Format CR109 (pickup location) as single string
            cr109 = ""
            if amb.get("pickup"):
                pickup = amb["pickup"]
                parts = []
                if pickup.get("addr"): parts.append(pickup["addr"])
                if pickup.get("city"): parts.append(pickup["city"])
                if pickup.get("state"): parts.append(pickup["state"])
                if pickup.get("zip"): parts.append(pickup["zip"])
                cr109 = ", ".join(parts) if parts else ""

            # Format CR110 (dropoff location) as single string
            cr110 = ""
            if amb.get("dropoff"):
                dropoff = amb["dropoff"]
                parts = []
                if dropoff.get("addr"): parts.append(dropoff["addr"])
                if dropoff.get("city"): parts.append(dropoff["city"])
                if dropoff.get("state"): parts.append(dropoff["state"])
                if dropoff.get("zip"): parts.append(dropoff["zip"])
                cr110 = ", ".join(parts) if parts else ""

            # Build CR1 with 10 elements
            w.segment("CR1",
                     amb.get("weight_unit","LB"),              # CR1-01: Unit
                     str(amb.get("patient_weight_lbs","")).replace(".0",""),  # CR1-02: Weight
                     amb.get("transport_reason",""),           # CR1-03: Transport Reason
                     "",                                       # CR1-04: (not used)
                     amb.get("transport_code",""),             # CR1-05: Transport Code
                     "",                                       # CR1-06: Reason Description
                     "",                                       # CR1-07: Quantity
                     "",                                       # CR1-08: Quantity
                     cr109,                                    # CR1-09: Pickup Location
                     cr110)                                    # CR1-10: Dropoff Location

            # Trip details still in NTE (other fields not in CR1)
            trip = []
            if amb.get("trip_number") is not None: trip.append(f"TRIPNUM-{str(amb['trip_number']).zfill(9)}")
            if amb.get("special_needs") is not None: trip.append(f"SPECNEED-{_yesno(amb['special_needs'])}")
            if amb.get("attendant_type"): trip.append(f"ATTENDTY-{amb['attendant_type']}")
            if amb.get("accompany_count") is not None: trip.append(f"ACCOMP-{amb['accompany_count']}")
            if amb.get("pickup_indicator"): trip.append(f"PICKUP-{amb['pickup_indicator']}")
            if amb.get("requested_date"): trip.append(f"TRIPREQ-{_fmt_d8(amb['requested_date'])}")
            if trip: w.segment("NTE", "ADD", ";".join(trip))

            # Note: Loops 2310E/F are NOT emitted in CR109/CR110 mode (locations are in CR1)
        else:
            # Default NTE Mode: CR1 with 8 elements + separate location loops
            # CR1-09 (Round Trip Purpose Description): Trip number zero-padded to 9 digits per Kaizen requirements
            w.segment("CR1", amb.get("weight_unit","LB"), str(amb.get("patient_weight_lbs","")).replace(".0",""), "", "", "", amb.get("transport_code",""), amb.get("transport_reason",""), trip_num)

            # Trip details in NTE (custom UHC format - was incorrectly in CR1)
            trip = []
            if amb.get("trip_number") is not None: trip.append(f"TRIPNUM-{str(amb['trip_number']).zfill(9)}")
            if amb.get("special_needs") is not None: trip.append(f"SPECNEED-{_yesno(amb['special_needs'])}")
            if amb.get("attendant_type"): trip.append(f"ATTENDTY-{amb['attendant_type']}")
            if amb.get("accompany_count") is not None: trip.append(f"ACCOMP-{amb['accompany_count']}")
            if amb.get("pickup_indicator"): trip.append(f"PICKUP-{amb['pickup_indicator']}")
            if amb.get("requested_date"): trip.append(f"TRIPREQ-{_fmt_d8(amb['requested_date'])}")
            if trip: w.segment("NTE", "ADD", ";".join(trip))

            # Loop 2310E - Ambulance Pick-up Location (Claim Level)
            if amb.get("pickup"):
                w.segment("NM1", "PW", "2"); w.segment("N3", amb["pickup"].get("addr",""))
                w.segment("N4", amb["pickup"].get("city",""), amb["pickup"].get("state",""), amb["pickup"].get("zip",""))

            # Loop 2310F - Ambulance Drop-off Location (Claim Level)
            if amb.get("dropoff"):
                w.segment("NM1", "45", "2"); w.segment("N3", amb["dropoff"].get("addr",""))
                w.segment("N4", amb["dropoff"].get("city",""), amb["dropoff"].get("state",""), amb["dropoff"].get("zip",""))

    # Loop 2310A - Referring Provider (Claim Level)
    # Per §2.1.1: "Referring provider loop should be reported if data is available for the claim"
    ref_prov = claim_json.get("referring_provider", {})
    if ref_prov.get("last") or ref_prov.get("first") or ref_prov.get("npi"):
        ref_last = ref_prov.get("last", "")
        ref_first = ref_prov.get("first", "")
        ref_qualifier = ref_prov.get("qualifier", "DN")  # DN = Referring Provider, P3 = Primary Care Provider

        if ref_prov.get("npi"):
            # Referring provider with NPI
            w.segment("NM1", ref_qualifier, "1", ref_last, ref_first, "", "", "", "XX", ref_prov["npi"])
        else:
            # Referring provider without NPI
            w.segment("NM1", ref_qualifier, "1", ref_last, ref_first)

        # REF*G2 - Secondary ID (state Medicaid ID if no NPI)
        if ref_prov.get("state_medicaid_id"):
            w.segment("REF", "G2", ref_prov["state_medicaid_id"])

    # Loop 2310B - Rendering Provider (Claim Level)
    # Per §2.1.1: "Rendering provider loop should be reported with Individual providers that provided the service"
    # "If the provider cannot be enrolled with State (like for Meals/Lodging/Air transport), then submit the claim by rendering provider as Kaizen"
    rend = claim_json.get("rendering_provider", {})

    # If no rendering provider data, use Kaizen (billing provider) as fallback per §2.1.1
    if not (rend.get("npi") or rend.get("last") or rend.get("first")):
        rend = {
            "npi": bp["npi"],
            "name": bp["name"],
            "taxonomy": bp.get("taxonomy")
        }

    # Extract name
    rend_name = rend.get("name", {})
    if rend_name and isinstance(rend_name, dict):
        last = rend_name.get("last", "")
        first = rend_name.get("first", "")
    else:
        # If name is a string (Kaizen fallback case)
        last = rend.get("name", "") if isinstance(rend.get("name"), str) else rend.get("last", "")
        first = rend.get("first", "")

    # NM1 segment
    if rend.get("npi"):
        # Provider with NPI
        w.segment("NM1", "82", "1", last, first, "", "", "", "XX", rend["npi"])
    else:
        # Atypical provider without NPI
        w.segment("NM1", "82", "1", last, first)

    # PRV segment - Taxonomy (MANDATORY per §2.1.1: "Taxonomy should always be reported for rendering providers")
    if rend.get("taxonomy"):
        w.segment("PRV", "PE", "PXC", rend["taxonomy"])

    # REF*G2 - Atypical Provider ID (state Medicaid ID if no NPI)
    if rend.get("atypical_id"):
        w.segment("REF", "G2", rend["atypical_id"])

    # REF*0B - Driver's License (Kaizen requirement for NEMT providers)
    if rend.get("driver_license"):
        w.segment("REF", "0B", rend["driver_license"])

    # Loop 2310C - Service Facility Location (Claim Level)
    svc_fac = clm.get("service_facility", {})
    if svc_fac.get("name"):
        w.segment("NM1", "77", "2", svc_fac["name"])
        # REF*G2 - Facility secondary ID (state Medicaid ID)
        if svc_fac.get("state_medicaid_id"):
            w.segment("REF", "G2", svc_fac["state_medicaid_id"])

    # Loop 2310D - Supervising Provider (Claim Level)
    sup = clm.get("supervising_provider", {})
    if sup.get("last") or sup.get("first"):
        if sup.get("npi"):
            w.segment("NM1", "DQ", "1", sup.get("last",""), sup.get("first",""), "", "", "", "XX", sup["npi"])
        else:
            w.segment("NM1", "DQ", "1", sup.get("last",""), sup.get("first",""))

        # REF*G2 - Atypical Provider ID (if no NPI)
        if sup.get("atypical_id"):
            w.segment("REF", "G2", sup["atypical_id"])

        # REF*0B - Driver's License (Kaizen requirement)
        if sup.get("driver_license"):
            w.segment("REF", "0B", sup["driver_license"])

        # REF*LU - Trip number reference
        if amb and amb.get("trip_number") is not None:
            w.segment("REF", "LU", str(amb["trip_number"]).zfill(9))

    # Loop 2400 - Service Line
    for i, svc in enumerate(claim_json.get("services", []), 1):
        w.segment("LX", str(i))
        hc_comp = ":".join(["HC", svc["hcpcs"]] + list(svc.get("modifiers", [])))
        # SV101-09: procedure, charge, unit, quantity, POS (SV105-06 empty), composite dx pointer (SV107 empty), monetary (SV108 empty), emergency (SV109)
        w.segment("SV1", hc_comp, f"{float(svc.get('charge',0.0)):.2f}", "UN", str(svc.get("units",1)), "", "", _pos(svc.get("pos", pos)), "", _yesno(svc.get("emergency")) or "")
        dos = svc.get("dos") or from_d
        if dos: w.segment("DTP", "472", "D8", _fmt_d8(dos))

        # NTE segments for NEMT-specific location and time data (2400 level)
        nte_parts = []
        if svc.get("pickup_loc_code"): nte_parts.append(f"PULOC-{svc['pickup_loc_code']}")
        if svc.get("pickup_time"): nte_parts.append(f"PUTIME-{svc['pickup_time']}")
        if svc.get("drop_loc_code"): nte_parts.append(f"DOLOC-{svc['drop_loc_code']}")
        if svc.get("drop_time"): nte_parts.append(f"DOTIME-{svc['drop_time']}")
        if nte_parts: w.segment("NTE", "ADD", ";".join(nte_parts))

        # Service-level trip details in NTE (custom UHC format - was incorrectly in CR1)
        # Trip type, leg, VAS, transport details
        trip_details = []
        if svc.get("trip_type"): trip_details.append(f"TRIPTYPE-{svc['trip_type']}")
        if svc.get("trip_leg"): trip_details.append(f"TRIPLEG-{svc['trip_leg']}")
        if svc.get("vas_indicator") is not None: trip_details.append(f"VAS-{_yesno(svc['vas_indicator'])}")
        if svc.get("transport_type"): trip_details.append(f"TRANTYPE-{svc['transport_type']}")
        if svc.get("appointment_time"): trip_details.append(f"APPTTIME-{svc['appointment_time']}")
        if svc.get("scheduled_pickup_time"): trip_details.append(f"SCHPUTIME-{svc['scheduled_pickup_time']}")
        if svc.get("trip_reason_code") is not None: trip_details.append(f"TRIPRSN-{svc['trip_reason_code']}")
        if trip_details: w.segment("NTE", "ADD", ";".join(trip_details))

        # Arrival/departure times in separate NTE (avoid redundancy with earlier DOLOC/DOTIME)
        time_details = []
        if svc.get("arrive_time"): time_details.append(f"ARRIVTIME-{svc['arrive_time']}")
        if svc.get("depart_time"): time_details.append(f"DEPRTTIME-{svc['depart_time']}")
        if time_details: w.segment("NTE", "ADD", ";".join(time_details))

        # K3 - Line-level payment status (must be at 2400 level, before 2420 provider loops)
        if svc.get("payment_status") in ("P","D"): w.segment("K3", f"PYMS-{svc['payment_status']}")

        # Per §2.1.4: Service-level CAS segments for denied service lines
        # Auto-generate CAS for denied service lines if not provided
        svc_cas_segments = svc.get("cas_segments", [])
        if svc.get("payment_status") == "D" and not svc_cas_segments:
            # Auto-generate denial CAS segment for service line
            svc_charge = svc.get("charge", 0)
            svc_cas_segments = [{
                "group_code": "CO",  # Contractual Obligation
                "reason_code": "45",  # Charge exceeds maximum allowable
                "amount": svc_charge,
                "quantity": ""
            }]

        if svc_cas_segments:
            for cas in svc_cas_segments:
                # CAS format: CAS*group_code*reason_code*amount*quantity~
                w.segment("CAS", cas.get("group_code"), cas.get("reason_code"),
                         f"{float(cas.get('amount', 0)):.2f}" if cas.get("amount") else "",
                         str(cas.get("quantity", "")) if cas.get("quantity") else "")

        # Per §2.1.4: Service-level MOA segment for RARC codes
        if svc.get("remittance_advice_code"):
            w.segment("MOA", "", svc["remittance_advice_code"])
        elif svc.get("payment_status") == "D":
            # Auto-generate MOA for denied service lines if not provided
            w.segment("MOA", "", "MA130")

        # Loop 2420D - Supervising Provider (Service Line Level)
        if svc.get("supervising_provider"):
            sp = svc["supervising_provider"]
            if sp.get("npi"):
                w.segment("NM1", "DQ", "1", sp.get("last",""), sp.get("first",""), "", "", "", "XX", sp["npi"])
            else:
                w.segment("NM1", "DQ", "1", sp.get("last",""), sp.get("first",""))

            # REF*G2 - Atypical Provider ID (if no NPI)
            if sp.get("atypical_id"):
                w.segment("REF", "G2", sp["atypical_id"])

            # REF*0B - Driver's License (Kaizen requirement)
            if sp.get("driver_license"):
                w.segment("REF", "0B", sp["driver_license"])

            # Trip number: use service-level if provided, otherwise cascade from claim-level
            trip_num = svc.get("trip_number")
            if trip_num is None and amb and amb.get("trip_number") is not None:
                trip_num = amb["trip_number"]
            if trip_num is not None:
                w.segment("REF", "LU", str(trip_num).zfill(9))

        # Loop 2420G - Ambulance Pick-up Location (Service Line Level)
        if svc.get("pickup"):
            w.segment("NM1", "PW", "2"); w.segment("N3", svc["pickup"].get("addr",""))
            w.segment("N4", svc["pickup"].get("city",""), svc["pickup"].get("state",""), svc["pickup"].get("zip",""))

        # Loop 2420H - Ambulance Drop-off Location (Service Line Level)
        if svc.get("dropoff"):
            w.segment("NM1", "45", "2"); w.segment("N3", svc["dropoff"].get("addr",""))
            w.segment("N4", svc["dropoff"].get("city",""), svc["dropoff"].get("state",""), svc["dropoff"].get("zip",""))

        # Loop 2430 - Line Adjudication Information
        for adj in svc.get("adjudication", []):
            paid = f"{float(adj.get('paid_amount',0.0)):.2f}"
            svd05 = str(adj.get("paid_units","")) if adj.get("paid_units") is not None else ""
            w.segment("SVD", payer.payer_id, paid, hc_comp, "", svd05)
            for cas in adj.get("cas", []):
                w.segment("CAS", cas.get("group","CO"), cas.get("reason",""), f"{float(cas.get('amount',0.0)):.2f}", str(cas.get("quantity","")))

    if clm.get("moa_rarc"): w.segment("MOA", clm["moa_rarc"])

    w.build_SE(st_index, st_cn); w.build_GE(1, gs_cn); w.build_IEA(1, isa_cn)
    return w.to_string()
