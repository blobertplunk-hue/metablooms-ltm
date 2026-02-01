#!/usr/bin/env python3
"""P15 Delta Pack Shipping
Packages the exact restored/changed surface from the most recent P14 self-repair report into a portable zip.
Inputs:
- latest reports/p14_self_repair_report_*.json
Outputs:
- /mnt/data/MetaBlooms_DELTA_P15_<UTC>.zip
- /mnt/data/MetaBlooms_DELTA_P15_<UTC>_MANIFEST.json
- receipts/p15_delta_ship_receipt_<UTC>.json (inside ROOT)
Fail-closed if no P14 report found.
import os, json, time, glob, zipfile, hashlib, sys

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MNT="/mnt/data"

def ts():
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

def utc_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def sha256_file(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(8192), b""):
            h.update(b)
    return h.hexdigest()

reports=sorted(glob.glob(os.path.join(ROOT,"reports","p14_self_repair_report_*.json")))
if not reports:
    sys.exit("P15_FAIL_NO_P14_REPORT")

report_path=reports[-1]
report=json.load(open(report_path,"r",encoding="utf-8"))
restored=report.get("restored_all") or report.get("restored_sample") or []

# Include P14 receipt/report as evidence
receipts=sorted(glob.glob(os.path.join(ROOT,"receipts","p14_self_repair_receipt_*.json")))
p14_receipt=receipts[-1] if receipts else None

tag=ts()
out_zip=os.path.join(MNT, f"MetaBlooms_DELTA_P15_{tag}.zip")

with zipfile.ZipFile(out_zip,"w",zipfile.ZIP_DEFLATED) as z:
    # restored paths relative to ROOT
    for rel in restored:
        p=os.path.join(ROOT, rel)
        if os.path.exists(p) and os.path.isfile(p):
            z.write(p, rel)
    # always include current policy + baseline (so deltas can be validated)
    for must in ["config/DRIFT_POLICY.json","indexes/BASELINE_HASHES.json","config/TOOL_CHOICE_GATE.json"]:
        p=os.path.join(ROOT,must)
        if os.path.exists(p):
            z.write(p, must)
    if p14_receipt and os.path.exists(p14_receipt):
        z.write(p14_receipt, os.path.join("evidence", os.path.basename(p14_receipt)))
    if os.path.exists(report_path):
        z.write(report_path, os.path.join("evidence", os.path.basename(report_path)))

manifest={
  "phase":"P15",
  "utc": utc_iso(),
  "delta_zip": os.path.basename(out_zip),
  "sha256": sha256_file(out_zip),
  "source_p14_report": os.path.relpath(report_path, ROOT),
  "restored_count": len(restored),
  "included_minimum": ["config/DRIFT_POLICY.json","indexes/BASELINE_HASHES.json","config/TOOL_CHOICE_GATE.json"]
}
man_path=os.path.join(MNT, f"MetaBlooms_DELTA_P15_{tag}_MANIFEST.json")
open(man_path,"w",encoding="utf-8").write(json.dumps(manifest,indent=2))

# Receipt in ROOT
os.makedirs(os.path.join(ROOT,"receipts"), exist_ok=True)
rc_path=os.path.join(ROOT,"receipts", f"p15_delta_ship_receipt_{tag}.json")
open(rc_path,"w",encoding="utf-8").write(json.dumps({
  "phase":"P15",
  "utc": manifest["utc"],
  "status":"OK",
  "delta_zip": os.path.basename(out_zip),
  "manifest": os.path.basename(man_path),
  "p14_report": manifest["source_p14_report"],
  "sha256": manifest["sha256"]
}, indent=2))

print(out_zip)
print(man_path)
print(rc_path)
"""
