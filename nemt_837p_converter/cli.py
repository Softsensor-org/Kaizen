# SPDX-License-Identifier: MIT
import argparse, json, sys
from .builder import build_837p_from_json, Config, ValidationError
from .x12 import ControlNumbers
from .payers import get_payer_config, list_payers

def main():
    p = argparse.ArgumentParser(description="Convert Kaizen NEMT JSON to 837P EDI (Availity/UHC).")
    p.add_argument("json_path", nargs="?", help="Input JSON claim file")
    p.add_argument("--out", default="-", help="Output EDI file path (default stdout)")
    p.add_argument("--sender-qual", default="ZZ")
    p.add_argument("--sender-id")
    p.add_argument("--receiver-qual", default="ZZ")
    p.add_argument("--receiver-id", help="Availity ISA08 ID assigned to you")
    p.add_argument("--usage", default="T", choices=["T","P"], help="T=Test, P=Production")
    p.add_argument("--gs-sender", help="GS02 (App Sender Code)")
    p.add_argument("--gs-receiver", help="GS03 (App Receiver Code)")
    p.add_argument("--payer", help="Payer key (e.g., UHC_CS, UHC_KY) or leave blank to use receiver data from JSON")
    p.add_argument("--list-payers", action="store_true", help="List available payer configurations and exit")
    args = p.parse_args()

    if args.list_payers:
        print("Available payer configurations:")
        for key, (payer_id, payer_name) in list_payers().items():
            print(f"  {key:15} - {payer_name} (ID: {payer_id})")
        sys.exit(0)

    # Validate required arguments for conversion
    if not args.json_path:
        p.error("json_path is required for conversion")
    if not args.sender_id:
        p.error("--sender-id is required for conversion")
    if not args.receiver_id:
        p.error("--receiver-id is required for conversion")
    if not args.gs_sender:
        p.error("--gs-sender is required for conversion")
    if not args.gs_receiver:
        p.error("--gs-receiver is required for conversion")

    with open(args.json_path, "r") as f:
        data = json.load(f)

    # Get payer configuration if specified
    payer_config = None
    if args.payer:
        payer_config = get_payer_config(payer_key=args.payer)

    cfg = Config(sender_qual=args.sender_qual, sender_id=args.sender_id,
                 receiver_qual=args.receiver_qual, receiver_id=args.receiver_id,
                 usage_indicator=args.usage, gs_sender_code=args.gs_sender, gs_receiver_code=args.gs_receiver,
                 payer_config=payer_config)

    try:
        edi = build_837p_from_json(data, cfg, ControlNumbers())
    except ValidationError as e:
        print(f"Validation Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.out == "-" or args.out == "/dev/stdout":
        sys.stdout.write(edi)
    else:
        with open(args.out, "w", newline="") as f:
            f.write(edi)
        print(f"Wrote {args.out}")

if __name__ == "__main__":
    main()
