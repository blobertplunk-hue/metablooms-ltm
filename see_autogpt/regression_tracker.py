"""
Agent Regression Tracker

Prevents AutoGPT's infinite loop problem by detecting when the agent:
- Repeats the same failed action
- Makes backward progress
- Gets stuck in a loop

This integrates with MMD to detect missing progress.
"""

import hashlib
import json
import os
from typing import Any, Dict, List, Optional


class AgentRegressionTracker:
    """
    Tracks agent progress across iterations to prevent infinite loops.

    AutoGPT's critical flaw: Agent repeats same failed command forever.
    SEE Agent: Detects regression and aborts.
    """

    def __init__(self, task_id: str):
        """
        Initialize regression tracker.

        Args:
            task_id: Unique identifier for the task
        """
        self.task_id = task_id
        self.iteration_states: List[Dict[str, Any]] = []
        self.command_history: List[str] = []
        self.goal_progress_history: List[float] = []

    def observe(
        self,
        iteration: int,
        receipt: Dict[str, Any],
        goal_validation: Dict[str, Any],
    ) -> None:
        """
        Record state after iteration.

        Args:
            iteration: Iteration number
            receipt: Command execution receipt
            goal_validation: Goal validation result
        """
        # Generate state hash
        state_hash = self._hash_state(receipt, goal_validation)

        # Track command for duplicate detection
        command_sig = self._get_command_signature(receipt)
        self.command_history.append(command_sig)

        # Track goal progress
        progress = goal_validation.get("confidence", 0.0)
        self.goal_progress_history.append(progress)

        # Store iteration state
        self.iteration_states.append(
            {
                "iteration": iteration,
                "state_hash": state_hash,
                "command_signature": command_sig,
                "goal_progress": progress,
                "success": receipt.get("execution", {}).get("success", False),
                "criteria_met": goal_validation.get("criteria_met", {}),
            }
        )

    def detect_regression(self) -> Dict[str, Any]:
        """
        Detect if agent is regressing or stuck.

        Returns:
            {
                "is_regression": bool,
                "regression_type": "duplicate_command" | "backward_progress" | "stuck" | None,
                "severity": "BLOCK" | "WARN" | None,
                "evidence": str,
                "recommendation": "abort" | "continue" | "retry_different"
            }
        """
        if len(self.iteration_states) < 2:
            # Need at least 2 iterations to detect regression
            return {
                "is_regression": False,
                "regression_type": None,
                "severity": None,
                "evidence": "Insufficient iteration history",
                "recommendation": "continue",
            }

        # Check for duplicate commands (exact same command repeated)
        duplicate_check = self._check_duplicate_commands()
        if duplicate_check["is_regression"]:
            return duplicate_check

        # Check for backward progress (goal achievement decreasing)
        backward_check = self._check_backward_progress()
        if backward_check["is_regression"]:
            return backward_check

        # Check for stuck state (no progress for multiple iterations)
        stuck_check = self._check_stuck_state()
        if stuck_check["is_regression"]:
            return stuck_check

        # No regression detected
        return {
            "is_regression": False,
            "regression_type": None,
            "severity": None,
            "evidence": "Agent making forward progress",
            "recommendation": "continue",
        }

    def _check_duplicate_commands(self) -> Dict[str, Any]:
        """
        Check if agent is repeating the same command.

        This is AutoGPT's most common failure mode:
        - Try command
        - Fails
        - Try SAME command again
        - Fails again
        - Infinite loop
        """
        if len(self.command_history) < 2:
            return {"is_regression": False}

        # Check last 3 commands for duplicates
        recent_commands = self.command_history[-3:]
        current_command = recent_commands[-1]

        # Count occurrences
        duplicate_count = recent_commands.count(current_command)

        if duplicate_count >= 2:
            # Same command repeated at least twice recently
            # Check if both failed
            recent_states = self.iteration_states[-duplicate_count:]
            all_failed = all(not s["success"] for s in recent_states)

            if all_failed:
                return {
                    "is_regression": True,
                    "regression_type": "duplicate_command",
                    "severity": "BLOCK",
                    "evidence": f"Command '{current_command}' repeated {duplicate_count} times and failed each time",
                    "recommendation": "abort",
                }
            else:
                return {
                    "is_regression": True,
                    "regression_type": "duplicate_command",
                    "severity": "WARN",
                    "evidence": f"Command '{current_command}' repeated {duplicate_count} times",
                    "recommendation": "retry_different",
                }

        return {"is_regression": False}

    def _check_backward_progress(self) -> Dict[str, Any]:
        """
        Check if goal achievement is decreasing.

        Example: Had 2/3 criteria met, now only 1/3 met.
        """
        if len(self.goal_progress_history) < 2:
            return {"is_regression": False}

        # Compare last 2 iterations
        previous_progress = self.goal_progress_history[-2]
        current_progress = self.goal_progress_history[-1]

        # Check for significant decrease (> 20% drop)
        if current_progress < previous_progress - 0.2:
            return {
                "is_regression": True,
                "regression_type": "backward_progress",
                "severity": "WARN",
                "evidence": f"Goal progress decreased from {previous_progress:.1%} to {current_progress:.1%}",
                "recommendation": "retry_different",
            }

        return {"is_regression": False}

    def _check_stuck_state(self) -> Dict[str, Any]:
        """
        Check if agent is stuck (no progress for multiple iterations).

        Example: Last 3 iterations all at 33% progress.
        """
        if len(self.goal_progress_history) < 3:
            return {"is_regression": False}

        # Check last 3 iterations
        recent_progress = self.goal_progress_history[-3:]

        # All same progress (no improvement)
        if len(set(recent_progress)) == 1 and recent_progress[0] < 1.0:
            return {
                "is_regression": True,
                "regression_type": "stuck",
                "severity": "WARN",
                "evidence": f"No progress for 3 iterations (stuck at {recent_progress[0]:.1%})",
                "recommendation": "retry_different",
            }

        return {"is_regression": False}

    def _hash_state(
        self, receipt: Dict[str, Any], goal_validation: Dict[str, Any]
    ) -> str:
        """
        Generate hash of current state for comparison.
        """
        state_data = {
            "command": receipt.get("command", {}),
            "success": receipt.get("execution", {}).get("success"),
            "criteria_met": goal_validation.get("criteria_met", {}),
        }
        state_str = json.dumps(state_data, sort_keys=True)
        return hashlib.sha256(state_str.encode()).hexdigest()[:16]

    def _get_command_signature(self, receipt: Dict[str, Any]) -> str:
        """
        Generate unique signature for a command execution.

        This identifies the command + arguments, so we can detect
        exact duplicates.
        """
        command = receipt.get("command", {})
        command_name = command.get("name", "unknown")
        arguments = command.get("arguments", {})

        # Create signature from command and key arguments
        # (ignore variable arguments like timestamps)
        sig_data = {
            "name": command_name,
            "args": {k: v for k, v in arguments.items() if k not in ["timestamp"]},
        }
        sig_str = json.dumps(sig_data, sort_keys=True)
        return hashlib.sha256(sig_str.encode()).hexdigest()[:16]

    def get_progress_summary(self) -> str:
        """
        Generate human-readable progress summary.
        """
        if not self.iteration_states:
            return "No iterations yet"

        current_state = self.iteration_states[-1]
        progress = current_state["goal_progress"]
        iteration = current_state["iteration"]

        criteria = current_state["criteria_met"]
        met_count = sum(criteria.values())
        total_count = len(criteria)

        return (
            f"Iteration {iteration}: {met_count}/{total_count} criteria met "
            f"({progress:.1%} progress)"
        )

    def is_making_progress(self) -> bool:
        """
        Check if agent is making forward progress.

        Returns True if:
        - Progress increased in last iteration
        - OR current iteration succeeded
        """
        if not self.iteration_states:
            return True

        current = self.iteration_states[-1]

        # Check if current iteration succeeded
        if current["success"] and current["goal_progress"] > 0.5:
            return True

        # Check if progress increased
        if len(self.goal_progress_history) >= 2:
            previous_progress = self.goal_progress_history[-2]
            current_progress = self.goal_progress_history[-1]
            return current_progress > previous_progress

        return True
