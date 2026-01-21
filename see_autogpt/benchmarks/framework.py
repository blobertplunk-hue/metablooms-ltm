"""
Benchmark Framework

Orchestrates benchmark runs across tasks and methods.
"""

import os
import sys
import json
import time
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from see_autogpt.benchmarks.tasks import get_all_tasks, BenchmarkTask
from see_autogpt.benchmarks.baselines import get_baseline
from see_autogpt.benchmarks.metrics import BenchmarkMetrics, ComparisonMetrics
from see_autogpt.agent_loop_recursive import SEERecursiveAgent


class BenchmarkRunner:
    """Runs benchmarks across tasks and methods."""

    def __init__(self, output_dir: str = "/tmp/see_benchmarks"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        self.tasks = get_all_tasks()
        self.results = {}

    def run_all_benchmarks(
        self,
        methods: List[str] = None,
        runs_per_task: int = 5,
        max_iterations: int = 10,
    ) -> Dict[str, Any]:
        """
        Run all benchmarks.

        Args:
            methods: List of method names to benchmark. If None, runs all.
            runs_per_task: Number of times to run each task (for statistical significance)
            max_iterations: Maximum iterations per run

        Returns:
            Dict with all results and comparisons
        """
        if methods is None:
            methods = ["simple_retry", "react", "reflexion", "see_mmd_ecl"]

        print("=" * 80)
        print("BENCHMARK SUITE")
        print("=" * 80)
        print(f"Tasks: {len(self.tasks)}")
        print(f"Methods: {', '.join(methods)}")
        print(f"Runs per task: {runs_per_task}")
        print(f"Max iterations: {max_iterations}")
        print("=" * 80)
        print()

        # Run benchmarks
        for method in methods:
            print(f"\n{'=' * 80}")
            print(f"Running: {method}")
            print(f"{'=' * 80}\n")

            self.results[method] = self._run_method_benchmark(
                method,
                runs_per_task,
                max_iterations
            )

        # Generate comparison
        comparison = self._generate_comparison()

        # Save results
        self._save_results(comparison)

        return comparison

    def _run_method_benchmark(
        self,
        method: str,
        runs_per_task: int,
        max_iterations: int
    ) -> List[Dict[str, Any]]:
        """Run benchmark for a specific method."""
        results = []

        for task in self.tasks:
            print(f"\n  Task: {task.task_id}")

            for run in range(runs_per_task):
                print(f"    Run {run + 1}/{runs_per_task}...", end=" ")

                # Reset task
                task.reset()

                # Run based on method
                if method == "see_mmd_ecl":
                    result = self._run_see_method(task, max_iterations)
                else:
                    result = self._run_baseline_method(task, method, max_iterations)

                result["task_id"] = task.task_id
                result["run"] = run + 1
                results.append(result)

                # Print result
                status = result.get("status", "UNKNOWN")
                iterations = result.get("iterations", 0)
                cost = result.get("total_cost_usd", result.get("total_cost", 0))
                print(f"{status} in {iterations} iterations (${cost:.3f})")

        return results

    def _run_see_method(self, task: BenchmarkTask, max_iterations: int) -> Dict[str, Any]:
        """Run SEE/MMD/ECL method."""
        evidence_root = os.path.join(self.output_dir, "see_evidence", task.task_id)
        os.makedirs(evidence_root, exist_ok=True)

        agent = SEERecursiveAgent(evidence_root)

        # Create intelligent command provider
        task_spec = task.get_task_spec()
        commands = task.get_available_commands()

        def command_provider(spec, iteration, learning_context):
            """Intelligent command provider for SEE agent."""
            # Start with simple approach
            if iteration == 1:
                # Try first command
                first_command = list(commands.keys())[0]
                return {
                    "name": first_command,
                    "callable": commands[first_command],
                    "arguments": self._infer_arguments(first_command, task),
                }

            # Learn from failures
            if learning_context.get("failure_evidence"):
                last_failure = learning_context["failure_evidence"][-1]
                unmet_criteria = last_failure.get("unmet_criteria", [])

                # Try different command based on unmet criteria
                for criterion in unmet_criteria:
                    # Map criterion to command
                    command_name = self._map_criterion_to_command(criterion, commands)
                    if command_name:
                        return {
                            "name": command_name,
                            "callable": commands[command_name],
                            "arguments": self._infer_arguments(command_name, task),
                        }

            # Default: try next command in sequence
            next_idx = (iteration - 1) % len(commands)
            command_name = list(commands.keys())[next_idx]
            return {
                "name": command_name,
                "callable": commands[command_name],
                "arguments": self._infer_arguments(command_name, task),
            }

        # Run task
        start_time = time.time()
        result = agent.run_task(
            task_spec,
            command_provider,
            max_iterations=max_iterations,
            cost_budget_usd=10.0
        )
        result["duration_seconds"] = time.time() - start_time

        return result

    def _run_baseline_method(
        self,
        task: BenchmarkTask,
        method: str,
        max_iterations: int
    ) -> Dict[str, Any]:
        """Run baseline method."""
        agent = get_baseline(method)
        task_spec = task.get_task_spec()
        commands = task.get_available_commands()

        start_time = time.time()
        result = agent.run_task(task_spec, commands, max_iterations)
        result["duration_seconds"] = time.time() - start_time

        return result

    def _infer_arguments(self, command_name: str, task: BenchmarkTask) -> Dict[str, Any]:
        """Infer arguments for a command based on task."""
        # Simple heuristics for common commands
        args = {}

        if "search" in command_name:
            args["query"] = "pizza"
            if "location" in command_name:
                args["location"] = "downtown"

        elif "select" in command_name or "verify" in command_name:
            args["restaurant_name"] = "Joe's Pizza"

        elif "email" in command_name:
            args["email"] = "test@example.com"

        elif "password" in command_name:
            if "confirm" in command_name:
                args["password_confirm"] = "Password123"
            else:
                args["password"] = "Password123"

        elif "api" in command_name:
            args["endpoint"] = "/users"
            if "auth" in command_name or "full" in command_name:
                args["api_key"] = "test_key"
            if "full" in command_name:
                args["user_id"] = "123"
                args["fields"] = ["name", "email"]

        return args

    def _map_criterion_to_command(self, criterion: str, commands: Dict) -> str:
        """Map unmet criterion to command that might satisfy it."""
        criterion_lower = criterion.lower()

        # Search-related
        if "search" in criterion_lower and "location" not in criterion_lower:
            if "search" in commands:
                return "search"

        if "location" in criterion_lower:
            if "search_with_location" in commands:
                return "search_with_location"

        if "rating" in criterion_lower or "select" in criterion_lower:
            if "select_restaurant" in commands:
                return "select_restaurant"

        if "delivery" in criterion_lower:
            if "verify_delivery" in commands:
                return "verify_delivery"

        # Form-related
        if "email" in criterion_lower:
            if "set_email" in commands:
                return "set_email"

        if "password" in criterion_lower:
            if "match" in criterion_lower:
                if "confirm_password" in commands:
                    return "confirm_password"
            elif "strong" in criterion_lower:
                if "set_password" in commands:
                    return "set_password"

        if "submit" in criterion_lower:
            if "submit_form" in commands:
                return "submit_form"

        # API-related
        if "auth" in criterion_lower:
            if "api_request_with_auth" in commands:
                return "api_request_with_auth"

        if "params" in criterion_lower or "complete" in criterion_lower:
            if "api_request_full" in commands:
                return "api_request_full"

        if "rate" in criterion_lower or "response" in criterion_lower:
            if "api_request_full" in commands:
                return "api_request_full"

        return None

    def _generate_comparison(self) -> Dict[str, Any]:
        """Generate comparison across all methods."""
        comparison = ComparisonMetrics()

        for method, results in self.results.items():
            comparison.add_method_results(method, results)

        report = comparison.generate_comparison_report()

        # Statistical significance
        significance = {}
        for metric in ["success_rate", "avg_iterations_success", "avg_cost_success"]:
            significance[metric] = comparison.get_statistical_significance(metric)

        return {
            "results": self.results,
            "comparison_report": report,
            "statistical_significance": significance,
            "method_metrics": comparison.method_metrics,
        }

    def _save_results(self, comparison: Dict[str, Any]):
        """Save results to disk."""
        # Save full results as JSON
        results_path = os.path.join(self.output_dir, "benchmark_results.json")
        with open(results_path, "w") as f:
            # Remove non-serializable parts
            serializable_results = {
                "method_metrics": comparison["method_metrics"],
                "statistical_significance": comparison["statistical_significance"],
            }
            json.dump(serializable_results, f, indent=2)

        # Save comparison report
        report_path = os.path.join(self.output_dir, "comparison_report.txt")
        with open(report_path, "w") as f:
            f.write(comparison["comparison_report"])

        print(f"\n{'=' * 80}")
        print(f"Results saved:")
        print(f"  JSON: {results_path}")
        print(f"  Report: {report_path}")
        print(f"{'=' * 80}\n")


def run_quick_benchmark():
    """Run a quick benchmark with minimal runs."""
    runner = BenchmarkRunner()

    print("Running QUICK benchmark (1 run per task)...\n")

    results = runner.run_all_benchmarks(
        methods=["simple_retry", "react", "reflexion", "see_mmd_ecl"],
        runs_per_task=1,
        max_iterations=10,
    )

    print("\n" + results["comparison_report"])

    return results


def run_full_benchmark():
    """Run full benchmark with multiple runs for statistical significance."""
    runner = BenchmarkRunner()

    print("Running FULL benchmark (5 runs per task)...\n")

    results = runner.run_all_benchmarks(
        methods=["simple_retry", "react", "reflexion", "see_mmd_ecl"],
        runs_per_task=5,
        max_iterations=10,
    )

    print("\n" + results["comparison_report"])

    # Print statistical significance
    print("\n" + "=" * 80)
    print("STATISTICAL SIGNIFICANCE")
    print("=" * 80 + "\n")

    for metric, sig in results["statistical_significance"].items():
        if "error" not in sig:
            print(f"{metric}:")
            print(f"  Best: {sig['best_method']} ({sig['best_value']:.3f})")
            print(f"  Worst: {sig['worst_method']} ({sig['worst_value']:.3f})")
            print(f"  Improvement: {sig['relative_improvement']:.1f}%")
            print()

    return results
