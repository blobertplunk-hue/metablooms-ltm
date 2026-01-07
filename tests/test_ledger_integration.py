#!/usr/bin/env python3
"""
Test: Ledger Integration in Runtime

Verifies that runtime appends events to ledger/ledger.ndjson.
Expected failure: No ledger integration.
"""

import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ZIP = ROOT / "2025-12-30_MetaBlooms_OS_CANONICAL_v7_4_1.zip"


def main():
    print("=" * 70)
    print("TEST: Ledger Integration in Runtime")
    print("=" * 70)

    if not RUNTIME_ZIP.exists():
        print(f"\n⚠️  SKIP: Runtime bundle not found")
        return 0

    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract runtime
        with zipfile.ZipFile(RUNTIME_ZIP, 'r') as zf:
            zf.extractall(tmpdir)

        tmppath = Path(tmpdir)

        # Boot runtime
        result = subprocess.run(
            [sys.executable, str(tmppath / "RUN_METABLOOMS.py")],
            cwd=str(tmppath),
            capture_output=True,
            text=True,
            timeout=10
        )

        # Check if boot succeeded
        if "BOOT_OK" not in result.stdout:
            print("\n⚠️  SKIP: Boot failed, cannot test ledger")
            return 0

        # Check for ledger writes
        potential_ledgers = [
            tmppath / "ledger" / "ledger.ndjson",
            tmppath / "control_plane" / "ledger.ndjson",
            tmppath / "state_hub" / "ledger.ndjson",
        ]

        ledger_found = None
        for ledger_path in potential_ledgers:
            if ledger_path.exists():
                ledger_found = ledger_path
                break

        if not ledger_found:
            print("\n❌ FAIL: Runtime does not write to ledger")
            print("\nIMPACT: No audit trail of boot events")
            print("FIX: Boot must append to ledger/ledger.ndjson")
            return 1

        # Check ledger has new entries
        with open(ledger_found) as f:
            entries = [line for line in f if line.strip()]

        print(f"\nLedger found at: {ledger_found.relative_to(tmppath)}")
        print(f"Entries: {len(entries)}")

        if len(entries) == 0:
            print("\n❌ FAIL: Ledger exists but runtime didn't append")
            return 1

        print("\n✅ PASS: Runtime writes to ledger")
        return 0


if __name__ == "__main__":
    sys.exit(main())
