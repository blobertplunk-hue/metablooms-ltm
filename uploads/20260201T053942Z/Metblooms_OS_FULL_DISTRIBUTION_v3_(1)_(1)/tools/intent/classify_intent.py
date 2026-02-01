#!/usr/bin/env python3
"""Deterministic intent classifier for MetaBlooms.
Returns intent + whether MPP is required.
"""
import json, sys, re

rules=json.load(open(sys.argv[1], "r", encoding="utf-8"))
text=" ".join(sys.argv[2:]).lower()

detected=[]
for intent in rules["precedence"]:
    cfg=rules["intents"][intent]
    for p in cfg["patterns"]:
        if p in text:
            detected.append(intent)
            break

intent = detected[0] if detected else "reasoning_only"
out = {
  "intent": intent,
  "mpp_required": rules["intents"][intent]["mpp_required"]
}
print(json.dumps(out))
