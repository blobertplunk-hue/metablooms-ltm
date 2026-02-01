#!/usr/bin/env python3
"""
MetaBlooms Prompt Linter (policy-as-code)

Reads: /mnt/data/Metblooms_OS/_policy/PROMPT_LINT_RULES.json

Contract:
- argv[1]: transcript path OR "-" for stdin
- argv[2]: turn_id
- Emits: /mnt/data/Metblooms_OS/_state/PROMPT_LINT_REPORT_<turn_id>.json
- Exit: 0 PASS, 2 FAIL, 3 ERROR
"""
import sys, json, hashlib, re
from pathlib import Path

RULES_PATH = Path("/mnt/data/Metblooms_OS/_policy/PROMPT_LINT_RULES.json")
STATE_DIR  = Path("/mnt/data/Metblooms_OS/_state")

def read_text():
    if len(sys.argv) >= 2 and sys.argv[1] not in ("-", ""):
        return Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
    return sys.stdin.read()

def write_report(turn_id, report):
    (STATE_DIR / f"PROMPT_LINT_REPORT_{turn_id}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

def main():
    turn_id = sys.argv[2] if len(sys.argv) >= 3 else "UNKNOWN"
    try:
        rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        write_report(turn_id, {"pass": False, "error": f"cannot_load_rules: {e}"})
        return 3

    text = read_text()
    report = {
        "rules_id": rules.get("id"),
        "turn_id": turn_id,
        "pass": True,
        "violations": [],
        "metrics": {
            "length_chars": len(text),
        },
        "sha256_input": hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
    }

    # Required sections
    for sec in rules.get("required_sections", []):
        if sec not in text:
            report["pass"] = False
            report["violations"].append({"type":"missing_required_section","section":sec})

    # NEW FULL PROMPT structural checks
    nfp_marker = "NEW FULL PROMPT"
    last_pos = text.rfind(nfp_marker)
    if last_pos < 0:
        report["pass"] = False
        report["violations"].append({"type":"missing_new_full_prompt_marker","marker":nfp_marker})
        nfp_tail = ""
    else:
        nfp_tail = text[last_pos:]

    # must_be_final_section
    if last_pos >= 0:
        # after NEW FULL PROMPT marker, there should be substantial content (not empty)
        if len(nfp_tail.strip()) < 200:
            report["pass"] = False
            report["violations"].append({"type":"new_full_prompt_too_short","min_chars":200,"actual":len(nfp_tail.strip())})

    # checklist invariants must appear somewhere in NEW FULL PROMPT tail
    for rule in rules.get("new_full_prompt_rules", []):
        if rule.get("type") == "checklist" and rule.get("name") == "must_include_invariants":
            for item in rule.get("items", []):
                if item not in nfp_tail:
                    report["pass"] = False
                    report["violations"].append({"type":"missing_invariant_in_new_full_prompt","item":item})

    # Forbidden phrases (regex)
    for fp in rules.get("forbidden_phrases", []):
        if fp.get("type") == "regex":
            pat = fp.get("pattern","")
            try:
                if re.search(pat, text):
                    report["pass"] = False
                    report["violations"].append({"type":"forbidden_phrase_regex","pattern":pat,"description":fp.get("description","")})
            except re.error as e:
                report["pass"] = False
                report["violations"].append({"type":"bad_regex","pattern":pat,"error":str(e)})

    # Forbidden endings
    endings = rules.get("forbidden_endings", [])
    for fe in endings:
        suf = fe.get("suffix")
        if suf and text.rstrip().endswith(suf):
            report["pass"] = False
            report["violations"].append({"type":"forbidden_ending","suffix":suf,"description":fe.get("description","")})

    # Minimum length if provided
    min_len = None
    m = rules.get("metrics")
    if isinstance(m, dict):
        min_len = m.get("min_total_chars")
    if isinstance(min_len, int) and len(text) < min_len:
        report["pass"] = False
        report["violations"].append({"type":"too_short","min":min_len,"actual":len(text)})

    write_report(turn_id, report)
    return 0 if report["pass"] else 2

if __name__ == "__main__":
    sys.exit(main())
