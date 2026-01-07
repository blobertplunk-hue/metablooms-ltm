#!/usr/bin/env python3
"""
MetaBlooms Test Suite Runner

Runs all tests and generates comprehensive report.
"""

import subprocess
import sys
import time
from pathlib import Path

TESTS_DIR = Path(__file__).parent

# All test modules in priority order
TESTS = [
    ("test_schema_consistency.py", "Schema consistency across deltas"),
    ("test_mips_index_exists.py", "MIPS Index exists and valid"),
    ("test_runtime_loads_governance.py", "Runtime loads governance deltas"),
    ("test_ledger_integration.py", "Ledger integration in runtime"),
    ("test_contract_violations.py", "Contract violation detection"),
    ("test_csrg_gate.py", "CSRG gate implementation"),
]


def run_test(test_file, description):
    """Run a single test and return result"""
    test_path = TESTS_DIR / test_file

    if not test_path.exists():
        return {"status": "SKIP", "reason": "Test not found", "time": 0}

    start = time.time()

    try:
        result = subprocess.run(
            [sys.executable, str(test_path)],
            capture_output=True,
            text=True,
            timeout=30
        )

        elapsed = time.time() - start

        return {
            "status": "PASS" if result.returncode == 0 else "FAIL",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "time": elapsed,
        }

    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "time": 30}
    except Exception as e:
        return {"status": "ERROR", "reason": str(e), "time": 0}


def main():
    print("=" * 70)
    print("METABLOOMS TEST SUITE")
    print("=" * 70)
    print(f"Running {len(TESTS)} tests...\n")

    results = []
    start_time = time.time()

    for test_file, description in TESTS:
        print(f"Running: {description}")
        result = run_test(test_file, description)
        results.append((test_file, description, result))

        # Print result
        status = result["status"]
        icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⚠️ ", "TIMEOUT": "⏱️ ", "ERROR": "💥"}.get(status, "?")
        print(f"  {icon} {status} ({result['time']:.2f}s)")

        # Print output for failures
        if status in ["FAIL", "ERROR"] and "stdout" in result:
            print("\n" + result["stdout"])

        print()

    total_time = time.time() - start_time

    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    status_counts = {}
    for _, _, result in results:
        status = result["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    print(f"\nTotal: {len(TESTS)} tests in {total_time:.2f}s")
    for status, count in sorted(status_counts.items()):
        icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⚠️ ", "TIMEOUT": "⏱️ ", "ERROR": "💥"}.get(status, "?")
        print(f"  {icon} {status}: {count}")

    # Overall result
    print("\n" + "=" * 70)

    passed = status_counts.get("PASS", 0)
    failed = status_counts.get("FAIL", 0) + status_counts.get("ERROR", 0) + status_counts.get("TIMEOUT", 0)

    if failed == 0:
        print("✅ ALL TESTS PASSED")
        return 0
    else:
        print(f"❌ {failed} TESTS FAILED")
        print("\nSee METABLOOMS_SELF_ANALYSIS_2026-01-06.md for detailed findings")
        return 1


if __name__ == "__main__":
    sys.exit(main())
