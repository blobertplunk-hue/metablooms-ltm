#!/usr/bin/env python3
import os, json, time, glob, hashlib, sys
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
def utc_iso(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
def exists(path): return os.path.exists(os.path.join(ROOT, path))
def sha256(path):
    p=os.path.join(ROOT, path)
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(8192), b""):
            h.update(b)
    return h.hexdigest()
checks=[
  ("canonical_root_lock","canonical_root_lock.json"),
  ("boot_policy","config/BOOT_POLICY.json"),
  ("bts_policy","config/BTS_POLICY.json"),
  ("see_gate","config/SEE_GATE.json"),
  ("mpp_gate","config/MPP_GATE.json"),
  ("mpp_guard","tools/mpp/mpp_guard.py"),
  ("bts_tick_runner","tools/bts/bts_tick_runner.py"),
  ("intent_rules_active","config/INTENT_RULES_ACTIVE.json"),
  ("intent_rules_v2","config/INTENT_RULES_v2.json"),
  ("tool_universe","indexes/TOOL_UNIVERSE.json"),
  ("tool_taxonomy","indexes/TOOL_TAXONOMY.json"),
  ("tool_choice_gate","config/TOOL_CHOICE_GATE.json"),
  ("action_wrapper_cfg","config/ACTION_WRAPPER.json"),
  ("action_wrapper","tools/bts/mb_action_wrapper.py"),
  ("task_class_rules","config/TASK_CLASS_RULES.json"),
  ("task_class_classifier","tools/bts/classify_task_class.py"),
]
results=[]
for name,path in checks:
    ok=exists(path)
    rec={"check":name,"path":path,"ok":ok}
    if ok:
        rec["sha256"]=sha256(path)
        rec["size"]=os.path.getsize(os.path.join(ROOT,path))
    results.append(rec)
boot_receipts=glob.glob(os.path.join(ROOT,"boot","boot_receipt_*.json"))
bts_ticks=glob.glob(os.path.join(ROOT,"_bts","bts_tick_receipt_*.json"))
mpp_starts=glob.glob(os.path.join(ROOT,"receipts","mpp_start_receipt_*.json"))
summary={"utc":utc_iso(),"root":ROOT,"checks":results,"counts":{"boot_receipts":len(boot_receipts),"bts_tick_receipts":len(bts_ticks),"mpp_start_receipts":len(mpp_starts)}}
enforce_true=False
if exists("config/TOOL_CHOICE_GATE.json"):
    cfg=json.load(open(os.path.join(ROOT,"config","TOOL_CHOICE_GATE.json"),"r",encoding="utf-8"))
    enforce_true=bool(cfg.get("enforce",False))
summary["tool_choice_enforce"]=enforce_true
hard_ok=all(r["ok"] for r in results)
status="PASS" if (hard_ok and enforce_true) else "FAIL"
summary["status"]=status
out_dir=os.path.join(ROOT,"reports"); os.makedirs(out_dir,exist_ok=True)
ts=time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
report_path=os.path.join(out_dir,f"p8_audit_report_{ts}.json")
open(report_path,"w",encoding="utf-8").write(json.dumps(summary,indent=2))
rec_dir=os.path.join(ROOT,"receipts"); os.makedirs(rec_dir,exist_ok=True)
receipt_path=os.path.join(rec_dir,f"p8_audit_receipt_{ts}.json")
open(receipt_path,"w",encoding="utf-8").write(json.dumps({"phase":"P8","utc":summary["utc"],"status":status,"report":os.path.relpath(report_path,ROOT)},indent=2))
print(receipt_path)
sys.exit(0 if status=="PASS" else 4)
