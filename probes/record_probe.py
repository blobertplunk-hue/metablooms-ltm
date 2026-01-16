#!/usr/bin/env python3
"""
Interactive probe result recorder
Run this after each probe execution to record observations
"""

import json
from pathlib import Path
from datetime import datetime

def record_probe_result():
    results_file = Path("./probes/results/probe_results.json")
    results_file.parent.mkdir(parents=True, exist_ok=True)

    # Load existing results
    if results_file.exists():
        with results_file.open() as f:
            results = json.load(f)
    else:
        results = []

    print("=" * 60)
    print("Claude Code Probe Result Recorder")
    print("=" * 60)

    probe_id = input("\nProbe ID (e.g., A1_context_window): ").strip()
    hypothesis = input("Hypothesis tested: ").strip()

    print("\nWhat happened? (enter empty line to finish)")
    observation_lines = []
    while True:
        line = input()
        if not line:
            break
        observation_lines.append(line)
    observation = "\n".join(observation_lines)

    interpretation = input("\nInterpretation: ").strip()

    print("\nEvidence strength?")
    print("  1. Weak (suggestive but inconclusive)")
    print("  2. Moderate (clear pattern but limited data)")
    print("  3. Strong (definitive, repeatable)")
    strength_map = {"1": "weak", "2": "moderate", "3": "strong"}
    strength = strength_map.get(input("Choice (1-3): ").strip(), "weak")

    result = {
        "probe_id": probe_id,
        "hypothesis": hypothesis,
        "observation": observation,
        "interpretation": interpretation,
        "evidence_strength": strength,
        "timestamp": datetime.now().isoformat()
    }

    results.append(result)

    with results_file.open("w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Recorded to {results_file}")
    print(f"Total probes recorded: {len(results)}")

if __name__ == "__main__":
    record_probe_result()
