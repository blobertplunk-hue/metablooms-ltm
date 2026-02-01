#!/usr/bin/env python3
import os, json, sys, time, re
from collections import defaultdict

ROOT=os.environ.get("MB_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
QUERY=(os.environ.get("MB_QUERY","") or "").strip()
CHAT_ID=(os.environ.get("MB_CHAT_ID","") or "").strip()
TOPK=int(os.environ.get("MB_TOPK","10"))

def utc(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
def tokenize(t):
    t=t.lower()
    t=re.sub(r"[^a-z0-9\s]+"," ",t)
    return [w for w in t.split() if w]

SYN={"remember":["recall","find"],"error":["fail","bug","issue"],"boot":["startup","initialize"],"index":["indexed","indexing","merkle"]}
def expand(tokens):
    out=set(tokens)
    for t in list(tokens):
        if t in SYN: out.update(SYN[t])
        for k,v in SYN.items():
            if t in v: out.add(k)
    return sorted(out)

if not QUERY:
    print(json.dumps({"utc":utc(),"status":"ERROR","error":"MB_QUERY is required"})); sys.exit(2)

inv_path=os.path.join(ROOT,"indexes","chat","inverted.json")
if not os.path.exists(inv_path):
    print(json.dumps({"utc":utc(),"status":"ERROR","error":"inverted index missing"})); sys.exit(3)
inv=json.load(open(inv_path,"r",encoding="utf-8"))

tokens=expand(tokenize(QUERY))
scores=defaultdict(int); hits_by_token=defaultdict(int)
for tok in tokens:
    postings=inv.get(tok,[])
    if not isinstance(postings,list): continue
    for p in postings:
        cid=p.get("chat_id"); tid=p.get("turn_id")
        if CHAT_ID and cid!=CHAT_ID: continue
        if not cid or not tid: continue
        scores[f"{cid}::{tid}"]+=1
        hits_by_token[tok]+=1

ranked=sorted(scores.items(), key=lambda kv:(-kv[1], kv[0]))[:TOPK]

def snippet(cid,tid):
    path=os.path.join(ROOT,"chat_store",cid,"turns.ndjson")
    if not os.path.exists(path): return None
    try:
        with open(path,"r",encoding="utf-8") as f:
            for line in f:
                try: row=json.loads(line)
                except Exception: continue
                if str(row.get("turn_id"))==str(tid):
                    c=" ".join(str(row.get("content","")).split())
                    return c[:240] + ("…" if len(c)>240 else "")
    except Exception:
        return None
    return None

results=[]
for key,score in ranked:
    cid,tid=key.split("::",1)
    results.append({"chat_id":cid,"turn_id":tid,"score":score,"snippet":snippet(cid,tid)})

print(json.dumps({"utc":utc(),"status":"OK","query":QUERY,"tokens":tokens,"token_posting_counts":hits_by_token,"results":results},
                 ensure_ascii=False, indent=2))
