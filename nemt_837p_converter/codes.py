# SPDX-License-Identifier: MIT
"""
Code value lookup tables for X12 837P validation
"""

# Place of Service Codes (common NEMT codes)
POS_CODES = {
    "02": "Telehealth",
    "11": "Office",
    "12": "Home",
    "21": "Inpatient Hospital",
    "22": "On Campus-Outpatient Hospital",
    "23": "Emergency Room - Hospital",
    "31": "Skilled Nursing Facility",
    "32": "Nursing Facility",
    "33": "Custodial Care Facility",
    "41": "Ambulance - Land",
    "42": "Ambulance - Air or Water",
    "49": "Independent Clinic",
    "50": "Federally Qualified Health Center",
    "51": "Inpatient Psychiatric Facility",
    "52": "Psychiatric Facility Partial Hospitalization",
    "53": "Community Mental Health Center",
    "54": "Intermediate Care Facility/Mentally Retarded",
    "55": "Residential Substance Abuse Treatment Facility",
    "56": "Psychiatric Residential Treatment Center",
    "57": "Non-residential Substance Abuse Treatment Facility",
    "60": "Mass Immunization Center",
    "61": "Comprehensive Inpatient Rehabilitation Facility",
    "62": "Comprehensive Outpatient Rehabilitation Facility",
    "65": "End-Stage Renal Disease Treatment Facility",
    "71": "Public Health Clinic",
    "72": "Rural Health Clinic",
    "81": "Independent Laboratory",
    "99": "Other Place of Service",
}

# NEMT HCPCS Codes (common ambulance codes)
NEMT_HCPCS_CODES = {
    "A0021": "Ambulance service, outside state per mile, transport",
    "A0080": "Non-emergency transportation, per mile - vehicle provided by volunteer",
    "A0090": "Non-emergency transportation, per mile - vehicle provided by individual",
    "A0100": "Non-emergency transportation; taxi",
    "A0110": "Non-emergency transportation and bus, intra- or inter-state carrier",
    "A0120": "Non-emergency transportation: mini-bus, mountain area transports",
    "A0130": "Non-emergency transportation: wheelchair van",
    "A0140": "Non-emergency transportation and air travel (private or commercial) intra- or inter-state",
    "A0160": "Non-emergency transportation: per mile - case worker or social worker",
    "A0170": "Transportation ancillary: parking fees, tolls, other",
    "A0180": "Non-emergency transportation: ancillary: lodging-recipient",
    "A0190": "Non-emergency transportation: ancillary: meals-recipient",
    "A0200": "Non-emergency transportation: ancillary: lodging-escort",
    "A0210": "Non-emergency transportation: ancillary: meals-escort",
    "A0225": "Ambulance service, neonatal transport, base rate, emergency transport",
    "A0382": "BLS mileage (per mile)",
    "A0384": "BLS specialized service disposable supplies",
    "A0392": "ALS specialized service disposable supplies",
    "A0394": "ALS specialized service mileage",
    "A0396": "ALS specialized service; defibrillation",
    "A0398": "ALS routine disposable supplies",
    "A0420": "Ambulance waiting time (ALS or BLS)",
    "A0422": "Ambulance (ALS or BLS) oxygen and oxygen supplies, life sustaining situation",
    "A0424": "Extra ambulance attendant, ground (ALS or BLS) or air (fixed or rotary winged)",
    "A0425": "Ground mileage, per statute mile",
    "A0426": "Ambulance service, advanced life support, non-emergency transport, level 1 (ALS 1)",
    "A0427": "Ambulance service, advanced life support, emergency transport, level 1 (ALS 1 - emergency)",
    "A0428": "Ambulance service, basic life support, non-emergency transport (BLS)",
    "A0429": "Ambulance service, basic life support, emergency transport (BLS-emergency)",
    "A0430": "Ambulance service, conventional air services, transport, one way (fixed wing)",
    "A0431": "Ambulance service, conventional air services, transport, one way (rotary wing)",
    "A0432": "Paramedic intercept (PI), rural area, transport furnished by a volunteer ambulance company",
    "A0433": "Advanced life support, level 2 (ALS 2)",
    "A0434": "Specialty care transport (SCT)",
    "A0435": "Fixed wing air mileage, per statute mile",
    "A0436": "Rotary wing air mileage, per statute mile",
}

