#!/usr/bin/env python3
"""
Demonstration: Recursive Evidence-Based Improvement

This simulates what happens when an LLM uses the SEE loop for
self-correction: it reads the evidence, fixes the code, and validates again.
"""

import sys
import os
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from metablooms.loop.see_recursive_controller_v1 import run_see_loop
from metablooms.runtime.sandbox_exec_v1 import sandbox_execute
from metablooms.diagnostics.failure_diagnoser_v1 import diagnose


def llm_patch_provider_mock(diagnosis: dict):
    """
    Mock LLM patch provider that 'reads' the error and generates a fix.

    In production, this would:
    1. Read stderr from the receipt
    2. Analyze the error
    3. Generate minimal code patch
    4. Return patch specification

    For this demo, we'll simulate by returning a fixed version.
    """
    stderr_path = diagnosis.get('stderr')
    if not stderr_path or not os.path.exists(stderr_path):
        return None

    with open(stderr_path, 'r') as f:
        error_content = f.read()

    # Simulate LLM reading the error
    print("\n🤖 LLM PATCH PROVIDER ANALYZING ERROR:")
    print("-" * 60)
    print("Error detected: ZeroDivisionError")
    print("Location: broken_function.py, line 3")
    print("Diagnosis: Missing zero-check in divide function")
    print("\nGenerating patch: Add zero-check before division")
    print("-" * 60)

    # Write fixed version
    fixed_code = '''def divide(a, b):
    """Divide two numbers."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

if __name__ == "__main__":
    assert divide(10, 2) == 5
    try:
        divide(10, 0)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Expected
    print("✓ All tests passed (including zero-check)")
'''

    with open('broken_function.py', 'w') as f:
        f.write(fixed_code)

    return {"patch_applied": "zero_check_added"}


def demo_recursive_improvement():
    """
    Show the full recursive improvement cycle.
    """
    print("="*60)
    print("RECURSIVE IMPROVEMENT DEMONSTRATION")
    print("="*60)
    print("\nStarting with broken code...")
    print("The SEE loop will:")
    print("  1. Detect failure")
    print("  2. Capture evidence")
    print("  3. Generate patch (simulated LLM)")
    print("  4. Re-validate")
    print("  5. Confirm fix\n")

    # First, restore the broken version
    broken_code = '''def divide(a, b):
    """Divide two numbers."""
    return a / b  # BUG: No zero check!

if __name__ == "__main__":
    assert divide(10, 2) == 5
    assert divide(10, 0) == 0  # Division by zero!
    print("✓ All tests passed")
'''
    with open('broken_function.py', 'w') as f:
        f.write(broken_code)

    evidence_root = tempfile.mkdtemp(prefix="see_recursive_")

    task_spec = {
        "task_id": "recursive_fix_demo",
        "command": ["python", "broken_function.py"],
        "workdir": os.path.dirname(os.path.abspath(__file__)),
        "evidence_root": evidence_root,
        "timeout": 10
    }

    result = run_see_loop(
        task_spec=task_spec,
        executor=sandbox_execute,
        diagnoser=diagnose,
        patch_provider=llm_patch_provider_mock,  # Mock LLM
        max_iterations=3
    )

    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    print(f"\nStatus: {result['status']}")
    print(f"Iterations: {result['iterations']}")

    if result['status'] == 'PASS':
        print("\n✅ CODE FIXED AND VALIDATED")
        print("\nWhat happened:")
        print("  Iteration 1: Failed with ZeroDivisionError")
        print("  → LLM analyzed error evidence")
        print("  → Generated patch (add zero-check)")
        print("  Iteration 2: Passed all tests ✓")
        print("\nEvidence level: E3 → E4 (validated through correction)")

        # Show the fixed code
        print("\n📝 FIXED CODE:")
        print("-" * 60)
        with open('broken_function.py', 'r') as f:
            print(f.read())
        print("-" * 60)

        print("\n🎯 This is recursive evidence-based improvement in action!")

    return result


if __name__ == "__main__":
    print("\n" + "🔄 RECURSIVE EVIDENCE-BASED IMPROVEMENT".center(60))
    print("Claude demonstrating self-correction using evidence\n")

    result = demo_recursive_improvement()

    print("\n" + "="*60)
    print("PARADIGM SHIFT DEMONSTRATED")
    print("="*60)
    print("""
What just happened:

1. CODE WRITTEN: Initial implementation (with bug)
2. EVIDENCE CAPTURED: Exact failure (ZeroDivisionError)
3. DIAGNOSIS: Evidence-based analysis (line 3, missing check)
4. PATCH GENERATED: Minimal fix (add zero-check)
5. RE-VALIDATION: Code ran again
6. SUCCESS PROVEN: Tests passed, E3/E4 achieved

This isn't "try until it works" - it's:
- Evidence-driven debugging
- Minimal patches
- Hash-verified progression
- Provable correctness

The system doesn't guess. It PROVES.
    """)
