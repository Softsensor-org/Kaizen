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

class ValidationError(Exception):
    """Raised when input JSON validation fails"""
    pass

def validate_claim_json(claim_json: dict):
    """Validate required fields, formats, and code values in claim JSON"""
    errors = []

    # Required top-level keys
    for key in ["submitter", "receiver", "billing_provider", "subscriber", "claim"]:
        if key not in claim_json:
            errors.append(f"Missing required top-level key: {key}")

    if errors:
        raise ValidationError("; ".join(errors))

    # Validate billing provider
    bp = claim_json["billing_provider"]
    if not bp.get("npi"):
        errors.append("billing_provider.npi is required")
    elif not re.match(r'^\d{10}$', str(bp["npi"])):
        errors.append(f"billing_provider.npi must be 10 digits, got: {bp['npi']}")

    if not bp.get("name"):
        errors.append("billing_provider.name is required")
    elif len(bp["name"]) > 60:
        errors.append(f"billing_provider.name must be ≤60 characters, got {len(bp['name'])}")

    if "address" not in bp:
        errors.append("billing_provider.address is required")
    else:
        addr = bp["address"]
        if not all(k in addr for k in ["line1", "city", "state", "zip"]):
            errors.append("billing_provider.address must have line1, city, state, zip")
        else:
            if len(addr["line1"]) > 55:
                errors.append(f"billing_provider.address.line1 must be ≤55 characters")
            if len(addr["city"]) > 30:
                errors.append(f"billing_provider.address.city must be ≤30 characters")
            err = validate_state(addr["state"], "billing_provider.address.state")
            if err: errors.append(err)
            err = validate_zip(addr["zip"], "billing_provider.address.zip")
            if err: errors.append(err)

    if bp.get("tax_id") and not re.match(r'^\d{9}$', str(bp["tax_id"]).replace("-", "")):
        errors.append(f"billing_provider.tax_id must be 9 digits, got: {bp['tax_id']}")

    # Validate subscriber
    subr = claim_json["subscriber"]
    if not subr.get("member_id"):
        errors.append("subscriber.member_id is required")
    elif len(subr["member_id"]) > 80:
        errors.append(f"subscriber.member_id must be ≤80 characters")

    if "name" not in subr or not subr["name"].get("last") or not subr["name"].get("first"):
        errors.append("subscriber.name.last and subscriber.name.first are required")
    else:
        if len(subr["name"]["last"]) > 60:
            errors.append(f"subscriber.name.last must be ≤60 characters")
        if len(subr["name"]["first"]) > 35:
            errors.append(f"subscriber.name.first must be ≤35 characters")

    if subr.get("dob") and not re.match(r'^\d{4}-\d{2}-\d{2}$', subr["dob"]):
        errors.append(f"subscriber.dob must be in YYYY-MM-DD format, got: {subr['dob']}")

    if subr.get("sex"):
        err = validate_code(subr["sex"], GENDER_CODES, "subscriber.sex")
        if err: errors.append(err)

    if "address" in subr:
        addr = subr["address"]
        if addr.get("state"):
            err = validate_state(addr["state"], "subscriber.address.state")
            if err: errors.append(err)
        if addr.get("zip"):
            err = validate_zip(addr["zip"], "subscriber.address.zip")
            if err: errors.append(err)

    # Validate claim
    clm = claim_json["claim"]
    if not clm.get("clm_number"):
        errors.append("claim.clm_number is required")
    elif len(str(clm["clm_number"])) > 30:
        errors.append(f"claim.clm_number must be ≤30 characters, got {len(str(clm['clm_number']))}")

    if not clm.get("total_charge"):
        errors.append("claim.total_charge is required")

    if not clm.get("from"):
        errors.append("claim.from date is required")
    elif not re.match(r'^\d{4}-\d{2}-\d{2}$', clm["from"]):
        errors.append(f"claim.from must be in YYYY-MM-DD format, got: {clm['from']}")

    if clm.get("to") and not re.match(r'^\d{4}-\d{2}-\d{2}$', clm["to"]):
        errors.append(f"claim.to must be in YYYY-MM-DD format, got: {clm['to']}")

    if clm.get("pos"):
        err = validate_code(clm["pos"], POS_CODES, "claim.pos")
        if err: errors.append(err)

    if clm.get("frequency_code"):
        err = validate_code(clm["frequency_code"], FREQUENCY_CODES, "claim.frequency_code")
        if err: errors.append(err)

    if clm.get("payment_status"):
        err = validate_code(clm["payment_status"], PAYMENT_STATUS_CODES, "claim.payment_status")
        if err: errors.append(err)

    if clm.get("rendering_network_indicator"):
        err = validate_code(clm["rendering_network_indicator"], NETWORK_INDICATORS, "claim.rendering_network_indicator")
        if err: errors.append(err)

    if clm.get("submission_channel"):
        err = validate_code(clm["submission_channel"], SUBMISSION_CHANNELS, "claim.submission_channel")
        if err: errors.append(err)

    # Validate ambulance data
    if clm.get("ambulance"):
        amb = clm["ambulance"]
        if amb.get("weight_unit"):
            err = validate_code(amb["weight_unit"], WEIGHT_UNITS, "claim.ambulance.weight_unit")
            if err: errors.append(err)

        if amb.get("transport_code"):
            err = validate_code(amb["transport_code"], TRANSPORT_CODES, "claim.ambulance.transport_code")
            if err: errors.append(err)

        if amb.get("transport_reason"):
            err = validate_code(amb["transport_reason"], TRANSPORT_REASON_CODES, "claim.ambulance.transport_reason")
            if err: errors.append(err)

        if amb.get("requested_date") and not re.match(r'^\d{4}-\d{2}-\d{2}$', amb["requested_date"]):
            errors.append(f"claim.ambulance.requested_date must be in YYYY-MM-DD format")

    # Validate services
    if not claim_json.get("services"):
        errors.append("At least one service is required")
    else:
        for i, svc in enumerate(claim_json["services"], 1):
            if not svc.get("hcpcs"):
                errors.append(f"services[{i}].hcpcs is required")
            elif len(svc["hcpcs"]) > 5:
                errors.append(f"services[{i}].hcpcs must be ≤5 characters")

            if not svc.get("charge"):
                errors.append(f"services[{i}].charge is required")

            if svc.get("modifiers"):
                if len(svc["modifiers"]) > 4:
                    errors.append(f"services[{i}].modifiers: maximum 4 modifiers allowed")
                for mod in svc["modifiers"]:
                    if len(mod) > 2:
                        errors.append(f"services[{i}].modifiers: modifier '{mod}' must be ≤2 characters")

            if svc.get("pos"):
                err = validate_code(svc["pos"], POS_CODES, f"services[{i}].pos")
                if err: errors.append(err)

            if svc.get("dos") and not re.match(r'^\d{4}-\d{2}-\d{2}$', svc["dos"]):
                errors.append(f"services[{i}].dos must be in YYYY-MM-DD format")

            if svc.get("trip_type"):
                err = validate_code(svc["trip_type"], TRIP_TYPES, f"services[{i}].trip_type")
                if err: errors.append(err)

            if svc.get("trip_leg"):
                err = validate_code(svc["trip_leg"], TRIP_LEGS, f"services[{i}].trip_leg")
                if err: errors.append(err)

            if svc.get("payment_status"):
                err = validate_code(svc["payment_status"], PAYMENT_STATUS_CODES, f"services[{i}].payment_status")
                if err: errors.append(err)

    if errors:
        raise ValidationError("; ".join(errors))

