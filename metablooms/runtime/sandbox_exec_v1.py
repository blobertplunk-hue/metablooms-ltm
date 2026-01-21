import subprocess
import os
import time
import sys
import json
import platform
from metablooms.evidence.store_v1 import EvidenceStore

def sandbox_execute(task_spec: dict, iteration: int) -> dict:
    store = EvidenceStore(task_spec["evidence_root"])
    attempt_dir = store.alloc_attempt_dir(task_spec["task_id"], iteration)

    stdout_path = os.path.join(attempt_dir, "stdout.txt")
    stderr_path = os.path.join(attempt_dir, "stderr.txt")

    start = time.time()
    proc = subprocess.Popen(
        task_spec["command"],
        cwd=task_spec["workdir"],
        stdout=open(stdout_path, "w"),
        stderr=open(stderr_path, "w"),
        text=True,
    )
    exit_code = proc.wait(timeout=task_spec.get("timeout", 30))
    end = time.time()

    artifacts = store.list_artifacts_with_hashes([stdout_path, stderr_path])

    receipt = {
        "receipt_version": "v1",
        "task_id": task_spec["task_id"],
        "iteration": iteration,
        "command": task_spec["command"],
        "workdir": task_spec["workdir"],
        "exec": {
            "exit_code": exit_code,
            "duration_ms": int((end - start) * 1000),
        },
        "artifacts": artifacts,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
        },
        "evidence_level_claimed": "E3" if exit_code == 0 else "E2",
    }

    receipt_path = store.write_receipt(attempt_dir, receipt)

    return {
        "success": exit_code == 0,
        "exit_code": exit_code,
        "receipt_path": receipt_path,
        "stdout": stdout_path,
        "stderr": stderr_path,
    }
