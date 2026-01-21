"""
Metrics Calculation for Benchmark Results

Calculates and compares:
- Success rate
- Average iterations to success
- Average cost per task
- Convergence rate (SEE-specific)
- Failure mode analysis
"""

from typing import Dict, Any, List
import statistics


class BenchmarkMetrics:
    """Calculates metrics from benchmark results."""

    def __init__(self):
        self.results = []

    def add_result(self, result: Dict[str, Any]):
        """Add a benchmark result."""
        self.results.append(result)

    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate aggregate metrics."""
        if not self.results:
            return {}

        successes = [r for r in self.results if r["status"] in ["SUCCESS", "GOAL_ACHIEVED"]]
        failures = [r for r in self.results if r["status"] not in ["SUCCESS", "GOAL_ACHIEVED"]]

        total = len(self.results)
        success_count = len(successes)
        failure_count = len(failures)

        metrics = {
            "total_runs": total,
            "successes": success_count,
            "failures": failure_count,
            "success_rate": success_count / total if total > 0 else 0,

            # Iterations
            "avg_iterations": statistics.mean([r["iterations"] for r in self.results]) if self.results else 0,
            "avg_iterations_success": statistics.mean([r["iterations"] for r in successes]) if successes else 0,
            "avg_iterations_failure": statistics.mean([r["iterations"] for r in failures]) if failures else 0,

            # Cost
            "total_cost": sum(r.get("total_cost_usd", r.get("total_cost", 0)) for r in self.results),
            "avg_cost": statistics.mean([r.get("total_cost_usd", r.get("total_cost", 0)) for r in self.results]) if self.results else 0,
            "avg_cost_success": statistics.mean([r.get("total_cost_usd", r.get("total_cost", 0)) for r in successes]) if successes else 0,

            # SEE-specific metrics
            "avg_final_progress": statistics.mean([r.get("final_progress", 0) for r in self.results]) if self.results else 0,
            "avg_convergence_rate": self._calculate_avg_convergence_rate(self.results),

            # Failure modes
            "failure_modes": self._analyze_failure_modes(failures),
        }

        return metrics

    def _calculate_avg_convergence_rate(self, results: List[Dict[str, Any]]) -> float:
        """Calculate average convergence rate for SEE results."""
        convergence_rates = []

        for result in results:
            if "learning_trajectory" in result:
                trajectory = result["learning_trajectory"]
                if len(trajectory) >= 2:
                    # Calculate average progress delta
                    deltas = []
                    for i in range(1, len(trajectory)):
                        prev_progress = trajectory[i-1].get("progress", 0)
                        curr_progress = trajectory[i].get("progress", 0)
                        deltas.append(curr_progress - prev_progress)

                    if deltas:
                        avg_delta = statistics.mean(deltas)
                        convergence_rates.append(avg_delta)

        return statistics.mean(convergence_rates) if convergence_rates else 0

    def _analyze_failure_modes(self, failures: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze types of failures."""
        modes = {}

        for failure in failures:
            status = failure.get("status", "UNKNOWN")
            modes[status] = modes.get(status, 0) + 1

        return modes

    def generate_report(self, method_name: str) -> str:
        """Generate human-readable report."""
        metrics = self.calculate_metrics()

        if not metrics:
            return f"No results for {method_name}"

        report = []
        report.append(f"=" * 70)
        report.append(f"BENCHMARK RESULTS: {method_name}")
        report.append(f"=" * 70)
        report.append("")

        report.append(f"Overall Performance:")
        report.append(f"  Total runs: {metrics['total_runs']}")
        report.append(f"  Successes: {metrics['successes']}")
        report.append(f"  Failures: {metrics['failures']}")
        report.append(f"  Success rate: {metrics['success_rate']:.1%}")
        report.append("")

        report.append(f"Efficiency:")
        report.append(f"  Avg iterations (all): {metrics['avg_iterations']:.1f}")
        report.append(f"  Avg iterations (success): {metrics['avg_iterations_success']:.1f}")
        report.append(f"  Avg cost (all): ${metrics['avg_cost']:.3f}")
        report.append(f"  Avg cost (success): ${metrics['avg_cost_success']:.3f}")
        report.append(f"  Total cost: ${metrics['total_cost']:.2f}")
        report.append("")

        if metrics.get("avg_convergence_rate"):
            report.append(f"Learning:")
            report.append(f"  Avg progress per iteration: {metrics['avg_convergence_rate']:+.1%}")
            report.append(f"  Avg final progress: {metrics['avg_final_progress']:.1%}")
            report.append("")

        if metrics["failure_modes"]:
            report.append(f"Failure Modes:")
            for mode, count in metrics["failure_modes"].items():
                report.append(f"  {mode}: {count}")
            report.append("")

        return "\n".join(report)


