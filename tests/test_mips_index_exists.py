#!/usr/bin/env python3
"""
Test: MIPS Index Exists

Verifies that MIPS_INDEX_CORE.mips.json exists and is valid.
Expected failure: Index missing.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "MIPS_INDEX_CORE.mips.json"


def main():
    print("=" * 70)
    print("TEST: MIPS Index Exists")
    print("=" * 70)

    if not INDEX_PATH.exists():
        print(f"\n❌ FAIL: Index not found at {INDEX_PATH}")
        print("\nIMPACT: Cannot determine active deltas, load order, conflicts")
        print("FIX: Implement scripts/generate_mips_index.py")
        return 1

    try:
        with open(INDEX_PATH) as f:
            index = json.load(f)

        # Verify required fields
        required = ["boot", "runtime", "registry", "timestamps"]
        missing = [f for f in required if f not in index]

        if missing:
            print(f"\n❌ FAIL: Index missing required fields: {missing}")
            return 1

        print(f"\n✅ PASS: Index exists with {len(index.get('registry', {}))} modules")
        return 0

    except Exception as e:
        print(f"\n❌ FAIL: Index exists but invalid: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
