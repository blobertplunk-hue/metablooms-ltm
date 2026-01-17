from metablooms.validators.missing_middle_detector_v1 import detect_missing_middle

GATE_ID = "GATE.EVIDENCE.SEE.LOOP.V1"
P0 = False  # promote later

def run_gate(context, ledger_writer=None):
    root = context.get("root") or "."
    findings = detect_missing_middle(root)

    ok = len(findings) == 0
    out = {
        "gate_id": GATE_ID,
        "p0": P0,
        "ok": ok,
        "errors": findings if not ok else [],
    }

    if ledger_writer:
        ledger_writer({"event_type": "GATE_RESULT", **out})

    return out
