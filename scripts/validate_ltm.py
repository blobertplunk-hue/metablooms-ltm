#!/usr/bin/env python3
"""
MetaBlooms LTM repo validator (fail-closed).
Checks:
- Required paths exist.
- manifests/latest.json validates against schemas/manifest.latest.schema.json
- manifests/bootstrap.json validates against schemas/manifest.bootstrap.schema.json
- If latest.state.type == "snapshot": referenced snapshot exists and sha256 matches
- For each delta in latest.deltas: referenced file exists and sha256 matches
- ledger/ledger.ndjson is valid NDJSON (each non-empty line is valid JSON)
Notes:
- This does NOT attempt to enforce append-only across history (needs git diff context).
  In PR context, you can add an additional step to diff against base branch if desired.
"""

import json
import hashlib
from pathlib import Path
import sys

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "manifests/bootstrap.json",
    "manifests/latest.json",
    "ledger/ledger.ndjson",
    "schemas/manifest.bootstrap.schema.json",
    "schemas/manifest.latest.schema.json",
    "schemas/ledger.event.schema.json",
]

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def read_json(path: Path):
    return json.loads(read_text(path))

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def ensure(cond: bool, msg: str):
    if not cond:
        raise RuntimeError(msg)

def validate_schema(instance, schema_path: Path):
    schema = read_json(schema_path)
    v = Draft202012Validator(schema)
    errors = sorted(v.iter_errors(instance), key=lambda e: e.path)
    if errors:
        msg = "\n".join([f"- {list(e.path)}: {e.message}" for e in errors])
        raise RuntimeError(f"Schema validation failed for {schema_path}:\n{msg}")

def main():
    # Required paths
    for rel in REQUIRED:
        p = ROOT / rel
        ensure(p.exists(), f"Missing required file: {rel}")

    bootstrap = read_json(ROOT / "manifests/bootstrap.json")
    latest = read_json(ROOT / "manifests/latest.json")

    # Schema validation
    validate_schema(bootstrap, ROOT / "schemas/manifest.bootstrap.schema.json")
    validate_schema(latest, ROOT / "schemas/manifest.latest.schema.json")

    # Snapshot / deltas
    state = latest.get("state", {})
    stype = state.get("type")

    if stype == "snapshot":
        snap_path = state.get("snapshot_path")
        snap_sha = state.get("snapshot_sha256")
        ensure(isinstance(snap_path, str) and snap_path.strip(), "latest.state.snapshot_path must be a non-empty string for snapshot state")
        ensure(isinstance(snap_sha, str) and len(snap_sha) == 64, "latest.state.snapshot_sha256 must be a 64-char hex string for snapshot state")

        snap_file = ROOT / snap_path
        ensure(snap_file.exists(), f"Snapshot file missing: {snap_path}")

        computed = sha256_text(read_text(snap_file))
        ensure(computed == snap_sha, f"Snapshot sha256 mismatch for {snap_path}: expected {snap_sha}, got {computed}")

    # Delta verification
    for i, d in enumerate(latest.get("deltas", [])):
        path = d.get("path")
        sha = d.get("sha256")
        ensure(isinstance(path, str) and path.strip(), f"Delta[{i}] path must be non-empty string")
        ensure(isinstance(sha, str) and len(sha) == 64, f"Delta[{i}] sha256 must be 64-char hex string")

        f = ROOT / path
        ensure(f.exists(), f"Delta file missing: {path}")
        computed = sha256_text(read_text(f))
        ensure(computed == sha, f"Delta sha256 mismatch for {path}: expected {sha}, got {computed}")

    # Ledger NDJSON sanity (JSON parse only)
    ledger_path = ROOT / "ledger/ledger.ndjson"
    for ln, line in enumerate(read_text(ledger_path).splitlines(), start=1):
        if not line.strip():
            continue
        try:
            json.loads(line)
        except Exception as e:
            raise RuntimeError(f"Ledger NDJSON invalid JSON at line {ln}: {e}")

    print("OK: MetaBlooms LTM validation passed.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
