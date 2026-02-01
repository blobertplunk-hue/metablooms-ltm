#!/usr/bin/env python3
"""P17.1 Chat Turn Capture Hook
Append-only capture of every user/assistant/tool turn into per-chat NDJSON.
"""
import os, json, time, hashlib, sys

ROOT=os.environ.get("MB_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHAT_ID=os.environ.get("MB_CHAT_ID","default_chat")

def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

# Expect env-provided payload
payload=os.environ.get("MB_TURN_PAYLOAD")
if not payload:
    sys.exit(0)

data=json.loads(payload)

store=os.path.join(ROOT,"chat_store",CHAT_ID)
os.makedirs(store, exist_ok=True)
path=os.path.join(store,"turns.ndjson")

row={
  "chat_id": CHAT_ID,
  "turn_id": data.get("turn_id"),
  "role": data.get("role"),
  "utc": data.get("utc") or utc(),
  "content_sha256": sha256_text(data.get("content","")),
  "content": data.get("content",""),
  "tool_events": data.get("tool_events",[]),
  "receipts": data.get("receipts",[])
}

with open(path,"a",encoding="utf-8") as f:
    f.write(json.dumps(row, ensure_ascii=False)+"\n")
