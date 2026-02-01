#!/usr/bin/env python3
"""
BOOT_ORCHESTRATOR_v1 — canonical boot runner for sandbox/project-files usage.

Contract:
- When user says "boot", the assistant should run this tool (via python execution).
- This tool runs:
  1) ZOOP_GUARD_v1 (extract + guard) against the configured OS zip, into canonical root
  2) CANONICAL_ROOT_INTEGRITY_CHECK
  3) Emits BOOT_RECEIPT_v1.json under receipts/

No network. Writes only within canonical root receipts and extraction target.
"""
from __future__ import annotations
from pathlib import Path
import argparse, json, subprocess, time, os, sys

def now_utc():
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def run(cmd:list[str]) -> tuple[int,str,str]:
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate()
    return p.returncode, out, err

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True, help="project-files OS zip path")
    ap.add_argument("--root", default="/mnt/data/Metblooms_OS", help="canonical root")
    args = ap.parse_args()

    zip_path = Path(args.zip).resolve()
    root = Path(args.root).resolve()
    receipts = root / "receipts"
    receipts.mkdir(parents=True, exist_ok=True)

    boot_receipt = {
        "artifact":"BOOT_RECEIPT_v1",
        "timestamp_utc": now_utc(),
        "status":"FAIL",
        "os_zip": str(zip_path),
        "canonical_root": str(root),
        "steps": [],
        "errors": []
    }

    if not zip_path.exists():
        boot_receipt["errors"].append("os_zip_missing")
        (receipts / "BOOT_RECEIPT_v1.json").write_text(json.dumps(boot_receipt, indent=2))
        return 2

    # 1) run zoop guard
    zoop_guard = root / "tools" / "zoop" / "zoop_guard.py"
    if not zoop_guard.exists():
        boot_receipt["errors"].append("zoop_guard_missing")
        (receipts / "BOOT_RECEIPT_v1.json").write_text(json.dumps(boot_receipt, indent=2))
        return 2

    rc, out, err = run([sys.executable, str(zoop_guard), "--zip", str(zip_path), "--target", str(root)])
    boot_receipt["steps"].append({"step":"ZOOP_GUARD_v1","rc":rc,"stdout":out[-5000:], "stderr":err[-5000:]})
    if rc != 0:
        boot_receipt["errors"].append("zoop_guard_failed")
        (receipts / "BOOT_RECEIPT_v1.json").write_text(json.dumps(boot_receipt, indent=2))
        return 2

    # 2) canonical integrity
    checker = root / "tools" / "boot" / "canonical_root_integrity_check.py"
    rc2, out2, err2 = run([sys.executable, str(checker), "--root", str(root)])
    boot_receipt["steps"].append({"step":"CANONICAL_ROOT_INTEGRITY_CHECK","rc":rc2,"stdout":out2[-5000:], "stderr":err2[-5000:]})
    if rc2 != 0:
        boot_receipt["errors"].append("canonical_integrity_failed")
        (receipts / "BOOT_RECEIPT_v1.json").write_text(json.dumps(boot_receipt, indent=2))
        return 2

    boot_receipt["status"] = "PASS"
    (receipts / "BOOT_RECEIPT_v1.json").write_text(json.dumps(boot_receipt, indent=2))
    print(f"BOOT_ORCHESTRATOR_v1 -> PASS :: {receipts / 'BOOT_RECEIPT_v1.json'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
