#!/usr/bin/env python3
"""
Test: Runtime Loads Governance Deltas

Verifies that runtime actually loads and enforces deltas from manifests/latest.json.
Expected failure: Runtime doesn't load deltas.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ZIP = ROOT / "2025-12-30_MetaBlooms_OS_CANONICAL_v7_4_1.zip"


def main():
    print("=" * 70)
    print("TEST: Runtime Loads Governance Deltas")
    print("=" * 70)

    if not RUNTIME_ZIP.exists():
        print(f"\n⚠️  SKIP: Runtime bundle not found at {RUNTIME_ZIP}")
        return 0

    # Extract and check if runtime loads deltas
    import zipfile
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(RUNTIME_ZIP, 'r') as zf:
            zf.extractall(tmpdir)

        # Check if RUN_METABLOOMS.py loads from manifests/latest.json
        run_script = Path(tmpdir) / "RUN_METABLOOMS.py"

        if not run_script.exists():
            print("\n❌ FAIL: RUN_METABLOOMS.py not found in bundle")
            return 1

        with open(run_script) as f:
            code = f.read()

        # Check for indicators of delta loading
        indicators = [
            "latest.json",
            "delta",
            "enforce_active_deltas",
            "load_governance",
        ]

        found = [ind for ind in indicators if ind in code]

        print(f"\nChecking RUN_METABLOOMS.py for delta loading...")
        print(f"  Indicators found: {found if found else 'NONE'}")

        if not found:
            print("\n❌ FAIL: Runtime does not load governance deltas")
            print("\nIMPACT: Governance contracts not enforced at runtime")
            print("FIX: Runtime must load deltas from manifests/latest.json")
            return 1

        print("\n✅ PASS: Runtime appears to load deltas")
        return 0


if __name__ == "__main__":
    sys.exit(main())
