"""
Goal Validation System

The critical missing middle in AutoGPT: validating that actions
actually achieve stated goals, not just that they "succeeded."

This is what prevents hallucinated success and ensures evidence-based
termination.
"""

import json
import os
from typing import Any, Dict, List, Optional


class GoalValidator:
    """
    Validates whether command execution achieved task goals.

    This is the KEY difference from AutoGPT:
    - AutoGPT: "Command returned success=True" → Continue
    - SEE Agent: "Did this achieve the goal?" → Validate with evidence
    """

    def validate_goal(
        self,
        task_spec: Dict[str, Any],
        receipts: List[Dict[str, Any]],
        current_receipt: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate if goal criteria are met based on accumulated evidence.

        Args:
            task_spec: Task specification with goal and success criteria
            receipts: All receipts from previous iterations
            current_receipt: Receipt from current iteration

        Returns:
            {
                "goal_achieved": bool,
                "criteria_met": {<criterion>: bool, ...},
                "evidence_level": "E0" | "E1" | "E2" | "E3" | "E4",
                "confidence": 0.0-1.0,
                "next_action_needed": str | None,
                "rationale": str
            }
        """
        goal = task_spec.get("goal", "")
        success_criteria = task_spec.get("success_criteria", {})

        if not success_criteria:
            # No explicit criteria - use command success as proxy
            return self._validate_without_criteria(current_receipt, goal)

        # Evaluate each criterion
        criteria_met = {}
        for criterion, expected_value in success_criteria.items():
            met = self._evaluate_criterion(
                criterion, expected_value, receipts, current_receipt
            )
            criteria_met[criterion] = met

        # Goal achieved if ALL criteria met
        goal_achieved = all(criteria_met.values())

        # Determine evidence level
        if goal_achieved:
            # All criteria met - check if validated in system (E4) or isolation (E3)
            evidence_level = self._determine_achievement_evidence_level(
                receipts, current_receipt
            )
        else:
            # Not achieved - determine partial evidence level
            evidence_level = current_receipt.get("evidence_level_claimed", "E1")

        # Calculate confidence
        if success_criteria:
            # Percentage of criteria met
            confidence = sum(criteria_met.values()) / len(criteria_met)
        else:
            confidence = 1.0 if goal_achieved else 0.0

        # Determine next action
        next_action = self._determine_next_action(
            goal_achieved, criteria_met, success_criteria
        )

        # Generate rationale
        rationale = self._generate_rationale(
            goal_achieved, criteria_met, current_receipt, evidence_level
        )

        return {
            "goal_achieved": goal_achieved,
            "criteria_met": criteria_met,
            "evidence_level": evidence_level,
            "confidence": confidence,
            "next_action_needed": next_action,
            "rationale": rationale,
        }

    def _evaluate_criterion(
        self,
        criterion: str,
        expected_value: Any,
        receipts: List[Dict[str, Any]],
        current_receipt: Dict[str, Any],
    ) -> bool:
        """
        Evaluate a single success criterion against evidence.

        This looks for evidence in:
        1. Command execution results
        2. Artifact contents (stdout/stderr)
        3. Previous iteration results

        Examples:
        - "order_confirmed": Look for confirmation in command result
        - "receipt_received": Check if receipt artifact exists
        - "delivery_time_known": Search for time in output
        """
        # Check current command result
        if self._check_criterion_in_receipt(criterion, expected_value, current_receipt):
            return True

        # Check accumulated evidence from all receipts
        for receipt in receipts:
            if self._check_criterion_in_receipt(criterion, expected_value, receipt):
                return True

        return False

    def _check_criterion_in_receipt(
        self, criterion: str, expected_value: Any, receipt: Dict[str, Any]
    ) -> bool:
        """
        Check if criterion is satisfied in a single receipt.

        Strategies:
        1. Check if criterion appears in command result
        2. Look for keywords in output artifacts
        3. Check execution success status
        """
        command_result = receipt.get("execution", {})

        # Strategy 1: Check command result directly
        if command_result.get(criterion) == expected_value:
            return True

        # Strategy 2: Check for evidence in artifacts
        artifacts = receipt.get("artifacts", [])
        for artifact in artifacts:
            if self._check_criterion_in_artifact(
                criterion, expected_value, artifact["path"]
            ):
                return True

        # Strategy 3: Check execution status for boolean criteria
        if isinstance(expected_value, bool) and expected_value:
            # If we're looking for True, check if command succeeded
            return command_result.get("success", False)

        return False

    def _check_criterion_in_artifact(
        self, criterion: str, expected_value: Any, artifact_path: str
    ) -> bool:
        """
        Search artifact contents for evidence of criterion.

        This is a simple keyword search. In production, this would use:
        - NLP/LLM to understand semantic meaning
        - Regex patterns for structured data
        - JSON parsing for structured outputs
        """
        if not os.path.exists(artifact_path):
            return False

        try:
            with open(artifact_path, "r") as f:
                content = f.read().lower()

            # Look for criterion keyword
            criterion_lower = criterion.replace("_", " ")
            if criterion_lower in content:
                # Found mention - check if positive or negative
                if isinstance(expected_value, bool):
                    if expected_value:
                        # Looking for True - check for positive indicators
                        positive_keywords = ["success", "confirmed", "received", "complete"]
                        return any(kw in content for kw in positive_keywords)
                    else:
                        # Looking for False - check for negative indicators
                        negative_keywords = ["failed", "error", "missing", "not found"]
                        return any(kw in content for kw in negative_keywords)

        except Exception:
            # Can't read artifact
            pass

        return False

    def _validate_without_criteria(
        self, current_receipt: Dict[str, Any], goal: str
    ) -> Dict[str, Any]:
        """
        Fallback validation when no explicit success criteria provided.

        Uses command execution success as proxy for goal achievement.
        This is what AutoGPT does, but we do it explicitly and with evidence.
        """
        success = current_receipt.get("execution", {}).get("success", False)
        evidence_level = current_receipt.get("evidence_level_claimed", "E1")

        return {
            "goal_achieved": success,
            "criteria_met": {"command_succeeded": success},
            "evidence_level": evidence_level,
            "confidence": 1.0 if success else 0.0,
            "next_action_needed": None if success else "Retry with different approach",
            "rationale": f"Goal: {goal}. Command {'succeeded' if success else 'failed'}. "
            f"Evidence level: {evidence_level}.",
        }

    def _determine_achievement_evidence_level(
        self, receipts: List[Dict[str, Any]], current_receipt: Dict[str, Any]
    ) -> str:
        """
        Determine evidence level when goal is achieved.

        E3: Validated in isolation (single command succeeded)
        E4: Validated in system (multiple commands converge to goal)
        """
        if len(receipts) > 1:
            # Multiple iterations converged to goal - stronger evidence
            return "E4"
        else:
            # Single iteration achieved goal
            return current_receipt.get("evidence_level_claimed", "E3")

    def _determine_next_action(
        self,
        goal_achieved: bool,
        criteria_met: Dict[str, bool],
        success_criteria: Dict[str, Any],
    ) -> Optional[str]:
        """
        Determine what action to take next based on validation.

        If goal not achieved, identify which criterion is missing and
        suggest next step.
        """
        if goal_achieved:
            return None

        # Find first unmet criterion
        for criterion, met in criteria_met.items():
            if not met:
                return self._suggest_action_for_criterion(criterion, success_criteria)

        return "Continue with next logical step toward goal"

    def _suggest_action_for_criterion(
        self, criterion: str, success_criteria: Dict[str, Any]
    ) -> str:
        """
        Suggest action to satisfy unmet criterion.

        This is where an LLM would be used in production to generate
        context-aware suggestions. For now, we use simple heuristics.
        """
        # Map common criteria to suggested actions
        suggestions = {
            "order_confirmed": "Submit order and verify confirmation",
            "receipt_received": "Check email or confirmation page for receipt",
            "delivery_time_known": "Look for delivery estimate in confirmation",
            "payment_processed": "Complete payment workflow",
            "account_created": "Submit registration form",
        }

        return suggestions.get(
            criterion, f"Take action to satisfy: {criterion.replace('_', ' ')}"
        )

    def _generate_rationale(
        self,
        goal_achieved: bool,
        criteria_met: Dict[str, bool],
        current_receipt: Dict[str, Any],
        evidence_level: str,
    ) -> str:
        """
        Generate human-readable rationale for validation decision.
        """
        if goal_achieved:
            return (
                f"✅ Goal achieved with evidence level {evidence_level}. "
                f"All {len(criteria_met)} criteria satisfied: {list(criteria_met.keys())}"
            )

        met_count = sum(criteria_met.values())
        total_count = len(criteria_met)
        unmet = [k for k, v in criteria_met.items() if not v]

        return (
            f"⏳ Goal not yet achieved. Progress: {met_count}/{total_count} criteria met. "
            f"Still need: {', '.join(unmet)}. Evidence level: {evidence_level}."
        )


def load_receipt(receipt_path: str) -> Dict[str, Any]:
    """Load receipt from file."""
    with open(receipt_path, "r") as f:
        return json.load(f)