# Common HCPCS Modifiers for NEMT
HCPCS_MODIFIERS = {
    "EH": "NEMT medical necessity",
    "GA": "Waiver of liability statement issued as required by payer policy",
    "GY": "Item or service statutorily excluded",
    "GZ": "Item or service expected to be denied",
    "QM": "Ambulance service provided under arrangement by a provider of services",
    "QN": "Ambulance service furnished directly by a provider of services",
    "GM": "Multiple patients on one ambulance trip",
    "QL": "Patient pronounced dead after ambulance called",
    "TQ": "Basic life support transport by a volunteer ambulance provider",
    # Origin/Destination codes
    "D": "Diagnostic or therapeutic site other than 'P' or 'H' when these are used as origin codes",
    "E": "Residential, Domiciliary, Custodial Facility",
    "G": "Hospital-based dialysis facility",
    "H": "Hospital",
    "I": "Site of transfer between ambulance, car, helicopter",
    "J": "Non-hospital-based dialysis facility",
    "N": "Skilled nursing facility",
    "P": "Physician's office",
    "R": "Residence",
    "S": "Scene of accident or acute event",
    "X": "Intermediate stop at physician's office",
}

# Frequency/Type of Bill Codes (CLM05-3)
FREQUENCY_CODES = {
    "1": "Original claim",
    "6": "Corrected claim",
    "7": "Replacement of prior claim",
    "8": "Void/cancel of prior claim",
}

# Ambulance Transport Codes (CR1-05)
TRANSPORT_CODES = {
    "A": "Patient was transported to nearest facility",
    "B": "Patient was transported for the benefit of a preferred physician",
    "C": "Patient was transported for the nearness of family members",
    "D": "Patient was transported for the care of a specialist or for availability of specialized equipment",
    "E": "Patient was transported for the care of a preferred facility",
}

# Ambulance Transport Reasons (CR1-06)
TRANSPORT_REASON_CODES = {
    "A": "Patient was transported for the purposes of ambulance transport",
    "B": "Patient was transported for the purposes of medical treatment",
    "C": "Patient was transported for the purposes of diagnostic procedures",
    "D": "Patient was transported for the purposes of a medical emergency",
    "DH": "Dialysis patient transported to/from dialysis facility",
    "E": "Patient was transported for the purposes of surgery",
}

# Patient Weight Units (CR1-01)
WEIGHT_UNITS = {
    "LB": "Pounds",
    "KG": "Kilograms",
}

# Sex/Gender Codes
GENDER_CODES = {
    "F": "Female",
    "M": "Male",
    "U": "Unknown",
}

# State Codes (US States)
STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR", "VI", "GU", "AS", "MP",
}

# Trip Types (custom UHC format)
TRIP_TYPES = {
    "I": "Initial trip (outbound)",
    "R": "Return trip (inbound)",
    "B": "Both directions",
}

# Trip Legs (custom UHC format)
TRIP_LEGS = {
    "A": "Leg A (first leg)",
    "B": "Leg B (return leg)",
}

# Network Indicators (custom UHC format)
NETWORK_INDICATORS = {
    "I": "In-network",
    "O": "Out-of-network",
}

# Submission Channels (custom UHC format)
SUBMISSION_CHANNELS = {
    "ELECTRONIC": "Electronic submission",
    "PAPER": "Paper submission",
}

# Payment Status Codes (custom UHC format)
PAYMENT_STATUS_CODES = {
    "P": "Paid",
    "D": "Denied",
}


def validate_code(code: str, code_dict: dict, field_name: str) -> str:
    """Validate a code against a lookup dictionary"""
    if code and code not in code_dict:
        return f"{field_name} '{code}' is not a valid code. Valid values: {', '.join(sorted(code_dict.keys())[:10])}{'...' if len(code_dict) > 10 else ''}"
    return None


def validate_state(state: str, field_name: str) -> str:
    """Validate a state code"""
    if state and state.upper() not in STATE_CODES:
        return f"{field_name} '{state}' is not a valid US state code"
    return None


def validate_zip(zip_code: str, field_name: str) -> str:
    """Validate ZIP code format"""
    import re
    if zip_code and not re.match(r'^\d{5}(-\d{4})?$', zip_code):
        return f"{field_name} '{zip_code}' is not a valid ZIP code format (expected: 12345 or 12345-6789)"
    return None
