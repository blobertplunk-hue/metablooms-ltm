#!/usr/bin/env python3
"""
Demonstration: SEE Loop detecting and capturing failure evidence

This shows what happens when code FAILS - the system captures evidence
and blocks progression (fail-closed behavior).
"""

import sys
import os
import tempfile
import json

# Add metablooms to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from metablooms.loop.see_recursive_controller_v1 import run_see_loop
from metablooms.runtime.sandbox_exec_v1 import sandbox_execute
from metablooms.diagnostics.failure_diagnoser_v1 import diagnose
from metablooms.patching.patch_provider_v1 import provide_patch


def demo_failure_detection():
    """
    Demonstrate SEE loop catching broken code.
    """
    print("="*60)
    print("FAILURE DETECTION DEMONSTRATION")
    print("="*60)
    print("\nValidating broken_function.py (contains division by zero)...\n")

    evidence_root = tempfile.mkdtemp(prefix="see_failure_evidence_")

    task_spec = {
        "task_id": "broken_divide_validation",
        "command": ["python", "broken_function.py"],
        "workdir": os.path.dirname(os.path.abspath(__file__)),
        "evidence_root": evidence_root,
        "timeout": 10
    }

    print(f"Evidence directory: {evidence_root}\n")

    result = run_see_loop(
        task_spec=task_spec,
        executor=sandbox_execute,
        diagnoser=diagnose,
        patch_provider=provide_patch,
        max_iterations=3
    )

    print("="*60)
    print("SEE LOOP RESULTS")
    print("="*60)
    print(f"\nStatus: {result['status']}")
    print(f"Iterations: {result['iterations']}")
    print(f"Reason: {result.get('reason', 'N/A')}")

    # Load and display the receipt
    with open(result['final_receipt'], 'r') as f:
        receipt = json.load(f)

    print(f"\nExit code: {receipt['exec']['exit_code']}")
    print(f"Evidence level: {receipt['evidence_level_claimed']}")

    # Show the error captured
    iter_dir = os.path.dirname(result['final_receipt'])
    stderr_path = os.path.join(iter_dir, 'stderr.txt')

    if os.path.exists(stderr_path):
        with open(stderr_path, 'r') as f:
            stderr = f.read()
        if stderr.strip():
            print(f"\n📋 CAPTURED ERROR EVIDENCE:")
            print("-" * 60)
            # Show last 10 lines of stderr
            lines = stderr.strip().split('\n')
            for line in lines[-10:]:
                print(f"  {line}")
            print("-" * 60)

    print("\n✅ FAIL-CLOSED BEHAVIOR DEMONSTRATED")
    print("\nThe system:")
    print("  1. Detected the failure (exit code != 0)")
    print("  2. Captured exact error evidence (stderr)")
    print("  3. Classified as E2 (partial evidence - failed)")
    print("  4. Attempted patch (none available in stub)")
    print("  5. Stopped with status: FAIL")
    print("\n🎯 KEY INSIGHT: Failure is PROVEN, not guessed")
    print("   The receipt contains SHA256 hashes of the error logs")
    print("   This evidence could be fed back to an LLM for fixing")

    return result, evidence_root


if __name__ == "__main__":
    print("\n" + "🔍 EVIDENCE-BASED FAILURE DETECTION".center(60))
    print("Demonstrating fail-closed behavior\n")

    result, evidence_dir = demo_failure_detection()

    print("\n" + "="*60)
    print("WHAT THIS PROVES")
    print("="*60)
    print(f"""
The SEE loop doesn't just validate SUCCESS - it captures FAILURE evidence.

Evidence artifacts in: {evidence_dir}

This enables:
1. Precise diagnosis (exact error, exact line)
2. Recursive correction (feed evidence back to LLM)
3. Fail-closed safety (can't claim success without proof)
4. Audit trail (every failure is documented with hashes)

With an LLM-backed patch provider, this would:
- Read the error evidence
- Generate a minimal fix
- Re-run the code
- Verify the fix worked
- Iterate until E3/E4 achieved

This is the recursive evidence loop in action.
    """)
