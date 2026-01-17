import os
import json
import hashlib
from typing import List, Dict

class EvidenceStore:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir

    def alloc_attempt_dir(self, task_id: str, iteration: int) -> str:
        path = os.path.join(self.root_dir, task_id, f"iter_{iteration:03d}")
        os.makedirs(path, exist_ok=True)
        return path

    def sha256(self, path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def list_artifacts_with_hashes(self, paths: List[str]) -> List[Dict[str, str]]:
        out = []
        for p in paths:
            out.append({"path": p, "sha256": self.sha256(p)})
        return out

    def write_receipt(self, attempt_dir: str, receipt: Dict) -> str:
        path = os.path.join(attempt_dir, "receipt.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2, sort_keys=True)
        return path
