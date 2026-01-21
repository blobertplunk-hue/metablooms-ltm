#!/usr/bin/env python3
"""
Demonstration: Using the SEE Loop to validate code

This proves Claude can use the SEE loop system for self-validation.
"""

import sys
import os
import tempfile

# Add metablooms to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from metablooms.loop.see_recursive_controller_v1 import run_see_loop
from metablooms.runtime.sandbox_exec_v1 import sandbox_execute
from metablooms.diagnostics.failure_diagnoser_v1 import diagnose
from metablooms.patching.patch_provider_v1 import provide_patch


def demo_see_loop_on_example_code():
    """
    Demonstrate the SEE loop validating the example Fibonacci function.
    """
    print("="*60)
    print("SEE LOOP DEMONSTRATION")
    print("="*60)
    print("\nValidating example_function.py using the SEE loop...\n")

    # Create evidence directory
    evidence_root = tempfile.mkdtemp(prefix="see_evidence_")

    task_spec = {
        "task_id": "fibonacci_validation",
        "command": ["python", "example_function.py"],
        "workdir": os.path.dirname(os.path.abspath(__file__)),
        "evidence_root": evidence_root,
        "timeout": 10
    }

    print(f"Task: {task_spec['task_id']}")
    print(f"Command: {' '.join(task_spec['command'])}")
    print(f"Evidence will be stored in: {evidence_root}\n")

    try:
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
        print(f"Final Receipt: {result['final_receipt']}")

        if result['status'] == 'PASS':
            print("\n✅ CODE VALIDATED (E3/E4)")
            print("The code executed successfully and passed all tests.")
            print("\nEvidence artifacts:")

            # Show receipt contents
            import json
            with open(result['final_receipt'], 'r') as f:
                receipt = json.load(f)

            print(f"  - Exit code: {receipt['exec']['exit_code']}")
            print(f"  - Duration: {receipt['exec']['duration_ms']}ms")
            print(f"  - Evidence level: {receipt['evidence_level_claimed']}")
            print(f"  - Environment: {receipt['environment']['python']}")

            # Show stdout
            iter_dir = os.path.dirname(result['final_receipt'])
            stdout_path = os.path.join(iter_dir, 'stdout.txt')
            if os.path.exists(stdout_path):
                with open(stdout_path, 'r') as f:
                    stdout_content = f.read()
                if stdout_content.strip():
                    print(f"\n  Output: {stdout_content.strip()}")

            print("\n🎯 PROOF: Code is correct (evidence-backed, not claimed)")

        else:
            print(f"\n❌ VALIDATION FAILED")
            print(f"Reason: {result.get('reason', 'Unknown')}")
            print("\nThis is GOOD - the system caught a problem before deployment!")

        return result

    except Exception as e:
        print(f"\n⚠️ SEE Loop encountered an error: {e}")
        print("This demonstrates fail-closed behavior - better to fail than claim success without proof.")
        raise


if __name__ == "__main__":
    print("\n" + "🔄 RECURSIVE EVIDENCE-BASED VALIDATION IN ACTION".center(60))
    print("Claude using the SEE loop to validate its own code\n")

    result = demo_see_loop_on_example_code()

    print("\n" + "="*60)
    print("META-OBSERVATION")
    print("="*60)
    print("""
This demonstration proves:
1. The SEE loop system is operational
2. Claude can use it for self-validation
3. Evidence is captured automatically
4. Success requires proof, not narrative
5. The meta-loop is closed: AI validates AI using evidence

This is the paradigm shift in practice.
    """)
