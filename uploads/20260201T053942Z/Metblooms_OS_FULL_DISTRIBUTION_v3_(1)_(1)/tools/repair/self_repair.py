#!/usr/bin/env python3
"""P14 Self-Repair (deterministic, fail-closed)
Trigger: drift detected or missing critical governance artifacts.
Strategy:
- Locate latest shipped OS zip in /mnt/data (MetaBlooms_OS_SHIP_P9_*.zip)
- Extract to temp dir
- Restore monitored paths (config/, tools/, indexes/) into ROOT (overwrite)
- Re-run drift detector; if clean -> PASS, else FAIL (do not proceed silently)
Emits: receipts/p14_self_repair_receipt_<UTC>.json and reports/p14_self_repair_report_<UTC>.json
"""
import os, json, time, glob, zipfile, tempfile, shutil, subprocess, sys, hashlib

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MNT="/mnt/data"

def utc_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def ts():
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

def sha256(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(8192), b""):
            h.update(b)
    return h.hexdigest()

policy=json.load(open(os.path.join(ROOT,"config","DRIFT_POLICY.json"),"r",encoding="utf-8"))
monitored=policy.get("monitored_paths",["config/","tools/","indexes/"])

# find latest ship zip
zips=sorted(glob.glob(os.path.join(MNT,"MetaBlooms_OS_SHIP_P9_*.zip")))
if not zips:
    out={"utc":utc_iso(),"status":"FAIL","error":"No ship zip found in /mnt/data"}
    os.makedirs(os.path.join(ROOT,"reports"), exist_ok=True)
    rp=os.path.join(ROOT,"reports",f"p14_self_repair_report_{ts()}.json")
    open(rp,"w",encoding="utf-8").write(json.dumps(out,indent=2))
    sys.exit(6)

ship=zips[-1]

tmp=tempfile.mkdtemp(prefix="mb_repair_")
try:
    with zipfile.ZipFile(ship,"r") as z:
        z.extractall(tmp)

    restored=[]
    for prefix in monitored:
        src=os.path.join(tmp, prefix)
        dst=os.path.join(ROOT, prefix)
        if os.path.exists(src):
            os.makedirs(dst, exist_ok=True)
            # copy tree contents
            for root, dirs, files in os.walk(src):
                rel=os.path.relpath(root, src)
                target=os.path.join(dst, rel) if rel!="." else dst
                os.makedirs(target, exist_ok=True)
                for fn in files:
                    sp=os.path.join(root, fn)
                    dp=os.path.join(target, fn)
                    shutil.copy2(sp, dp)
                    restored.append(os.path.relpath(dp, ROOT))

    # run drift detector
    detector=os.path.join(ROOT,"tools","drift","detect_drift.py")
    proc=subprocess.run(["python3", detector], capture_output=True, text=True)
    drift_out=None
    try:
        drift_out=json.loads(proc.stdout) if proc.stdout.strip() else {"raw":proc.stdout}
    except Exception:
        drift_out={"raw":proc.stdout,"stderr":proc.stderr}

    status="PASS" if proc.returncode==0 else "FAIL"

    report={
      "utc": utc_iso(),
      "ship_zip": os.path.basename(ship),
      "ship_zip_sha256": sha256(ship),
      "restored_count": len(restored),
      "restored_sample": restored[:50],
      "drift_check_returncode": proc.returncode,
      "drift": drift_out,
      "status": status
    }
    os.makedirs(os.path.join(ROOT,"reports"), exist_ok=True)
    rp=os.path.join(ROOT,"reports",f"p14_self_repair_report_{ts()}.json")
    open(rp,"w",encoding="utf-8").write(json.dumps(report,indent=2))

    os.makedirs(os.path.join(ROOT,"receipts"), exist_ok=True)
    rc=os.path.join(ROOT,"receipts",f"p14_self_repair_receipt_{ts()}.json")
    open(rc,"w",encoding="utf-8").write(json.dumps({
      "phase":"P14",
      "utc": report["utc"],
      "status": status,
      "report": os.path.relpath(rp, ROOT),
      "ship_zip": report["ship_zip"]
    }, indent=2))

    sys.exit(0 if status=="PASS" else 7)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
