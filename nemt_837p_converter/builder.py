# SPDX-License-Identifier: MIT
import datetime
from .x12 import X12Writer, ControlNumbers

class Config:
    def __init__(self, sender_qual="ZZ", sender_id="SENDERID", receiver_qual="ZZ", receiver_id="RECEIVERID",
                 usage_indicator="T", gs_sender_code="SENDER", gs_receiver_code="RECEIVER", component_sep=":"):
        self.sender_qual = sender_qual
        self.sender_id = sender_id
        self.receiver_qual = receiver_qual
        self.receiver_id = receiver_id
        self.usage_indicator = usage_indicator
        self.gs_sender_code = gs_sender_code
        self.gs_receiver_code = gs_receiver_code
        self.component_sep = component_sep

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
    if cn is None: cn = ControlNumbers()
    w = X12Writer(component_sep=cfg.component_sep)
    now = datetime.datetime.now()

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
    recv = claim_json["receiver"]
    w.segment("NM1", "40", "2", recv.get("payer_name","RECEIVER"), "", "", "", "", "46", cfg.receiver_id)

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
    w.segment("NM1", "PR", "2", recv.get("payer_name","UNITED HEALTHCARE"), "", "", "", "", "PI", recv.get("payer_id","87726"))

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

    # Ambulance/NEMT claim-level CR1 and CR109
    amb = clm.get("ambulance", {})
    if amb:
        c1 = ["CR1", amb.get("weight_unit","LB"), str(amb.get("patient_weight_lbs","")).replace(".0",""), "", "", amb.get("transport_code",""), amb.get("transport_reason","")]
        w.extend(w.element_sep.join(c1) + w.segment_term)
        trip = []
        if amb.get("trip_number") is not None: trip.append(f"TRIPNUM-{str(amb['trip_number']).zfill(9)}")
        if amb.get("special_needs") is not None: trip.append(f"SPECNEED-{_yesno(amb['special_needs'])}")
        if amb.get("attendant_type"): trip.append(f"ATTENDTY-{amb['attendant_type']}")
        if amb.get("accompany_count") is not None: trip.append(f"ACCOMP-{amb['accompany_count']}")
        if amb.get("pickup_indicator"): trip.append(f"PICKUP-{amb['pickup_indicator']}")
        if amb.get("requested_date"): trip.append(f"TRIPREQ-{_fmt_d8(amb['requested_date'])}")
        if trip: w.segment("CR1", "", "", "", "", "", "", "", ";".join(trip))
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

        # 2400 CR109 and CR110 strings
        cr109 = []
        if svc.get("trip_type"): cr109.append(f"TRIPTYPE-{svc['trip_type']}")
        if svc.get("trip_leg"): cr109.append(f"TRIPLEG-{svc['trip_leg']}")
        if svc.get("vas_indicator") is not None: cr109.append(f"VAS-{_yesno(svc['vas_indicator'])}")
        if svc.get("transport_type"): cr109.append(f"TRANTYPE-{svc['transport_type']}")
        if svc.get("appointment_time"): cr109.append(f"APPTTIME-{svc['appointment_time']}")
        if svc.get("scheduled_pickup_time"): cr109.append(f"SCHPUTIME-{svc['scheduled_pickup_time']}")
        if svc.get("trip_reason_code") is not None: cr109.append(f"TRIPRSN-{svc['trip_reason_code']}")
        if cr109: w.segment("CR1", "", "", "", "", "", "", "", ";".join(cr109))
        cr110 = []
        if svc.get("arrive_time"): cr110.append(f"ARRIVTIME-{svc['arrive_time']}")
        if svc.get("depart_time"): cr110.append(f"DEPRTTIME-{svc['depart_time']}")
        if svc.get("drop_loc_code"): cr110.append(f"DOLOC-{svc['drop_loc_code']}")
        if svc.get("drop_time"): cr110.append(f"DOTIME-{svc['drop_time']}")
        if cr110: w.segment("CR1", "", "", "", "", "", "", "", "", ";".join(cr110))

        # Supervising provider at line (2420D) and REF*LU Trip Number
        if svc.get("supervising_provider"):
            sp = svc["supervising_provider"]
            w.segment("NM1", "DQ", "1", sp.get("last",""), sp.get("first",""))
            if svc.get("trip_number") is not None: w.segment("REF", "LU", str(svc["trip_number"]).zfill(9))

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
            w.segment("SVD", recv.get("payer_id","87726"), paid, hc_comp, "", svd05)
            for cas in adj.get("cas", []):
                w.segment("CAS", cas.get("group","CO"), cas.get("reason",""), f"{float(cas.get('amount',0.0)):.2f}", str(cas.get("quantity","")))

    if clm.get("moa_rarc"): w.segment("MOA", clm["moa_rarc"])

    w.build_SE(st_index, st_cn); w.build_GE(1, gs_cn); w.build_IEA(1, isa_cn)
    return w.to_string()
