import json
import os
from metablooms.evidence.store_v1 import EvidenceStore

REQUIRED_FIELDS = {
    "receipt_version",
    "task_id",
    "iteration",
    "command",
    "workdir",
    "exec",
    "artifacts",
    "environment",
    "evidence_level_claimed",
}

def validate_receipt(receipt_path: str) -> None:
    if not os.path.exists(receipt_path):
        raise ValueError("RECEIPT_NOT_FOUND")

    data = json.load(open(receipt_path, "r", encoding="utf-8"))
    missing = REQUIRED_FIELDS - set(data.keys())
    if missing:
        raise ValueError(f"RECEIPT_MISSING_FIELDS:{sorted(missing)}")

    store = EvidenceStore("/")
    for artifact in data["artifacts"]:
        path = artifact["path"]
        if not os.path.exists(path):
            raise ValueError(f"ARTIFACT_MISSING:{path}")
        if store.sha256(path) != artifact["sha256"]:
            raise ValueError(f"HASH_MISMATCH:{path}")