class Config:
    def __init__(self, sender_qual="ZZ", sender_id="SENDERID", receiver_qual="ZZ", receiver_id="RECEIVERID",
                 usage_indicator="T", gs_sender_code="SENDER", gs_receiver_code="RECEIVER", component_sep=":",
                 payer_config=None):
        self.sender_qual = sender_qual
        self.sender_id = sender_id
        self.receiver_qual = receiver_qual
        self.receiver_id = receiver_id
        self.usage_indicator = usage_indicator
        self.gs_sender_code = gs_sender_code
        self.gs_receiver_code = gs_receiver_code
        self.component_sep = component_sep
        self.payer_config = payer_config  # PayerConfig object for payer-specific settings

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

    # BHT
    w.segment("BHT", "0019", "00", (clm.get("clm_number") or "REF")[:30], now.strftime("%Y%m%d"), now.strftime("%H%M"), "CH")

    # 1000A Submitter
    subm = claim_json["submitter"]
    w.segment("NM1", "41", "2", subm.get("name",""), "", "", "", "", subm.get("id_qualifier","ZZ"), subm.get("id") or subm.get("sender_id",""))
    if subm.get("contact_name") or subm.get("contact_phone"):
        w.segment("PER", "IC", subm.get("contact_name",""), "TE", subm.get("contact_phone",""))

    # 1000B Receiver
    w.segment("NM1", "40", "2", payer.payer_name or recv.get("payer_name","RECEIVER"), "", "", "", "", "46", cfg.receiver_id)

    # 2000A Billing Provider
    w.segment("HL", "1", "", "20", "1")
    bp = claim_json["billing_provider"]
    w.segment("NM1", "85", "2", bp["name"], "", "", "", "", "XX", bp["npi"])
    w.segment("N3", bp["address"]["line1"])
    w.segment("N4", bp["address"]["city"], bp["address"]["state"], bp["address"]["zip"])
    if bp.get("tax_id"): w.segment("REF", "EI", bp["tax_id"])
    if bp.get("taxonomy"): w.segment("PRV", "BI", "PXC", bp["taxonomy"])

    # 2000B Subscriber
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

    # 2300 Claim
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

    # K3 occurrences: PYMS; SUB/IPAD/USER; SNWK; TRPN-ASPUFE*
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

    # NTE member group structure
    group = clm.get("member_group", {})
    if any(group.get(k) for k in ("group_id","sub_group_id","class_id","plan_id","product_id")):
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
        # CR1: Ambulance Transport Information (proper X12 format)
        w.segment("CR1", amb.get("weight_unit","LB"), str(amb.get("patient_weight_lbs","")).replace(".0",""), "", "", amb.get("transport_code",""), amb.get("transport_reason",""))

        # Trip details in NTE (custom UHC format - was incorrectly in CR1)
        trip = []
        if amb.get("trip_number") is not None: trip.append(f"TRIPNUM-{str(amb['trip_number']).zfill(9)}")
        if amb.get("special_needs") is not None: trip.append(f"SPECNEED-{_yesno(amb['special_needs'])}")
        if amb.get("attendant_type"): trip.append(f"ATTENDTY-{amb['attendant_type']}")
        if amb.get("accompany_count") is not None: trip.append(f"ACCOMP-{amb['accompany_count']}")
        if amb.get("pickup_indicator"): trip.append(f"PICKUP-{amb['pickup_indicator']}")
        if amb.get("requested_date"): trip.append(f"TRIPREQ-{_fmt_d8(amb['requested_date'])}")
        if trip: w.segment("NTE", "ADD", ";".join(trip))
        if amb.get("pickup"):
            w.segment("NM1", "PW", "2"); w.segment("N3", amb["pickup"].get("addr",""))
            w.segment("N4", amb["pickup"].get("city",""), amb["pickup"].get("state",""), amb["pickup"].get("zip",""))
        if amb.get("dropoff"):
            w.segment("NM1", "45", "2"); w.segment("N3", amb["dropoff"].get("addr",""))
            w.segment("N4", amb["dropoff"].get("city",""), amb["dropoff"].get("state",""), amb["dropoff"].get("zip",""))

    sup = clm.get("supervising_provider", {})
    if sup.get("last") or sup.get("first"):
        w.segment("NM1", "DQ", "1", sup.get("last",""), sup.get("first",""))
        if amb and amb.get("trip_number") is not None: w.segment("REF", "LU", str(amb["trip_number"]).zfill(9))

    # 2400 Service lines
    for i, svc in enumerate(claim_json.get("services", []), 1):
        w.segment("LX", str(i))
        hc_comp = ":".join(["HC", svc["hcpcs"]] + list(svc.get("modifiers", [])))
        w.segment("SV1", hc_comp, f"{float(svc.get('charge',0.0)):.2f}", "UN", str(svc.get("units",1)), "", "", _pos(svc.get("pos", pos)), "", "", _yesno(svc.get("emergency")) or "")
        dos = svc.get("dos") or from_d
        if dos: w.segment("DTP", "472", "D8", _fmt_d8(dos))

        # 2400 NTE for locations & times
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

        # Supervising provider at line (2420D) and REF*LU Trip Number
        if svc.get("supervising_provider"):
            sp = svc["supervising_provider"]
            w.segment("NM1", "DQ", "1", sp.get("last",""), sp.get("first",""))
            # Trip number: use service-level if provided, otherwise cascade from claim-level
            trip_num = svc.get("trip_number")
            if trip_num is None and amb and amb.get("trip_number") is not None:
                trip_num = amb["trip_number"]
            if trip_num is not None:
                w.segment("REF", "LU", str(trip_num).zfill(9))

        # 2420G/H pickup & drop-off
        if svc.get("pickup"):
            w.segment("NM1", "PW", "2"); w.segment("N3", svc["pickup"].get("addr",""))
            w.segment("N4", svc["pickup"].get("city",""), svc["pickup"].get("state",""), svc["pickup"].get("zip",""))
        if svc.get("dropoff"):
            w.segment("NM1", "45", "2"); w.segment("N3", svc["dropoff"].get("addr",""))
            w.segment("N4", svc["dropoff"].get("city",""), svc["dropoff"].get("state",""), svc["dropoff"].get("zip",""))

        # Line-level PYMS
        if svc.get("payment_status") in ("P","D"): w.segment("K3", f"PYMS-{svc['payment_status']}")

        # 2430 adjudication (SVD + CAS)
        for adj in svc.get("adjudication", []):
            paid = f"{float(adj.get('paid_amount',0.0)):.2f}"
            svd05 = str(adj.get("paid_units","")) if adj.get("paid_units") is not None else ""
            w.segment("SVD", payer.payer_id, paid, hc_comp, "", svd05)
            for cas in adj.get("cas", []):
                w.segment("CAS", cas.get("group","CO"), cas.get("reason",""), f"{float(cas.get('amount',0.0)):.2f}", str(cas.get("quantity","")))

    if clm.get("moa_rarc"): w.segment("MOA", clm["moa_rarc"])

    w.build_SE(st_index, st_cn); w.build_GE(1, gs_cn); w.build_IEA(1, isa_cn)
    return w.to_string()
