#!/usr/bin/env python3
import os, json, hashlib, sys, time, re

ROOT=os.environ.get("MB_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHAT_ID=os.environ.get("MB_CHAT_ID","default_chat")

def sha256_text(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()
def tokenize(text):
    text=text.lower()
    text=re.sub(r"[^a-z0-9\s]+"," ",text)
    return [t for t in text.split() if t]

store=os.path.join(ROOT,"chat_store",CHAT_ID,"turns.ndjson")
if not os.path.exists(store):
    sys.exit(0)

with open(store,"rb") as f:
    try:
        f.seek(-2, os.SEEK_END)
        while f.read(1) != b"\n":
            f.seek(-2, os.SEEK_CUR)
    except OSError:
        f.seek(0)
    last=f.readline().decode("utf-8")

row=json.loads(last)
turn_id=row.get("turn_id")
content=row.get("content","")

inv_path=os.path.join(ROOT,"indexes","chat","inverted.json")
inv=json.load(open(inv_path,"r",encoding="utf-8")) if os.path.exists(inv_path) else {}
for tok in tokenize(content):
    inv.setdefault(tok,[]).append({"chat_id":CHAT_ID,"turn_id":turn_id})
json.dump(inv, open(inv_path,"w",encoding="utf-8"), indent=2)

merkle_path=os.path.join(ROOT,"indexes","chat","merkle.json")
prev=json.load(open(merkle_path,"r",encoding="utf-8")).get("root","") if os.path.exists(merkle_path) else ""
new_root=sha256_text(prev + sha256_text(content))
json.dump({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "root": new_root, "last_turn": turn_id},
          open(merkle_path,"w",encoding="utf-8"), indent=2)

print(json.dumps({"chat_id":CHAT_ID,"turn_id":turn_id,"tokens_indexed":len(tokenize(content)),"merkle_root":new_root}, indent=2))
