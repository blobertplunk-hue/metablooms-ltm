#!/usr/bin/env python3
"""
Test: CSRG Gate Simulation

Tests if CSRG (Common-Sense Reasoning Gate) would catch problematic actions.
Expected failure: No CSRG implementation.
"""

import sys


def simulate_csrg_check(intent, action, context):
    """
    Simulates CSRG evaluation.

    Since CSRG is not implemented, this always returns UNDETECTED.
    A real implementation would check the CSRG spec rules.
    """
    # Check Set 1: Would this ever make sense?
    # Check Set 2: Toolchain awareness
    # Check Set 3: Self-consistency
    # Check Set 4: Single-instance / Idempotency
    # Check Set 5: RCA coupling

    # Without implementation, we cannot detect
    return {"decision": "UNDETECTED", "reason": "No CSRG implementation"}


def main():
    print("=" * 70)
    print("TEST: CSRG Gate Simulation")
    print("=" * 70)

    # Test cases from real failures
    test_cases = [
        {
            "intent": "Make watcher work on Termux",
            "action": {
                "type": "command",
                "surface": "termux",
                "summary": "Use perl script",
                "dependencies": ["perl"],
            },
            "context": {
                "toolchain_facts": {"termux": {"has_perl": False}},
            },
            "should_block": True,
            "reason": "Toolchain assumption leakage (perl not verified)",
        },
        {
            "intent": "Test is_delta recognizer",
            "action": {
                "type": "file_write",
                "summary": "Create test payload",
            },
            "context": {
                "os_rules": ["is_delta gate requires specific format"],
            },
            "should_block": True,
            "reason": "Self-consistency (test contradicts gate)",
        },
        {
            "intent": "Fix boot path problem",
            "action": {
                "type": "tool_call",
                "summary": "Build validators without verifying boot",
            },
            "context": {
                "session_failures": [],
            },
            "should_block": True,
            "reason": "Would this make sense? (no boot verification first)",
        },
    ]

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test['intent']}")
        print(f"  Action: {test['action']['summary']}")
        print(f"  Should block: {test['should_block']} ({test['reason']})")

        result = simulate_csrg_check(
            test['intent'],
            test['action'],
            test['context']
        )

        if result['decision'] == "UNDETECTED":
            print(f"  ❌ UNDETECTED: {result['reason']}")
            failed += 1
        else:
            print(f"  ✅ DETECTED")
            passed += 1

    print("\n" + "=" * 70)
    print(f"Results: {passed}/{len(test_cases)} actions properly gated")

    if failed > 0:
        print("❌ FAIL: CSRG not implemented")
        print("\nIMPACT: Problematic actions not caught before execution")
        print("FIX: Implement csrg.py with Check Sets 1-5")
        return 1

    print("✅ PASS: CSRG catches all problematic actions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
