# NEMT 837P Converter (Kaizen/UHC KY – JSON → X12 005010X222A1)

Implements Kaizen encounter requirements for UHC C&S:
- 2300 K3: PYMS P/D; SUB/IPAD/USER; SNWK I/O; TRPN-ASPUFEELEC/PAPER
- 2300 NTE: GRP/SGR/CLS/PLN/PRD group structure
- 2300 CR1/CR109: TRIPNUM/SPECNEED/ATTENDTY/ACCOMP/PICKUP/TRIPREQ
- 2310E/F and 2420G/H for pickup/drop-off
- 2310D/2420D supervising with REF*LU Trip Number
- 2400 NTE: PULOC/PUTIME/DOLOC/DOTIME
- 2400 CR109/CR110 details
- 2400 SV109 emergency Y/N
- CLM05-3 frequency (1/7/8), REF*D9 tracking, REF*F8 account
- 2430 SVD/CAS with paid units in SVD05, MOA at claim

## Run
```bash
unzip nemt_837p_converter_v2.zip
cd nemt_837p_converter
python -m nemt_837p_converter examples/claim_kaizen.json --out out.edi   --sender-qual ZZ --sender-id KAIZENKZN01   --receiver-qual ZZ --receiver-id 030240928   --usage T --gs-sender KAIZENKZN01 --gs-receiver 030240928
```
