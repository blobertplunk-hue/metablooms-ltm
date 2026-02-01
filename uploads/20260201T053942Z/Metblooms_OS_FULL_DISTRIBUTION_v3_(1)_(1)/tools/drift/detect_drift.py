#!/usr/bin/env python3
import os, json, hashlib, time, sys

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def sha256(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(8192), b""):
            h.update(b)
    return h.hexdigest()

policy=json.load(open(os.path.join(ROOT,"config","DRIFT_POLICY.json"),"r",encoding="utf-8"))
baseline=json.load(open(os.path.join(ROOT,policy["baseline"]),"r",encoding="utf-8"))

drift=[]
for rel, old_hash in baseline["hashes"].items():
    p=os.path.join(ROOT, rel)
    if not os.path.exists(p):
        drift.append({"path":rel,"type":"MISSING"})
        continue
    new_hash=sha256(p)
    if new_hash!=old_hash:
        drift.append({"path":rel,"type":"MODIFIED","old":old_hash,"new":new_hash})

for root, dirs, files in os.walk(ROOT):
    for fn in files:
        rel=os.path.relpath(os.path.join(root,fn), ROOT)
        if rel in baseline["hashes"]:
            continue
        if any(rel.startswith(p) for p in policy.get("ignore_paths", [])):
            continue
        if any(rel.startswith(p) for p in policy.get("monitored_paths", [])):
            drift.append({"path":rel,"type":"NEW"})

out={"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
     "drift": drift,
     "status": "CLEAN" if not drift else "DRIFT"}
print(json.dumps(out,indent=2))
sys.exit(0 if not drift else 5)
