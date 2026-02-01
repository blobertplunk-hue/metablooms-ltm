#!/usr/bin/env python3
"""BTS Tick Runner
- Emits BTS tick every turn
- Classifies intent (simple heuristic)
- Invokes MPP guard
- Blocks execution unless MPP complete or bypassed
"""
import os, json, time, subprocess, sys, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
UTC = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
BTS_DIR = os.path.join(ROOT, "_bts")
BOOT_DIR = os.path.join(ROOT, "boot")
REC_DIR = os.path.join(ROOT, "receipts")
os.makedirs(BTS_DIR, exist_ok=True)
os.makedirs(BOOT_DIR, exist_ok=True)
os.makedirs(REC_DIR, exist_ok=True)

def utc_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def emit(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

# Always emit BTS tick attempt
bts_tick = {
    "utc": utc_iso(),
    "status": "BTS_TICK_ATTEMPT",
    "runner": "bts_tick_runner.py"
}
bts_path = os.path.join(BTS_DIR, f"bts_tick_receipt_{UTC}.json")
emit(bts_path, bts_tick)

# Intent classification (minimal, deterministic)
intent = os.environ.get("MB_INTENT","").lower()
if not intent:
    intent = "reasoning_only"

# Bypass detection
bypass = os.environ.get("MB_BYPASS_MPP","false").lower() == "true"

# Call MPP guard
guard = os.path.join(ROOT, "tools", "mpp", "mpp_guard.py")
turn_id = UTC
cmd = [guard, "--root", ROOT, "--turn-id", turn_id, "--intent", intent]
if bypass:
    cmd.append("--bypass")

rc = 0
try:
    p = subprocess.run(cmd, capture_output=True, text=True)
    rc = p.returncode
    guard_out = {
        "stdout": p.stdout.strip(),
        "stderr": p.stderr.strip(),
        "returncode": rc
    }
except Exception as e:
    guard_out = {"error": repr(e)}
    rc = 1

# Emit decision receipt
decision = {
    "utc": utc_iso(),
    "turn_id": turn_id,
    "intent": intent,
    "bypass": bypass,
    "guard_result": guard_out,
    "policy": "config/MPP_GATE.json"
}
emit(os.path.join(REC_DIR, f"bts_mpp_decision_{UTC}.json"), decision)

# Finalize BTS tick
final = {
    "utc": utc_iso(),
    "status": "BTS_OK" if rc in (0,2) else "BTS_FAIL",
    "mpp_state": "STARTED" if rc==2 else ("BYPASS" if bypass else "OK"),
}
emit(bts_path, final)

# Exit codes:
# 0 -> proceed (non-gated or bypass)
# 2 -> MPP started; block execution
# 1 -> failure
sys.exit(rc)
