#!/usr/bin/env python3
import os, json
from collections import defaultdict

ROOT=os.environ.get("MB_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
cfg=json.load(open(os.path.join(ROOT,"config","TOOL_SCORING.json"),"r",encoding="utf-8"))
text=(os.environ.get("MB_USER_TEXT","") or "").lower()

scores=defaultdict(int)
for k,v in cfg.get("base_scores",{}).items():
    scores[k]+=int(v)
for rule in cfg.get("rules",[]):
    if any(c.lower() in text for c in rule.get("if_contains",[])):
        for tool,boost in rule.get("boost",{}).items():
            scores[tool]+=int(boost)

ranked=sorted([{"tool":t,"score":s} for t,s in scores.items()], key=lambda x:(-x["score"], x["tool"]))
rec=ranked[0]["tool"] if ranked else "unknown"
print(json.dumps({"ranked":ranked,"recommended":rec}, indent=2))
