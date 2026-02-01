#!/usr/bin/env python3
"""Tool-choice evaluator (deterministic)
Inputs: env MB_TASK_CLASS, MB_TOOL_USED
Outputs: JSON verdict, appends to ledger if configured.
"""
import os, json, time

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

task=os.environ.get("MB_TASK_CLASS","").strip() or "unknown"
used=os.environ.get("MB_TOOL_USED","").strip() or "unknown"

tax=json.load(open(os.path.join(ROOT,"indexes","TOOL_TAXONOMY.json"),"r",encoding="utf-8"))
cfg=json.load(open(os.path.join(ROOT,"config","TOOL_CHOICE_GATE.json"),"r",encoding="utf-8"))

best = tax.get("task_classes",{}).get(task,{}).get("best_tool","unknown")
status = "PASS" if best=="unknown" or used==best else "FAIL"

verdict={
  "utc": utc(),
  "task_class": task,
  "tool_used": used,
  "best_tool": best,
  "status": status
}

ledger_path=os.path.join(ROOT, cfg.get("log_ledger","bts/tool_choice_audit.ndjson"))
os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
with open(ledger_path,"a",encoding="utf-8") as f:
    f.write(json.dumps(verdict)+"\n")

print(json.dumps(verdict))
if cfg.get("enforce", False) and status=="FAIL":
    raise SystemExit(3)
