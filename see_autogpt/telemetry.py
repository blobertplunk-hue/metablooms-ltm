"""
Telemetry System for Recursive Correction

Captures EVERYTHING about the recursive correction process:
- Every hypothesis generated
- Every execution result
- Every validation check
- Every convergence measurement
- Every diagnosis
- Every learning update

This is what makes recursion trustworthy - complete observability.
"""

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional


class TelemetrySink:
    """
    Captures all telemetry from recursive correction loop.

    Provides complete observability into:
    - What the agent tried
    - Why it tried it
    - What happened
    - Whether it's converging
    - How to debug failures

    All telemetry is written to:
    - NDJSON log (machine-readable, append-only)
    - Structured in-memory logs (for reporting)
    """

    def __init__(self, output_dir: str):
        """
        Initialize telemetry sink.

        Args:
            output_dir: Directory to write telemetry files
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Structured telemetry streams
        self.recursion_log: List[Dict[str, Any]] = []
        self.iteration_log: List[Dict[str, Any]] = []
        self.hypothesis_log: List[Dict[str, Any]] = []
        self.execution_log: List[Dict[str, Any]] = []
        self.validation_log: List[Dict[str, Any]] = []
        self.regression_log: List[Dict[str, Any]] = []
        self.convergence_log: List[Dict[str, Any]] = []
        self.diagnosis_log: List[Dict[str, Any]] = []
        self.learning_log: List[Dict[str, Any]] = []

        # Aggregate metrics
        self.metrics = {
            "total_recursions": 0,
            "successful_recursions": 0,
            "aborted_recursions": 0,
            "iteration_limit_recursions": 0,
            "no_correction_available": 0,
            "total_iterations": 0,
            "total_cost_usd": 0.0,
            "average_iterations_to_success": 0.0,
            "convergence_rate": 0.0,
        }

    def start_recursion(
        self, task_id: str, goal: str, max_iterations: int, timestamp: str
    ) -> str:
        """
        Start tracking a new recursion.

        Returns:
            recursion_id: Unique identifier for this recursion
        """
        recursion_id = f"recursion_{task_id}_{int(time.time() * 1000)}"

        entry = {
            "recursion_id": recursion_id,
            "task_id": task_id,
            "goal": goal,
            "max_iterations": max_iterations,
            "start_timestamp": timestamp,
            "status": "in_progress",
        }

        self.recursion_log.append(entry)
        self.metrics["total_recursions"] += 1

        self._write_event("recursion_start", entry)

        return recursion_id

    def start_iteration(
        self, recursion_id: str, iteration: int, learning_context_size: int
    ):
        """Start tracking an iteration."""
        entry = {
            "recursion_id": recursion_id,
            "iteration": iteration,
            "start_timestamp": datetime.utcnow().isoformat() + "Z",
            "learning_context_size": learning_context_size,
            "status": "in_progress",
        }

        self.iteration_log.append(entry)
        self.metrics["total_iterations"] += 1

        self._write_event("iteration_start", entry)

    def log_hypothesis(
        self,
        recursion_id: str,
        iteration: int,
        hypothesis: Dict[str, Any],
        duration_ms: int,
        is_refined: bool,
    ):
        """Log hypothesis generation."""
        entry = {
            "recursion_id": recursion_id,
            "iteration": iteration,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "hypothesis": hypothesis,
            "duration_ms": duration_ms,
            "is_refined": is_refined,
        }

        self.hypothesis_log.append(entry)
        self._write_event("hypothesis", entry)

    def log_execution(
        self, recursion_id: str, iteration: int, execution: Dict[str, Any]
    ):
        """Log execution results."""
        entry = {
            "recursion_id": recursion_id,
            "iteration": iteration,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **execution,
        }

        self.execution_log.append(entry)
        self.metrics["total_cost_usd"] += execution.get("cost_usd", 0.0)
        self._write_event("execution", entry)

    def log_validation(
        self, recursion_id: str, iteration: int, validation: Dict[str, Any]
    ):
        """Log goal validation."""
        entry = {
            "recursion_id": recursion_id,
            "iteration": iteration,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **validation,
        }

        self.validation_log.append(entry)
        self._write_event("validation", entry)

    def log_regression_check(
        self, recursion_id: str, iteration: int, regression: Dict[str, Any]
    ):
        """Log regression detection."""
        entry = {
            "recursion_id": recursion_id,
            "iteration": iteration,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **regression,
        }

        self.regression_log.append(entry)
        self._write_event("regression", entry)

    def log_convergence(
        self, recursion_id: str, iteration: int, metrics: Dict[str, Any]
    ):
        """
        Log convergence metrics.

        THIS IS CRITICAL - shows whether recursion is working.
        """
        entry = {
            "recursion_id": recursion_id,
            "iteration": iteration,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **metrics,
        }

        self.convergence_log.append(entry)
        self._write_event("convergence", entry)

        # Update aggregate convergence rate
        if metrics.get("is_converging") and metrics.get("progress_rate"):
            total_iters = self.metrics["total_iterations"]
            current_rate = self.metrics["convergence_rate"]
            new_rate = metrics["progress_rate"]
            self.metrics["convergence_rate"] = (
                (current_rate * (total_iters - 1) + new_rate) / total_iters
            )

    def log_diagnosis(
        self, recursion_id: str, iteration: int, diagnosis: Dict[str, Any]
    ):
        """Log failure diagnosis."""
        entry = {
            "recursion_id": recursion_id,
            "iteration": iteration,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **diagnosis,
        }

        self.diagnosis_log.append(entry)
        self._write_event("diagnosis", entry)

    def log_learning_update(
        self, recursion_id: str, iteration: int, learning: Dict[str, Any]
    ):
        """Log learning/memory update."""
        entry = {
            "recursion_id": recursion_id,
            "iteration": iteration,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **learning,
        }

        self.learning_log.append(entry)
        self._write_event("learning", entry)

    def end_iteration(
        self, recursion_id: str, iteration: int, duration_ms: int, will_retry: bool
    ):
        """End tracking an iteration."""
        # Update iteration log
        for entry in reversed(self.iteration_log):
            if (
                entry["recursion_id"] == recursion_id
                and entry["iteration"] == iteration
                and entry["status"] == "in_progress"
            ):
                entry["end_timestamp"] = datetime.utcnow().isoformat() + "Z"
                entry["duration_ms"] = duration_ms
                entry["will_retry"] = will_retry
                entry["status"] = "completed"
                break

        self._write_event(
            "iteration_end",
            {
                "recursion_id": recursion_id,
                "iteration": iteration,
                "duration_ms": duration_ms,
                "will_retry": will_retry,
            },
        )

    def end_recursion(
        self,
        recursion_id: str,
        status: str,
        final_iteration: int,
        total_duration_ms: Optional[int] = None,
        evidence_level: Optional[str] = None,
        total_cost_usd: Optional[float] = None,
        final_progress: Optional[float] = None,
        abort_reason: Optional[str] = None,
        learning_trajectory: Optional[List[Dict[str, Any]]] = None,
    ):
        """End tracking a recursion."""
        # Update recursion log
        for entry in reversed(self.recursion_log):
            if (
                entry["recursion_id"] == recursion_id
                and entry["status"] == "in_progress"
            ):
                entry["end_timestamp"] = datetime.utcnow().isoformat() + "Z"
                entry["status"] = status
                entry["final_iteration"] = final_iteration
                if total_duration_ms:
                    entry["total_duration_ms"] = total_duration_ms
                if evidence_level:
                    entry["evidence_level"] = evidence_level
                if total_cost_usd:
                    entry["total_cost_usd"] = total_cost_usd
                if final_progress is not None:
                    entry["final_progress"] = final_progress
                if abort_reason:
                    entry["abort_reason"] = abort_reason
                if learning_trajectory:
                    entry["learning_trajectory_count"] = len(learning_trajectory)
                break

        # Update metrics
        if status == "GOAL_ACHIEVED":
            self.metrics["successful_recursions"] += 1
            successful = self.metrics["successful_recursions"]
            avg = self.metrics["average_iterations_to_success"]
            self.metrics["average_iterations_to_success"] = (
                (avg * (successful - 1) + final_iteration) / successful
            )
        elif status == "REGRESSION_ABORT":
            self.metrics["aborted_recursions"] += 1
        elif status == "ITERATION_LIMIT":
            self.metrics["iteration_limit_recursions"] += 1
        elif status in ["NO_PATCH_AVAILABLE", "NO_CORRECTION_AVAILABLE"]:
            self.metrics["no_correction_available"] += 1

        self._write_event(
            "recursion_end",
            {
                "recursion_id": recursion_id,
                "status": status,
                "final_iteration": final_iteration,
                "evidence_level": evidence_level,
                "total_cost_usd": total_cost_usd,
                "final_progress": final_progress,
            },
        )

    def _write_event(self, event_type: str, data: Dict[str, Any]):
        """Write telemetry event to NDJSON log."""
        log_path = os.path.join(self.output_dir, "telemetry.ndjson")

        event = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": data,
        }

        with open(log_path, "a") as f:
            f.write(json.dumps(event) + "\n")

    def get_recursion_telemetry(self, recursion_id: str) -> Dict[str, Any]:
        """Get all telemetry for a specific recursion."""
        return {
            "recursion": next(
                (r for r in self.recursion_log if r["recursion_id"] == recursion_id),
                None,
            ),
            "iterations": [
                i for i in self.iteration_log if i["recursion_id"] == recursion_id
            ],
            "hypotheses": [
                h for h in self.hypothesis_log if h["recursion_id"] == recursion_id
            ],
            "executions": [
                e for e in self.execution_log if e["recursion_id"] == recursion_id
            ],
            "validations": [
                v for v in self.validation_log if v["recursion_id"] == recursion_id
            ],
            "regressions": [
                r for r in self.regression_log if r["recursion_id"] == recursion_id
            ],
            "convergences": [
                c for c in self.convergence_log if c["recursion_id"] == recursion_id
            ],
            "diagnoses": [
                d for d in self.diagnosis_log if d["recursion_id"] == recursion_id
            ],
            "learning": [
                l for l in self.learning_log if l["recursion_id"] == recursion_id
            ],
        }

    def generate_report(self, recursion_id: Optional[str] = None) -> str:
        """
        Generate human-readable telemetry report.

        Args:
            recursion_id: If provided, report for specific recursion.
                         Otherwise, aggregate report.
        """
        if recursion_id:
            return self._generate_recursion_report(recursion_id)
        else:
            return self._generate_aggregate_report()

    def _generate_recursion_report(self, recursion_id: str) -> str:
        """Generate report for specific recursion."""
        telemetry = self.get_recursion_telemetry(recursion_id)

        recursion = telemetry["recursion"]
        if not recursion:
            return f"No telemetry found for recursion: {recursion_id}"

        iterations = telemetry["iterations"]
        hypotheses = telemetry["hypotheses"]
        executions = telemetry["executions"]
        validations = telemetry["validations"]
        convergences = telemetry["convergences"]
        diagnoses = telemetry["diagnoses"]

        report = f"""
{'='*80}
RECURSIVE CORRECTION TELEMETRY REPORT
{'='*80}

