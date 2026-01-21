#!/usr/bin/env python3
"""
SEE/MMD/ECL Benchmark Runner

Compares SEE/MMD/ECL recursive correction against other methods:
- Simple Retry Loop
- ReAct (Reasoning + Acting)
- Reflexion (Self-reflection)

Measures:
- Success rate
- Iterations to success
- Cost per task
- Convergence rate
- Failure modes
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from see_autogpt.benchmarks.framework import run_quick_benchmark, run_full_benchmark


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run SEE/MMD/ECL benchmarks")
    parser.add_argument(
        "--mode",
        choices=["quick", "full"],
        default="quick",
        help="Benchmark mode: quick (1 run/task) or full (5 runs/task)"
    )

    args = parser.parse_args()

    print()
    print("=" * 80)
    print("SEE/MMD/ECL BENCHMARK SUITE")
    print("=" * 80)
    print()
    print("This benchmark compares SEE/MMD/ECL recursive correction against:")
    print("  - Simple Retry: Naive retry loop with no learning")
    print("  - ReAct: Reasoning + Acting (no evidence validation)")
    print("  - Reflexion: Self-reflection on failures (text-based)")
    print()
    print("Metrics measured:")
    print("  - Success rate")
    print("  - Average iterations to success")
    print("  - Average cost per task")
    print("  - Convergence rate (SEE-specific)")
    print("  - Failure mode analysis")
    print()
    print("=" * 80)
    print()

    if args.mode == "quick":
        print("Running QUICK benchmark (1 run per task)...")
        print("This is fast but may not be statistically significant.")
        print()
        results = run_quick_benchmark()
    else:
        print("Running FULL benchmark (5 runs per task)...")
        print("This takes longer but provides statistical significance.")
        print()
        results = run_full_benchmark()

    print()
    print("=" * 80)
    print("BENCHMARK COMPLETE")
    print("=" * 80)
    print()
    print("Key findings:")
    print()

    # Extract key findings
    method_metrics = results["method_metrics"]

    # Find best success rate
    best_success = max(
        method_metrics.items(),
        key=lambda x: x[1]["success_rate"]
    )
    print(f"✅ Best Success Rate: {best_success[0]} ({best_success[1]['success_rate']:.1%})")

    # Find most efficient (lowest iterations on success)
    efficient = min(
        method_metrics.items(),
        key=lambda x: x[1]["avg_iterations_success"] if x[1]["avg_iterations_success"] > 0 else float('inf')
    )
    print(f"⚡ Most Efficient: {efficient[0]} ({efficient[1]['avg_iterations_success']:.1f} iterations)")

    # Find cheapest
    cheapest = min(
        method_metrics.items(),
        key=lambda x: x[1]["avg_cost_success"] if x[1]["avg_cost_success"] > 0 else float('inf')
    )
    print(f"💰 Lowest Cost: {cheapest[0]} (${cheapest[1]['avg_cost_success']:.3f} per success)")

    # SEE-specific: convergence rate
    see_metrics = method_metrics.get("see_mmd_ecl", {})
    if see_metrics.get("avg_convergence_rate"):
        print(f"📈 SEE Convergence: {see_metrics['avg_convergence_rate']:+.1%} progress per iteration")

    print()
    print("=" * 80)
    print()

    # Print statistical significance if available
    if "statistical_significance" in results:
        print("Statistical Significance:")
        print()

        sig = results["statistical_significance"].get("success_rate", {})
        if "error" not in sig:
            improvement = sig.get("relative_improvement", 0)
            print(f"  Success Rate Improvement: {improvement:.1f}%")
            print(f"    ({sig['best_method']} vs {sig['worst_method']})")
            print()

    print("Full results saved to: /tmp/see_benchmarks/")
    print("  - benchmark_results.json")
    print("  - comparison_report.txt")
    print()


if __name__ == "__main__":
    main()
