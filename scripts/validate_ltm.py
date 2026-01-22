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
- This does NOT enforce append-only across git history; it validates current repo contents.
"""

import json
import hashlib
from pathlib import Path
import sys

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]

# Constants
SHA256_HEX_LENGTH = 64

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

def validate_path_format(path, context: str):
    """Validate that a path is a non-empty string."""
    ensure(isinstance(path, str) and path.strip(),
           f"{context} path must be a non-empty string")

def validate_sha256_format(sha256, context: str):
    """Validate that a SHA256 hash is a 64-character hex string."""
    ensure(isinstance(sha256, str) and len(sha256) == SHA256_HEX_LENGTH,
           f"{context} sha256 must be a {SHA256_HEX_LENGTH}-char hex string")

def verify_file_hash(file_path: Path, expected_sha256: str, relative_path: str):
    """Verify that a file exists and its SHA256 hash matches the expected value."""
    ensure(file_path.exists(), f"File missing: {relative_path}")
    computed = sha256_text(read_text(file_path))
    ensure(computed == expected_sha256,
           f"SHA256 mismatch for {relative_path}: expected {expected_sha256}, got {computed}")

def verify_snapshot(state: dict):
    """Verify snapshot file existence and hash if state type is 'snapshot'."""
    if state.get("type") != "snapshot":
        return

    snap_path = state.get("snapshot_path")
    snap_sha = state.get("snapshot_sha256")

    validate_path_format(snap_path, "latest.state.snapshot_path")
    validate_sha256_format(snap_sha, "latest.state.snapshot_sha256")

    snap_file = ROOT / snap_path
    verify_file_hash(snap_file, snap_sha, snap_path)

def verify_deltas(deltas: list):
    """Verify all delta files exist and their hashes match."""
    for i, delta in enumerate(deltas):
        path = delta.get("path")
        sha = delta.get("sha256")

        validate_path_format(path, f"Delta[{i}]")
        validate_sha256_format(sha, f"Delta[{i}]")

        delta_file = ROOT / path
        verify_file_hash(delta_file, sha, path)

def verify_ledger_ndjson(ledger_path: Path):
    """Verify that the ledger file is valid NDJSON (one JSON object per line)."""
    for ln, line in enumerate(read_text(ledger_path).splitlines(), start=1):
        if not line.strip():
            continue
        try:
            json.loads(line)
        except Exception as e:
            raise RuntimeError(f"Ledger NDJSON invalid JSON at line {ln}: {e}")

def main():
    # Required paths
    for rel in REQUIRED:
        p = ROOT / rel
        ensure(p.exists(), f"Missing required file: {rel}")

    # Load manifests
    bootstrap = read_json(ROOT / "manifests/bootstrap.json")
    latest = read_json(ROOT / "manifests/latest.json")

    # Schema validation
    validate_schema(bootstrap, ROOT / "schemas/manifest.bootstrap.schema.json")
    validate_schema(latest, ROOT / "schemas/manifest.latest.schema.json")

    # Content verification
    verify_snapshot(latest.get("state", {}))
    verify_deltas(latest.get("deltas", []))
    verify_ledger_ndjson(ROOT / "ledger/ledger.ndjson")

    print("OK: MetaBlooms LTM validation passed.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
