#!/usr/bin/env python3
import os, sys, json, hashlib

ROOT = "/mnt/data/Metblooms_OS"
HARNESS_DIR = os.path.join(ROOT, "_harness")
BASELINE_PATH = os.path.join(HARNESS_DIR, "ORACLE_BASELINE_v1.json")
ROEZ = os.path.join(ROOT, "_roez")

def sha256_file(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(8192), b""):
            h.update(c)
    return h.hexdigest()

def walk(include_roez: bool):
    files=[]
    for dp, dns, fns in os.walk(ROOT):
        if not include_roez and os.path.abspath(dp).startswith(os.path.abspath(ROEZ)):
            dns[:] = []
            continue
        dns[:] = [d for d in dns if d != "__pycache__"]
        for fn in fns:
            p=os.path.join(dp,fn)
            if (not include_roez) and os.path.abspath(p).startswith(os.path.abspath(ROEZ)):
                continue
            files.append(os.path.abspath(p))
    return sorted(files)

def snapshot(include_roez: bool):
    return {p: sha256_file(p) for p in walk(include_roez)}

def write_baseline():
    data={
        "version":"v1",
        "root":ROOT,
        "mode":"baseline_include_roez_once",
        "files": snapshot(include_roez=True)
    }
    with open(BASELINE_PATH,"w") as f:
        json.dump(data,f,indent=2,sort_keys=True)
    return 0

def verify():
    if not os.path.exists(BASELINE_PATH):
        print("BASELINE_MISSING", file=sys.stderr); return 2
    with open(BASELINE_PATH,"r") as f:
        base=json.load(f).get("files",{})
    cur=snapshot(include_roez=False)
    mism=[]
    for p,h in base.items():
        if p.startswith(os.path.abspath(ROEZ)):
            continue
        if p not in cur: mism.append({"missing":p})
        elif cur[p]!=h: mism.append({"mismatch":p})
    for p in cur:
        if p not in base: mism.append({"extra":p})
    if mism:
        print(json.dumps({"result":"FAIL","mismatches":mism},indent=2,sort_keys=True)); return 1
    print(json.dumps({"result":"PASS","checked":len(cur)},indent=2,sort_keys=True)); return 0

def main(argv):
    if "--baseline" in argv:
        return write_baseline()
    return verify()

if __name__=="__main__":
    raise SystemExit(main(sys.argv[1:]))
