"""
SEE-Powered Autonomous Agent with Full Recursive Correction

The complete implementation with:
- Full telemetry (every decision measured)
- True recursive correction (learning from failures)
- Convergence tracking (shows if we're making progress)
- Evidence-based termination (E3/E4 required)

This is what makes the recursion special - complete observability
and actual learning across iterations.
"""

import json
import os
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .command_executor import SEECommandExecutor, default_cost_tracker
from .goal_validator import GoalValidator
from .patch_provider import AgentPatchProvider
from .regression_tracker import AgentRegressionTracker
from .telemetry import TelemetrySink


class SEERecursiveAgent:
    """
    Evidence-based autonomous agent with full recursive correction and telemetry.

    The key difference from AutoGPT:
    - AutoGPT: Try → Fail → Try same thing → Fail → Repeat
    - SEE Agent: Try → Fail → Learn WHY → Correct → Try better → Success

    The recursion is:
    1. Hypothesis (what to try)
    2. Execute (with evidence)
    3. Validate (did it work?)
    4. If failed → SEE (gather failure evidence)
    5. Diagnose (why did it fail?)
    6. Learn (store evidence for next try)
    7. Recurse (with better hypothesis)

    Every step measured with telemetry.
    """

    def __init__(
        self,
        evidence_root: str,
        llm_provider: Optional[Any] = None,
        cost_tracker: Optional[Callable] = None,
    ):
        """
        Initialize SEE recursive agent.

        Args:
            evidence_root: Directory for evidence storage
            llm_provider: Optional LLM for intelligent patching
            cost_tracker: Optional cost tracking function
        """
        self.evidence_root = evidence_root
        self.llm_provider = llm_provider
        self.cost_tracker = cost_tracker or default_cost_tracker

        # Core components
        self.executor = SEECommandExecutor(evidence_root)
        self.goal_validator = GoalValidator()
        self.patch_provider = AgentPatchProvider(llm_provider)

        # Telemetry sink
        telemetry_dir = os.path.join(evidence_root, "telemetry")
        self.telemetry = TelemetrySink(telemetry_dir)

    def run_task(
        self,
        task_spec: Dict[str, Any],
        command_provider: Callable[[Dict[str, Any], int, Dict[str, Any]], Dict[str, Any]],
        max_iterations: int = 5,
        cost_budget_usd: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute task using full recursive correction loop.

        Args:
            task_spec: Task specification with goal and success criteria
            command_provider: Function that generates commands
                             (task_spec, iteration, learning_context) -> command
            max_iterations: Maximum iterations before termination
            cost_budget_usd: Optional cost budget

        Returns:
            Result with status, telemetry, and complete audit trail
        """
        task_id = task_spec.get("task_id", f"task_{int(time.time())}")
        task_spec["task_id"] = task_id

        # Telemetry: Start recursion
        recursion_start = time.time()
        recursion_id = self.telemetry.start_recursion(
            task_id=task_id,
            goal=task_spec.get("goal", ""),
            max_iterations=max_iterations,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

        # Learning context (persists across iterations)
        learning_context = {
            "failed_approaches": [],
            "failure_evidence": [],
            "hypothesis_evolution": [],
            "convergence_metrics": [],
            "receipts": [],
            "next_action": None,  # Corrective action from diagnosis
        }

        # Regression tracker
        tracker = AgentRegressionTracker(task_id)

        print(f"🚀 Starting Recursive SEE Agent for: {task_id}")
        print(f"   Goal: {task_spec.get('goal', 'unspecified')}")
        print(f"   Max iterations: {max_iterations}")
        if cost_budget_usd:
            print(f"   Budget: ${cost_budget_usd:.2f}")
        print(f"   Recursion ID: {recursion_id}")
        print()

        # ========================================
        # MAIN RECURSIVE CORRECTION LOOP
        # ========================================

        for iteration in range(1, max_iterations + 1):
            iter_start = time.time()

            # Telemetry: Start iteration
            self.telemetry.start_iteration(
                recursion_id=recursion_id,
                iteration=iteration,
                learning_context_size=len(learning_context["failure_evidence"]),
            )

            print(f"━━━ Iteration {iteration}/{max_iterations} ━━━")

            # ========================================
            # Step 1: HYPOTHESIS GENERATION
            # ========================================
            hypothesis_start = time.time()
            print("  📋 Proposing action...")

            try:
                # Command provider receives learning context
                # This is THE KEY: next iteration knows about previous failures
                command_spec = command_provider(task_spec, iteration, learning_context)

                command_name = command_spec["name"]
                command_callable = command_spec["callable"]
                command_arguments = command_spec["arguments"]

                if iteration == 1:
                    rationale = "Initial attempt"
                else:
                    rationale = learning_context.get("next_action", {}).get(
                        "rationale", "Retry with different approach"
                    )

                print(f"     → Command: {command_name}")
                print(f"     → Rationale: {rationale}")
                if iteration > 1:
                    print(f"     → Informed by {len(learning_context['failure_evidence'])} previous failure(s)")

            except Exception as e:
                print(f"  ❌ Command proposal failed: {e}")
                return self._end_recursion(
                    recursion_id,
                    "PROPOSAL_ERROR",
                    iteration - 1,
                    learning_context,
                    {},
                    recursion_start,
                    error=f"Command proposal failed: {e}",
                )

            hypothesis_duration = int((time.time() - hypothesis_start) * 1000)

            # Telemetry: Hypothesis
            self.telemetry.log_hypothesis(
                recursion_id=recursion_id,
                iteration=iteration,
                hypothesis={
                    "command": command_name,
                    "arguments": command_arguments,
                    "rationale": rationale,
                },
                duration_ms=hypothesis_duration,
                is_refined=iteration > 1,
            )

            # ========================================
            # Step 2: EXECUTION (with evidence capture)
            # ========================================
            print("  ⚙️  Executing command...")

            exec_result = self.executor.execute_with_evidence(
                command_name,
                command_callable,
                command_arguments,
                task_spec,
                iteration,
                llm_cost_tracker=self.cost_tracker,
            )

            print(f"     → {exec_result['result_summary']}")
            print(
                f"     → Cost: ${exec_result['cost_usd']:.4f} "
                f"(cumulative: ${exec_result['cumulative_cost_usd']:.2f})"
            )
            print(f"     → Evidence: {exec_result['evidence_level']}")

            # Telemetry: Execution
            self.telemetry.log_execution(
                recursion_id=recursion_id,
                iteration=iteration,
                execution={
                    "success": exec_result["success"],
                    "evidence_level": exec_result["evidence_level"],
                    "cost_usd": exec_result["cost_usd"],
                    "cumulative_cost_usd": exec_result["cumulative_cost_usd"],
                    "duration_ms": exec_result["duration_ms"],
                    "receipt_path": exec_result["receipt_path"],
                },
            )

            # Load receipt
            with open(exec_result["receipt_path"], "r") as f:
                receipt = json.load(f)
            learning_context["receipts"].append(receipt)

            # ========================================
            # Step 3: GOAL VALIDATION (testing)
            # ========================================
            validation_start = time.time()
            print("  🎯 Validating goal...")

            goal_validation = self.goal_validator.validate_goal(
                task_spec, learning_context["receipts"], receipt
            )

            print(f"     → {goal_validation['rationale']}")
            print(f"     → Confidence: {goal_validation['confidence']:.1%}")

            validation_duration = int((time.time() - validation_start) * 1000)

            # Telemetry: Validation
            self.telemetry.log_validation(
                recursion_id=recursion_id,
                iteration=iteration,
                validation={
                    "goal_achieved": goal_validation["goal_achieved"],
                    "criteria_met": goal_validation["criteria_met"],
                    "confidence": goal_validation["confidence"],
                    "evidence_level": goal_validation["evidence_level"],
                    "duration_ms": validation_duration,
                },
            )

            # ========================================
            # Step 4: REGRESSION DETECTION
            # ========================================
            regression_start = time.time()
            print("  🔍 Checking for regression...")

            tracker.observe(iteration, receipt, goal_validation)
            regression_check = tracker.detect_regression()

            if regression_check["is_regression"]:
                print(f"     ⚠️  {regression_check['evidence']}")
            else:
                print(f"     ✅ {regression_check['evidence']}")

            regression_duration = int((time.time() - regression_start) * 1000)

            # Telemetry: Regression
            self.telemetry.log_regression_check(
                recursion_id=recursion_id,
                iteration=iteration,
                regression={
                    "is_regression": regression_check["is_regression"],
                    "regression_type": regression_check.get("regression_type"),
                    "severity": regression_check.get("severity"),
                    "recommendation": regression_check["recommendation"],
                    "duration_ms": regression_duration,
                },
            )

            # ========================================
            # Step 5: CONVERGENCE METRICS (KEY!)
            # ========================================
            convergence = self._calculate_convergence(
                iteration, goal_validation, learning_context
            )

            print(f"  📊 Convergence: {convergence['confidence_trend']}")
            if convergence["progress_delta"] is not None:
                print(f"     → Progress delta: {convergence['progress_delta']:+.1%}")
            if convergence["estimated_remaining"]:
                print(f"     → Est. iterations remaining: {convergence['estimated_remaining']}")

            # Telemetry: Convergence
            self.telemetry.log_convergence(
                recursion_id=recursion_id,
                iteration=iteration,
                metrics=convergence,
            )

            learning_context["convergence_metrics"].append(convergence)

            # ========================================
            # Step 6: CHECK BUDGET
            # ========================================
            if cost_budget_usd:
                print("  💰 Checking budget...")
                if not self.executor.check_budget(cost_budget_usd):
                    print(
                        f"     ❌ Budget exceeded: "
                        f"${exec_result['cumulative_cost_usd']:.2f} > ${cost_budget_usd:.2f}"
                    )
                    return self._end_recursion(
                        recursion_id,
                        "BUDGET_EXCEEDED",
                        iteration,
                        learning_context,
                        goal_validation,
                        recursion_start,
                        error=f"Budget exceeded at iteration {iteration}",
                    )
                else:
                    print(
                        f"     ✅ Within budget: "
                        f"${exec_result['cumulative_cost_usd']:.2f} / ${cost_budget_usd:.2f}"
                    )

            # ========================================
            # SUCCESS PATH
            # ========================================
            if goal_validation["goal_achieved"]:
                print()
                print("🎉 GOAL ACHIEVED!")
                print(f"   Evidence level: {goal_validation['evidence_level']}")
                print(f"   Iterations: {iteration}")
                print(f"   Cost: ${exec_result['cumulative_cost_usd']:.2f}")
                print()

                return self._end_recursion(
                    recursion_id,
                    "GOAL_ACHIEVED",
                    iteration,
                    learning_context,
                    goal_validation,
                    recursion_start,
                )

            # ========================================
            # ABORT PATH (regression detected)
            # ========================================
            if regression_check["recommendation"] == "abort":
                print()
                print("🛑 ABORTING: Regression detected")
                print(f"   Type: {regression_check.get('regression_type')}")
                print(f"   Evidence: {regression_check['evidence']}")
                print()

                return self._end_recursion(
                    recursion_id,
                    "REGRESSION_ABORT",
                    iteration,
                    learning_context,
                    goal_validation,
                    recursion_start,
                    error=regression_check["evidence"],
                )

            # ========================================
            # Step 7: FAILURE DIAGNOSIS (SEE for correction)
            # ========================================
            if iteration < max_iterations:
                diagnosis_start = time.time()
                print("  🔧 Diagnosing failure...")

                # Generate detailed failure evidence
                failure_evidence = {
                    "iteration": iteration,
                    "command": command_spec,
                    "execution_result": exec_result,
                    "goal_validation": goal_validation,
                    "regression_check": regression_check,
                    "unmet_criteria": [
                        k
                        for k, v in goal_validation["criteria_met"].items()
                        if not v
                    ],
                    "convergence": convergence,
                }

                # Diagnose using evidence
                diagnosis = self.patch_provider.diagnose_and_patch(
                    receipt, goal_validation, task_spec, regression_check
                )

                diagnosis_duration = int((time.time() - diagnosis_start) * 1000)

                # Telemetry: Diagnosis
                self.telemetry.log_diagnosis(
                    recursion_id=recursion_id,
                    iteration=iteration,
                    diagnosis={
                        "failure_type": diagnosis.get("patch_type")
                        if diagnosis
                        else "no_correction_available",
                        "root_cause": diagnosis.get("diagnosis")
                        if diagnosis
                        else "Unable to diagnose",
                        "confidence": diagnosis.get("confidence") if diagnosis else 0.0,
                        "corrective_action": diagnosis.get("corrective_action")
                        if diagnosis
                        else None,
                        "duration_ms": diagnosis_duration,
                    },
                )

                if not diagnosis:
                    print("     → No corrective action possible")
                    return self._end_recursion(
                        recursion_id,
                        "NO_CORRECTION_AVAILABLE",
                        iteration,
                        learning_context,
                        goal_validation,
                        recursion_start,
                        error="No corrective patch available",
                    )

                print(f"     → Diagnosis: {diagnosis['diagnosis']}")
                print(
                    f"     → Confidence: {diagnosis.get('confidence', 0.0):.1%}"
                )
                print(
                    f"     → Next action: {diagnosis['corrective_action'].get('rationale', 'Retry')}"
                )

                # ========================================
                # Step 8: LEARNING (accumulate evidence)
                # ========================================
                learning_update = {
                    "iteration": iteration,
                    "hypothesis": command_spec,
                    "execution": exec_result,
                    "validation": goal_validation,
                    "diagnosis": diagnosis,
                    "progress": goal_validation["confidence"],
                    "evidence_quality": goal_validation["evidence_level"],
                }

                learning_context["failed_approaches"].append(command_spec)
                learning_context["failure_evidence"].append(failure_evidence)
                learning_context["hypothesis_evolution"].append(learning_update)

                # THIS IS THE KEY: Store corrective action for next iteration
                learning_context["next_action"] = diagnosis["corrective_action"]

                # Telemetry: Learning update
                self.telemetry.log_learning_update(
                    recursion_id=recursion_id,
                    iteration=iteration,
                    learning={
                        "total_attempts": len(learning_context["failed_approaches"]),
                        "evidence_accumulated": len(
                            learning_context["failure_evidence"]
                        ),
                        "hypothesis_refinements": len(
                            learning_context["hypothesis_evolution"]
                        ),
                        "next_action": learning_context["next_action"],
                    },
                )

                print(
                    f"  📚 Learning: {len(learning_context['failure_evidence'])} failure(s) stored"
                )

            # End iteration
            iter_duration = int((time.time() - iter_start) * 1000)
            self.telemetry.end_iteration(
                recursion_id=recursion_id,
                iteration=iteration,
                duration_ms=iter_duration,
                will_retry=iteration < max_iterations,
            )

            print()

        # ========================================
        # MAX ITERATIONS REACHED
        # ========================================
        print("⏱️  ITERATION LIMIT REACHED")
        print(f"   Max iterations: {max_iterations}")
        print(f"   Final progress: {goal_validation['confidence']:.1%}")
        print()

        return self._end_recursion(
            recursion_id,
            "ITERATION_LIMIT",
            max_iterations,
            learning_context,
            goal_validation,
            recursion_start,
            error=f"Reached iteration limit without achieving goal (progress: {goal_validation['confidence']:.1%})",
        )

    def _calculate_convergence(
        self,
        iteration: int,
        goal_validation: Dict[str, Any],
        learning_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculate convergence metrics.

        This is CRITICAL telemetry - shows whether recursion is working.

        Returns:
            {
                "progress_delta": float,  # Change from previous iteration
                "progress_rate": float,   # Average progress per iteration
                "is_converging": bool,    # Making forward progress
                "estimated_remaining": int,  # Iterations to completion
                "confidence_trend": str   # strong/weak/stalled/diverging
            }
        """
        current_progress = goal_validation["confidence"]

        if iteration == 1:
            return {
                "progress_delta": None,
                "progress_rate": None,
                "is_converging": None,
                "estimated_remaining": None,
                "confidence_trend": "initial",
            }

        # Get previous progress
        previous_progress = learning_context["hypothesis_evolution"][-1]["progress"]
        progress_delta = current_progress - previous_progress

        # Calculate overall progress rate
        all_progress = [h["progress"] for h in learning_context["hypothesis_evolution"]]
        all_progress.append(current_progress)

        if len(all_progress) >= 2:
            progress_rate = (current_progress - all_progress[0]) / iteration
        else:
            progress_rate = progress_delta

        # Determine if converging
        is_converging = progress_delta > 0

        # Estimate iterations remaining
        if is_converging and progress_rate > 0:
            remaining_progress = 1.0 - current_progress
            estimated_remaining = int(remaining_progress / progress_rate) + 1
        else:
            estimated_remaining = None

        # Confidence trend
        if progress_delta > 0.2:
            confidence_trend = "strong_convergence"
        elif progress_delta > 0:
            confidence_trend = "weak_convergence"
        elif progress_delta == 0:
            confidence_trend = "stalled"
        else:
            confidence_trend = "diverging"

        return {
            "progress_delta": progress_delta,
            "progress_rate": progress_rate,
            "is_converging": is_converging,
            "estimated_remaining": estimated_remaining,
            "confidence_trend": confidence_trend,
        }

    def _end_recursion(
        self,
        recursion_id: str,
        status: str,
        final_iteration: int,
        learning_context: Dict[str, Any],
        goal_validation: Dict[str, Any],
        recursion_start: float,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """End recursion with telemetry."""
        duration_ms = int((time.time() - recursion_start) * 1000)

        # End telemetry
        self.telemetry.end_recursion(
            recursion_id=recursion_id,
            status=status,
            final_iteration=final_iteration,
            total_duration_ms=duration_ms,
            evidence_level=goal_validation.get("evidence_level"),
            total_cost_usd=self.executor.get_cumulative_cost(),
            final_progress=goal_validation.get("confidence", 0.0),
            abort_reason=error,
            learning_trajectory=learning_context.get("hypothesis_evolution"),
        )

        # Generate telemetry report
        telemetry_report_path = os.path.join(
            self.evidence_root, "telemetry", f"{recursion_id}_report.txt"
        )
        report = self.telemetry.generate_report(recursion_id)
        with open(telemetry_report_path, "w") as f:
            f.write(report)

        return {
            "status": status,
            "recursion_id": recursion_id,
            "iterations": final_iteration,
            "final_evidence_level": goal_validation.get("evidence_level", "E0"),
            "total_cost_usd": self.executor.get_cumulative_cost(),
            "duration_ms": duration_ms,
            "goal_criteria_met": goal_validation.get("criteria_met", {}),
            "final_progress": goal_validation.get("confidence", 0.0),
            "learning_trajectory": learning_context.get("hypothesis_evolution"),
            "telemetry": self.telemetry.get_recursion_telemetry(recursion_id),
            "telemetry_report_path": telemetry_report_path,
            "summary": error
            or f"{'Success' if status == 'GOAL_ACHIEVED' else 'Failed'}: {status}",
        }
