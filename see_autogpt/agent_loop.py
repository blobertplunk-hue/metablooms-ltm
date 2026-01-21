"""
SEE-Powered Autonomous Agent Loop

The main orchestrator that replaces AutoGPT's broken loop with
evidence-based, fail-closed, recursive validation.

This is the complete SEE/MMD/ECL system applied to autonomous agents.
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


class SEEAutonomousAgent:
    """
    Evidence-based autonomous agent with fail-closed governance.

    AutoGPT Problems:
    - Infinite loops (no termination criteria)
    - Hallucinated success (trusts self-reports)
    - Expensive failures ($20+ per task)
    - No debugging capability (no evidence trail)

    SEE Agent Solutions:
    - Bounded iteration (max 5 by default)
    - Evidence-based termination (E3/E4 required)
    - Cost tracking and budgets
    - Full audit trail with SHA256 receipts
    - Self-correcting (patch provider)
    - Regression detection (prevents repeated errors)
    """

    def __init__(
        self,
        evidence_root: str,
        llm_provider: Optional[Any] = None,
        cost_tracker: Optional[Callable] = None,
    ):
        """
        Initialize SEE autonomous agent.

        Args:
            evidence_root: Directory to store evidence artifacts
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

    def run_task(
        self,
        task_spec: Dict[str, Any],
        command_provider: Callable[[Dict[str, Any], int], Dict[str, Any]],
        max_iterations: int = 5,
        cost_budget_usd: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute task using SEE loop.

        Args:
            task_spec: Task specification with goal and success criteria
            command_provider: Function that proposes next command to execute
                             (task_spec, iteration) -> {"name": str, "callable": Callable, "arguments": dict}
            max_iterations: Maximum iterations before termination (default: 5)
            cost_budget_usd: Optional cost budget in USD (default: no limit)

        Returns:
            {
                "status": "GOAL_ACHIEVED" | "ITERATION_LIMIT" | "BUDGET_EXCEEDED" | "REGRESSION_ABORT",
                "final_evidence_level": "E0" | "E1" | "E2" | "E3" | "E4",
                "iterations": int,
                "total_cost_usd": float,
                "goal_criteria_met": dict,
                "evidence_trail": [receipt_path1, ...],
                "summary": str
            }
        """
        task_id = task_spec.get("task_id", f"task_{int(time.time())}")
        task_spec["task_id"] = task_id

        # Initialize tracking
        tracker = AgentRegressionTracker(task_id)
        receipts = []
        receipt_paths = []

        start_time = datetime.utcnow()

        print(f"🚀 Starting SEE Agent Loop for task: {task_id}")
        print(f"   Goal: {task_spec.get('goal', 'unspecified')}")
        print(f"   Max iterations: {max_iterations}")
        if cost_budget_usd:
            print(f"   Budget: ${cost_budget_usd:.2f}")
        print()

        # Main SEE Loop
        for iteration in range(1, max_iterations + 1):
            print(f"━━━ Iteration {iteration}/{max_iterations} ━━━")

            # Step 1: Propose action
            print("  📋 Proposing action...")
            try:
                command_spec = command_provider(task_spec, iteration)
                command_name = command_spec["name"]
                command_callable = command_spec["callable"]
                command_arguments = command_spec["arguments"]

                print(f"     → Command: {command_name}")
                print(f"     → Arguments: {json.dumps(command_arguments, indent=8)}")

            except Exception as e:
                print(f"  ❌ Command proposal failed: {e}")
                return self._create_result(
                    "PROPOSAL_ERROR",
                    "E0",
                    iteration - 1,
                    receipts,
                    receipt_paths,
                    {},
                    start_time,
                    f"Command proposal failed: {e}",
                )

            # Step 2: Execute with evidence capture
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

            receipt_paths.append(exec_result["receipt_path"])

            # Load receipt for validation
            with open(exec_result["receipt_path"], "r") as f:
                receipt = json.load(f)
            receipts.append(receipt)

            # Step 3: Validate goal achievement
            print("  🎯 Validating goal...")
            goal_validation = self.goal_validator.validate_goal(
                task_spec, receipts, receipt
            )

            print(f"     → {goal_validation['rationale']}")
            print(f"     → Evidence level: {goal_validation['evidence_level']}")
            print(f"     → Confidence: {goal_validation['confidence']:.1%}")

            # Step 4: Track regression
            print("  🔍 Checking for regression...")
            tracker.observe(iteration, receipt, goal_validation)
            regression_check = tracker.detect_regression()

            if regression_check["is_regression"]:
                print(f"     ⚠️  {regression_check['evidence']}")
                print(f"     → Severity: {regression_check['severity']}")
            else:
                print(f"     ✅ {regression_check['evidence']}")

            # Step 5: Check budget
            if cost_budget_usd:
                print("  💰 Checking budget...")
                if not self.executor.check_budget(cost_budget_usd):
                    print(
                        f"     ❌ Budget exceeded: ${exec_result['cumulative_cost_usd']:.2f} > ${cost_budget_usd:.2f}"
                    )
                    return self._create_result(
                        "BUDGET_EXCEEDED",
                        goal_validation["evidence_level"],
                        iteration,
                        receipts,
                        receipt_paths,
                        goal_validation.get("criteria_met", {}),
                        start_time,
                        f"Budget exceeded at iteration {iteration}",
                    )
                else:
                    print(
                        f"     ✅ Within budget: ${exec_result['cumulative_cost_usd']:.2f} / ${cost_budget_usd:.2f}"
                    )

            # Step 6: Check if goal achieved
            if goal_validation["goal_achieved"]:
                print()
                print("🎉 GOAL ACHIEVED!")
                print(f"   Evidence level: {goal_validation['evidence_level']}")
                print(f"   Iterations: {iteration}")
                print(f"   Total cost: ${exec_result['cumulative_cost_usd']:.2f}")
                print()

                return self._create_result(
                    "GOAL_ACHIEVED",
                    goal_validation["evidence_level"],
                    iteration,
                    receipts,
                    receipt_paths,
                    goal_validation.get("criteria_met", {}),
                    start_time,
                    f"Goal achieved in {iteration} iteration(s)",
                )

            # Step 7: Check if should abort due to regression
            if regression_check.get("recommendation") == "abort":
                print()
                print("🛑 ABORTING: Regression detected")
                print(f"   Type: {regression_check['regression_type']}")
                print(f"   Evidence: {regression_check['evidence']}")
                print()

                return self._create_result(
                    "REGRESSION_ABORT",
                    goal_validation["evidence_level"],
                    iteration,
                    receipts,
                    receipt_paths,
                    goal_validation.get("criteria_met", {}),
                    start_time,
                    f"Aborted due to regression: {regression_check['evidence']}",
                )

            # Step 8: Diagnose and patch
            if iteration < max_iterations:
                print("  🔧 Diagnosing failure and generating patch...")
                patch = self.patch_provider.diagnose_and_patch(
                    receipt, goal_validation, task_spec, regression_check
                )

                if patch:
                    print(f"     → Diagnosis: {patch['diagnosis']}")
                    print(
                        f"     → Patch type: {patch['patch_type']} (confidence: {patch['confidence']:.1%})"
                    )
                    print(f"     → Rationale: {patch['corrective_action']['rationale']}")
                else:
                    print("     → No patch available, aborting")
                    return self._create_result(
                        "NO_PATCH_AVAILABLE",
                        goal_validation["evidence_level"],
                        iteration,
                        receipts,
                        receipt_paths,
                        goal_validation.get("criteria_met", {}),
                        start_time,
                        "No corrective patch could be generated",
                    )

            print()

        # Reached iteration limit without achieving goal
        print("⏱️  ITERATION LIMIT REACHED")
        print(f"   Max iterations: {max_iterations}")
        print(f"   Goal not achieved")
        print(f"   Final progress: {goal_validation['confidence']:.1%}")
        print(f"   Total cost: ${exec_result['cumulative_cost_usd']:.2f}")
        print()

        return self._create_result(
            "ITERATION_LIMIT",
            goal_validation["evidence_level"],
            max_iterations,
            receipts,
            receipt_paths,
            goal_validation.get("criteria_met", {}),
            start_time,
            f"Reached iteration limit without achieving goal (progress: {goal_validation['confidence']:.1%})",
        )

    def _create_result(
        self,
        status: str,
        evidence_level: str,
        iterations: int,
        receipts: List[Dict[str, Any]],
        receipt_paths: List[str],
        criteria_met: Dict[str, bool],
        start_time: datetime,
        summary: str,
    ) -> Dict[str, Any]:
        """
        Create standardized result object.
        """
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return {
            "status": status,
            "final_evidence_level": evidence_level,
            "iterations": iterations,
            "total_cost_usd": self.executor.get_cumulative_cost(),
            "duration_ms": duration_ms,
            "goal_criteria_met": criteria_met,
            "evidence_trail": receipt_paths,
            "summary": summary,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


def save_agent_result(result: Dict[str, Any], output_path: str) -> None:
    """
    Save agent execution result to file.
    """
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"📝 Result saved to: {output_path}")
