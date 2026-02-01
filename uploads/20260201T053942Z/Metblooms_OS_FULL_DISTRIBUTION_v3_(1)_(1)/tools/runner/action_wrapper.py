#!/usr/bin/env python3
"""Universal Action Wrapper (P7.9)
All actions must flow through this wrapper to:
1) classify task class
2) record instinct tool
3) evaluate tool choice
4) enforce or warn based on gate config
"""
import os, json, time, subprocess, sys

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

# Inputs via env
user_text=os.environ.get("MB_USER_TEXT","")
instinct_tool=os.environ.get("MB_INSTINCT_TOOL","unknown")

# Classify task class from user text (simple mapping)
task_class="unknown"
if user_text:
    t=user_text.lower()
    if any(k in t for k in ["research","benchmark","compare","best practice","sources"]):
        task_class="external_research"
    elif any(k in t for k in ["pdf","scan","document"]):
        task_class="pdf_analysis"
    elif any(k in t for k in ["upload","corpus","file","index"]):
        task_class="uploaded_corpus_lookup"
    elif any(k in t for k in ["download","export","generate file","deliverable"]):
        task_class="create_user_downloadable_artifact"
    elif any(k in t for k in ["hash","inspect","ls","shell","container"]):
        task_class="shell_inspection_hashing"

# Evaluate tool choice
env=os.environ.copy()
env["MB_TASK_CLASS"]=task_class
env["MB_TOOL_USED"]=instinct_tool

eval_path=os.path.join(ROOT,"tools","bts","evaluate_tool_choice.py")
p = subprocess.run(["python3", eval_path], capture_output=True, text=True, env=env)

# Pass-through execution (actual tool execution is external to wrapper)
out={
  "utc": utc(),
  "task_class": task_class,
  "instinct_tool": instinct_tool,
  "evaluator_stdout": p.stdout.strip(),
  "evaluator_stderr": p.stderr.strip(),
  "returncode": p.returncode
}
print(json.dumps(out))
if p.returncode!=0:
    sys.exit(p.returncode)