Recursion ID: {recursion_id}
Task: {recursion['task_id']}
Goal: {recursion['goal']}
Status: {recursion['status']}
Iterations: {recursion.get('final_iteration', 0)} / {recursion['max_iterations']}

OUTCOME:
  Evidence Level: {recursion.get('evidence_level', 'N/A')}
  Total Cost: ${recursion.get('total_cost_usd', 0):.2f}
  Total Duration: {recursion.get('total_duration_ms', 0)/1000:.2f}s
  Final Progress: {recursion.get('final_progress', 0):.1%}

{'='*80}
ITERATION BREAKDOWN
{'='*80}
"""

        for i in range(len(iterations)):
            iteration = iterations[i]
            hypothesis = hypotheses[i] if i < len(hypotheses) else {}
            execution = executions[i] if i < len(executions) else {}
            validation = validations[i] if i < len(validations) else {}
            convergence = convergences[i] if i < len(convergences) else {}
            diagnosis = diagnoses[i] if i < len(diagnoses) else {}

            iter_num = iteration["iteration"]

            report += f"""
Iteration {iter_num}:
  Hypothesis:
    - Command: {hypothesis.get('hypothesis', {}).get('command', 'N/A')}
    - Refined: {hypothesis.get('is_refined', False)}
    - Generation time: {hypothesis.get('duration_ms', 0)}ms

  Execution:
    - Success: {execution.get('success', False)}
    - Evidence: {execution.get('evidence_level', 'N/A')}
    - Cost: ${execution.get('cost_usd', 0):.4f}
    - Duration: {execution.get('duration_ms', 0)}ms

  Validation:
    - Goal achieved: {validation.get('goal_achieved', False)}
    - Confidence: {validation.get('confidence', 0):.1%}
    - Criteria met: {sum(validation.get('criteria_met', {}).values())}/{len(validation.get('criteria_met', {}))}

  Convergence:
    - Progress delta: {f"{convergence.get('progress_delta'):+.1%}" if convergence.get('progress_delta') is not None else 'N/A'}
    - Trend: {convergence.get('confidence_trend', 'N/A')}
    - Converging: {convergence.get('is_converging', 'N/A')}

  Diagnosis:
    - Type: {diagnosis.get('failure_type', 'N/A')}
    - Root cause: {diagnosis.get('root_cause', 'N/A')[:60]}...
