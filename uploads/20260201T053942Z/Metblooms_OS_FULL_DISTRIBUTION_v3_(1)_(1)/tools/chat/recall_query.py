#!/usr/bin/env python3
"""P17.4 Recall Wrapper
Accepts a single query string (with optional inline filters) and runs tools/chat/recall.py.
Supported inline filters (best-effort parsing):
- chat_id:<id>
- topk:<n>
All other tokens are left in the query.
"""
import os, sys, re, subprocess

ROOT=os.environ.get("MB_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
q=" ".join(sys.argv[1:]).strip()
if not q:
    sys.exit("usage: recall_query.py <query>")

chat_id=""
topk="10"

m=re.search(r"\bchat_id:([^\s]+)", q)
if m:
    chat_id=m.group(1); q=re.sub(r"\bchat_id:[^\s]+","",q).strip()
m=re.search(r"\btopk:(\d+)", q)
if m:
    topk=m.group(1); q=re.sub(r"\btopk:\d+","",q).strip()

# Strip prefixes like 'recall:'
q=re.sub(r"^(recall:|remember:|find:)\s*","",q,flags=re.I).strip()

env=os.environ.copy()
env["MB_ROOT"]=ROOT
env["MB_QUERY"]=q
env["MB_TOPK"]=topk
if chat_id:
    env["MB_CHAT_ID"]=chat_id

proc=subprocess.run(["python3", os.path.join(ROOT,"tools","chat","recall.py")], env=env)
raise SystemExit(proc.returncode)
