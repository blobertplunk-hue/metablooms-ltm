import os

def detect_missing_middle(root: str) -> list:
    findings = []

    required_paths = [
        "metablooms/loop/see_recursive_controller_v1.py",
        "metablooms/runtime/sandbox_exec_v1.py",
        "metablooms/evidence/store_v1.py",
    ]

    for p in required_paths:
        if not os.path.exists(os.path.join(root, p)):
            findings.append({
                "severity": "BLOCK",
                "category": "PLAN_CODE",
                "missing": p,
            })

    return findings
