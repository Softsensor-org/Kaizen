# SPDX-License-Identifier: MIT
import argparse, json, sys
from .builder import build_837p_from_json, Config
from .x12 import ControlNumbers

def main():
    p = argparse.ArgumentParser(description="Convert Kaizen NEMT JSON to 837P EDI (Availity/UHC).")
    p.add_argument("json_path", help="Input JSON claim file")
    p.add_argument("--out", default="-", help="Output EDI file path (default stdout)")
    p.add_argument("--sender-qual", default="ZZ")
    p.add_argument("--sender-id", required=True)
    p.add_argument("--receiver-qual", default="ZZ")
    p.add_argument("--receiver-id", required=True, help="Availity ISA08 ID assigned to you")
    p.add_argument("--usage", default="T", choices=["T","P"], help="T=Test, P=Production")
    p.add_argument("--gs-sender", required=True, help="GS02 (App Sender Code)")
    p.add_argument("--gs-receiver", required=True, help="GS03 (App Receiver Code)")
    args = p.parse_args()

    with open(args.json_path, "r") as f:
        data = json.load(f)

    cfg = Config(sender_qual=args.sender_qual, sender_id=args.sender_id,
                 receiver_qual=args.receiver_qual, receiver_id=args.receiver_id,
                 usage_indicator=args.usage, gs_sender_code=args.gs_sender, gs_receiver_code=args.gs_receiver)

    edi = build_837p_from_json(data, cfg, ControlNumbers())
    if args.out == "-" or args.out == "/dev/stdout":
        sys.stdout.write(edi)
    else:
        with open(args.out, "w", newline="") as f:
            f.write(edi)
        print(f"Wrote {args.out}")

if __name__ == "__main__":
    main()
