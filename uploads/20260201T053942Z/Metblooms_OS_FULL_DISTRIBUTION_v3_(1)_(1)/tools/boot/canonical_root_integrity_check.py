#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse, json, time

def now_utc():
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    receipts = root / "receipts"
    receipts.mkdir(parents=True, exist_ok=True)

    # Shadow roots: top-level /mnt/data variants + nested variants
    data_root = root.parent
    shadow_names = ["Metablooms_OS","MetaBlooms_OS","metablooms_os","METABLOOMS_OS","Metabooms_OS","Metabloom_OS"]
    shadows = []
    for name in shadow_names:
        p = data_root / name
        if p.exists():
            shadows.append(str(p))
        q = root / name
        if q.exists():
            shadows.append(str(q))

    required = ["tools","config"]
    missing = [d for d in required if not (root / d).exists()]
    subsystems = sorted([p.name for p in root.iterdir() if p.is_dir()])

    ready = root.exists() and len(shadows) == 0 and len(missing) == 0

    report = {
        "artifact":"CANONICAL_ROOT_INTEGRITY_REPORT_v1",
        "timestamp_utc": now_utc(),
        "canonical_root": str(root),
        "checks":{
            "canonical_root_exists": root.exists(),
            "shadow_roots_found": shadows,
            "shadow_root_absent": len(shadows)==0,
            "subsystems_present": subsystems,
            "missing_required_subsystems": missing,
        },
        "ready_for_overlay_integration": ready
    }
    report_path = receipts / "CANONICAL_ROOT_INTEGRITY_REPORT_v1.json"
    report_path.write_text(json.dumps(report, indent=2))

    receipt = {
        "artifact":"CANONICAL_ROOT_INTEGRITY_RECEIPT_v1",
        "timestamp_utc": report["timestamp_utc"],
        "report": str(report_path),
        "status":"PASS" if ready else "FAIL"
    }
    receipt_path = receipts / "CANONICAL_ROOT_INTEGRITY_RECEIPT_v1.json"
    receipt_path.write_text(json.dumps(receipt, indent=2))

    print(f"CANONICAL_ROOT_INTEGRITY_CHECK -> {receipt['status']} :: {receipt_path}")
    return 0 if ready else 2

if __name__ == "__main__":
    raise SystemExit(main())
