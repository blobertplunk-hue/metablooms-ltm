#!/usr/bin/env python3
"""MetaBlooms Action Wrapper (P7.9)
- Classifies task class from MB_USER_TEXT unless MB_TASK_CLASS provided
- Evaluates tool choice (instinct vs governed best) via evaluate_tool_choice.py
- Logs a single ledger entry per invocation
- If gate.enforce=true and violation -> exits nonzero
"""
import os, json, time, subprocess, sys

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

cfg=json.load(open(os.path.join(ROOT,"config","ACTION_WRAPPER.json"),"r",encoding="utf-8"))
gate=json.load(open(os.path.join(ROOT,"config","TOOL_CHOICE_GATE.json"),"r",encoding="utf-8"))

user_text=os.environ.get(cfg["env"]["user_text"], "") or ""
tool_used=os.environ.get(cfg["env"]["tool_used"], "") or "unknown"
task_override=os.environ.get(cfg["env"]["task_class_override"], "").strip()

# Determine task class
task_class="unknown"
matched=[]
if task_override:
    task_class=task_override
else:
    rules_path=os.path.join(ROOT, cfg["task_rules"])
    p=subprocess.run(["python3", os.path.join(ROOT,"tools","bts","classify_task_class.py"), rules_path, user_text],
                     capture_output=True, text=True)
    try:
        out=json.loads(p.stdout.strip() or "{}")
        task_class=out.get("task_class","unknown")
        matched=out.get("matched_keywords",[]) or []
    except Exception:
        task_class="unknown"

# Run evaluator (writes to tool_choice_audit ledger)
os.environ["MB_TASK_CLASS"]=task_class
os.environ["MB_TOOL_USED"]=tool_used
eval_proc=subprocess.run(["python3", os.path.join(ROOT,"tools","bts","evaluate_tool_choice.py")],
                         capture_output=True, text=True)
verdict_txt=eval_proc.stdout.strip()

try:
    verdict=json.loads(verdict_txt) if verdict_txt else {"status":"UNKNOWN"}
except Exception:
    verdict={"status":"UNKNOWN","raw":verdict_txt}

# Append wrapper ledger
ledger=os.path.join(ROOT, cfg["ledger"])
os.makedirs(os.path.dirname(ledger), exist_ok=True)
entry={
  "utc": utc(),
  "task_class": task_class,
  "matched_keywords": matched,
  "tool_used": tool_used,
  "verdict": verdict,
  "enforce": bool(gate.get("enforce", False))
}
with open(ledger,"a",encoding="utf-8") as f:
    f.write(json.dumps(entry)+"\n")

# Enforcement
if gate.get("enforce", False) and verdict.get("status")=="FAIL":
    sys.exit(3)

print(json.dumps({"status":"OK","task_class":task_class,"tool_used":tool_used,"verdict":verdict}))
