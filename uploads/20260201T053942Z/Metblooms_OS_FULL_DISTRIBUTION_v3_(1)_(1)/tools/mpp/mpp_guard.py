#!/usr/bin/env python3
"""MetaBlooms MPP Guard
Purpose: hard-gate implementation/planning actions unless MPP is started or user bypasses.
This tool is deterministic and file-backed. It does not perform SEE itself; it enforces that SEE receipts exist when required.
"""
import os, json, time, argparse, sys

def utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--turn-id", required=True)
    ap.add_argument("--intent", required=True)
    ap.add_argument("--bypass", action="store_true")
    args = ap.parse_args()

    root=args.root
    cfg_path=os.path.join(root,"config","MPP_GATE.json")
    cfg=json.load(open(cfg_path, "r", encoding="utf-8"))

    os.makedirs(os.path.join(root,"receipts"), exist_ok=True)
    start_receipt=os.path.join(root,"receipts", f"mpp_start_receipt_{args.turn_id}.json")
    phase_log=os.path.join(root,"receipts", "mpp_phase_receipts.ndjson")

    # If bypass requested, emit bypass receipt and allow
    if args.bypass:
        r={"utc":utc_now(),"turn_id":args.turn_id,"intent":args.intent,"status":"MPP_BYPASS","phases_planned":[]}
        open(start_receipt,"w",encoding="utf-8").write(json.dumps(r,indent=2))
        open(phase_log,"a",encoding="utf-8").write(json.dumps({"utc":utc_now(),"turn_id":args.turn_id,"phase":"BYPASS","status":"OK"})+"\n")
        print("MPP_BYPASS_OK")
        return 0

    # Autostart if intent is gated
    gated = any(k in args.intent.lower() for k in cfg.get("mpp_autostart_on_intents", []))
    if gated:
        r={"utc":utc_now(),"turn_id":args.turn_id,"intent":args.intent,"status":"MPP_STARTED","phases_planned":cfg.get("required_phases_default",[])}
        open(start_receipt,"w",encoding="utf-8").write(json.dumps(r,indent=2))
        open(phase_log,"a",encoding="utf-8").write(json.dumps({"utc":utc_now(),"turn_id":args.turn_id,"phase":"P0_GUARD","status":"STARTED","intent":args.intent})+"\n")
        print("MPP_STARTED")
        # Fail-closed: require subsequent phase receipts before execution (enforced by caller/gates)
        return 2  # signal: started but not complete
    else:
        print("MPP_NOT_REQUIRED")
        return 0

if __name__ == "__main__":
    sys.exit(main())
