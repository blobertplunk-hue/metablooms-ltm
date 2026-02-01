#!/usr/bin/env python3
"""Deterministic task-class classifier.
Input: rules JSON + free text.
Output: JSON {task_class, confidence, matched_keywords}
"""
import json, sys

rules=json.load(open(sys.argv[1], "r", encoding="utf-8"))
text=" ".join(sys.argv[2:]).lower()

best=None
matched=[]
for tc in rules.get("precedence", []):
    cfg=rules["task_classes"][tc]
    hits=[k for k in cfg.get("keywords",[]) if k in text]
    if hits:
        best=tc
        matched=sorted(set(hits))
        break

out={
  "task_class": best or "unknown",
  "confidence": 0.7 if best else 0.0,
  "matched_keywords": matched
}
print(json.dumps(out))