class ComparisonMetrics:
    """Compares multiple methods."""

    def __init__(self):
        self.method_metrics = {}

    def add_method_results(self, method_name: str, results: List[Dict[str, Any]]):
        """Add results for a method."""
        metrics_calc = BenchmarkMetrics()
        for result in results:
            metrics_calc.add_result(result)

        self.method_metrics[method_name] = metrics_calc.calculate_metrics()

    def generate_comparison_report(self) -> str:
        """Generate comparison report."""
        if not self.method_metrics:
            return "No methods to compare"

        report = []
        report.append("=" * 100)
        report.append("BENCHMARK COMPARISON REPORT")
        report.append("=" * 100)
        report.append("")

        # Table header
        methods = list(self.method_metrics.keys())
        report.append(f"{'Metric':<30} " + " ".join(f"{m:>20}" for m in methods))
        report.append("-" * 100)

        # Success rate
        report.append(f"{'Success Rate':<30} " + " ".join(
            f"{self.method_metrics[m]['success_rate']:>19.1%}" for m in methods
        ))

        # Avg iterations (success)
        report.append(f"{'Avg Iterations (Success)':<30} " + " ".join(
            f"{self.method_metrics[m]['avg_iterations_success']:>20.1f}" for m in methods
        ))

        # Avg cost (success)
        report.append(f"{'Avg Cost (Success)':<30} " + " ".join(
            f"${self.method_metrics[m]['avg_cost_success']:>19.3f}" for m in methods
        ))

        # Total cost
        report.append(f"{'Total Cost':<30} " + " ".join(
            f"${self.method_metrics[m]['total_cost']:>19.2f}" for m in methods
        ))

        # Convergence rate (if available)
        if any(self.method_metrics[m].get('avg_convergence_rate') for m in methods):
            report.append(f"{'Avg Progress/Iteration':<30} " + " ".join(
                f"{self.method_metrics[m].get('avg_convergence_rate', 0):>19.1%}" if self.method_metrics[m].get('avg_convergence_rate') else f"{'N/A':>20}"
                for m in methods
            ))

        report.append("")

        # Detailed breakdown by task
        report.append("=" * 100)
        report.append("DETAILED BREAKDOWN")
        report.append("=" * 100)
        report.append("")

        for method in methods:
            metrics = self.method_metrics[method]
            report.append(f"{method}:")
            report.append(f"  Success rate: {metrics['success_rate']:.1%}")
            report.append(f"  Avg iterations: {metrics['avg_iterations']:.1f}")
            report.append(f"  Avg cost: ${metrics['avg_cost']:.3f}")
            if metrics.get('avg_convergence_rate'):
                report.append(f"  Convergence rate: {metrics['avg_convergence_rate']:+.1%}/iteration")
            if metrics['failure_modes']:
                report.append(f"  Failure modes: {metrics['failure_modes']}")
            report.append("")

        # Winner analysis
        report.append("=" * 100)
        report.append("WINNER ANALYSIS")
        report.append("=" * 100)
        report.append("")

        best_success_rate = max(self.method_metrics[m]['success_rate'] for m in methods)
        best_avg_iterations = min(
            self.method_metrics[m]['avg_iterations_success']
            for m in methods
            if self.method_metrics[m]['avg_iterations_success'] > 0
        ) if any(self.method_metrics[m]['avg_iterations_success'] > 0 for m in methods) else 0

        best_avg_cost = min(
            self.method_metrics[m]['avg_cost_success']
            for m in methods
            if self.method_metrics[m]['avg_cost_success'] > 0
        ) if any(self.method_metrics[m]['avg_cost_success'] > 0 for m in methods) else 0

        for metric_name, best_value, maximize in [
            ("Success Rate", best_success_rate, True),
            ("Avg Iterations (Success)", best_avg_iterations, False),
            ("Avg Cost (Success)", best_avg_cost, False),
        ]:
            winners = []
            for m in methods:
                if metric_name == "Success Rate":
                    value = self.method_metrics[m]['success_rate']
                elif metric_name == "Avg Iterations (Success)":
                    value = self.method_metrics[m]['avg_iterations_success']
                else:
                    value = self.method_metrics[m]['avg_cost_success']

                if maximize:
                    if value == best_value:
                        winners.append(m)
                else:
                    if value == best_value and value > 0:
                        winners.append(m)

            report.append(f"Best {metric_name}: {', '.join(winners)}")

        report.append("")

        return "\n".join(report)

    def get_statistical_significance(self, metric: str = "success_rate") -> Dict[str, Any]:
        """
        Calculate statistical significance of differences.

        Note: This is a simplified version. For real statistical significance,
        would need raw trial data and proper hypothesis testing.
        """
        if len(self.method_metrics) < 2:
            return {"error": "Need at least 2 methods to compare"}

        methods = list(self.method_metrics.keys())

        # Get metric values
        values = {m: self.method_metrics[m].get(metric, 0) for m in methods}

        # Find best and worst
        best_method = max(methods, key=lambda m: values[m])
        worst_method = min(methods, key=lambda m: values[m])

        improvement = values[best_method] - values[worst_method]
        improvement_pct = (improvement / values[worst_method] * 100) if values[worst_method] > 0 else 0

        return {
            "metric": metric,
            "best_method": best_method,
            "best_value": values[best_method],
            "worst_method": worst_method,
            "worst_value": values[worst_method],
            "absolute_improvement": improvement,
            "relative_improvement": improvement_pct,
        }