"""

        report += f"""
{'='*80}
CONVERGENCE ANALYSIS
{'='*80}
"""

        if convergences:
            progress_deltas = [c.get("progress_delta", 0) for c in convergences if c.get("progress_delta") is not None]
            avg_progress = sum(progress_deltas) / len(progress_deltas) if progress_deltas else 0

            report += f"""
Average progress per iteration: {avg_progress:+.1%}
Final trend: {convergences[-1].get('confidence_trend', 'N/A')}
Final convergence status: {convergences[-1].get('is_converging', 'N/A')}
"""

        return report

    def _generate_aggregate_report(self) -> str:
        """Generate aggregate report across all recursions."""
        total = self.metrics["total_recursions"]
        success_rate = (
            (self.metrics["successful_recursions"] / total * 100) if total > 0 else 0
        )

        report = f"""
{'='*80}
AGGREGATE TELEMETRY REPORT
{'='*80}

OVERALL METRICS:
  Total recursions: {total}
  Successful: {self.metrics['successful_recursions']} ({success_rate:.1f}%)
  Aborted (regression): {self.metrics['aborted_recursions']}
  Iteration limit: {self.metrics['iteration_limit_recursions']}
  No correction available: {self.metrics['no_correction_available']}

  Total iterations: {self.metrics['total_iterations']}
  Avg iterations to success: {self.metrics['average_iterations_to_success']:.1f}

  Total cost: ${self.metrics['total_cost_usd']:.2f}
  Avg cost per recursion: ${self.metrics['total_cost_usd']/max(total,1):.2f}

  Average convergence rate: {self.metrics['convergence_rate']:.1%} per iteration

RECURSION HISTORY:
"""

        for recursion in self.recursion_log:
            report += f"""
  {recursion['recursion_id']}:
    Status: {recursion['status']}
    Iterations: {recursion.get('final_iteration', '?')}
    Progress: {recursion.get('final_progress', 0):.1%}
    Cost: ${recursion.get('total_cost_usd', 0):.2f}
"""

        return report
