"""
Agent Patch Provider

Analyzes failure evidence and generates corrective actions.
This is what makes the agent self-correcting instead of endlessly
repeating the same errors like AutoGPT.
"""

import json
import os
from typing import Any, Dict, List, Optional


class AgentPatchProvider:
    """
    Diagnoses failures and generates patches (corrective actions).

    AutoGPT: Fails → Logs error → Continues with same approach → Infinite loop
    SEE Agent: Fails → Diagnoses → Patches → Retries with correction → Success
    """

    def __init__(self, llm_provider: Optional[Any] = None):
        """
        Initialize patch provider.

        Args:
            llm_provider: Optional LLM for intelligent diagnosis.
                         If None, uses rule-based diagnosis.
        """
        self.llm_provider = llm_provider
        self.diagnosis_history: List[Dict[str, Any]] = []

    def diagnose_and_patch(
        self,
        receipt: Dict[str, Any],
        goal_validation: Dict[str, Any],
        task_spec: Dict[str, Any],
        regression_check: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze failure and generate corrective patch.

        Args:
            receipt: Command execution receipt (may show error)
            goal_validation: Goal validation result (shows unmet criteria)
            task_spec: Original task specification
            regression_check: Regression detection result

        Returns:
            Patch specification or None if no patch possible:
            {
                "patch_type": "retry_with_correction" | "different_approach" | "abort",
                "diagnosis": str,
                "corrective_action": {
                    "command": str,
                    "arguments": dict,
                    "rationale": str
                },
                "confidence": 0.0-1.0
            }
        """
        # First, check if we should abort based on regression
        if self._should_abort_based_on_regression(regression_check):
            return None

        # Analyze the failure
        diagnosis = self._diagnose_failure(receipt, goal_validation, task_spec)

        # Generate patch based on diagnosis
        patch = self._generate_patch(diagnosis, receipt, goal_validation, task_spec)

        # Store diagnosis for learning
        self.diagnosis_history.append(
            {
                "diagnosis": diagnosis,
                "patch": patch,
                "receipt": receipt.get("command", {}),
            }
        )

        return patch

    def _should_abort_based_on_regression(
        self, regression_check: Dict[str, Any]
    ) -> bool:
        """
        Check if regression detection recommends abort.
        """
        if regression_check.get("severity") == "BLOCK":
            return True
        if regression_check.get("recommendation") == "abort":
            return True
        return False

    def _diagnose_failure(
        self,
        receipt: Dict[str, Any],
        goal_validation: Dict[str, Any],
        task_spec: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Diagnose why the action failed or didn't achieve goal.

        Returns:
            {
                "failure_type": str,
                "root_cause": str,
                "evidence": str,
                "recoverable": bool
            }
        """
        execution = receipt.get("execution", {})
        error_message = execution.get("error")

        # Case 1: Command execution error
        if error_message:
            return self._diagnose_execution_error(error_message, receipt)

        # Case 2: Command succeeded but goal not achieved
        if execution.get("success") and not goal_validation.get("goal_achieved"):
            return self._diagnose_goal_miss(goal_validation, receipt, task_spec)

        # Case 3: Ambiguous failure
        return {
            "failure_type": "ambiguous",
            "root_cause": "Command completed but unclear if successful",
            "evidence": "No clear error, but goal not achieved",
            "recoverable": True,
        }

    def _diagnose_execution_error(
        self, error_message: str, receipt: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Diagnose command execution errors.

        Common patterns:
        - Missing parameters
        - Invalid arguments
        - Timeout
        - Permission denied
        - Not found (404)
        """
        error_lower = error_message.lower()

        # Pattern matching for common errors
        if "missing" in error_lower or "required" in error_lower:
            return {
                "failure_type": "missing_parameter",
                "root_cause": "Command called with missing required parameter",
                "evidence": error_message,
                "recoverable": True,
            }

        if "invalid" in error_lower or "unexpected" in error_lower:
            return {
                "failure_type": "invalid_argument",
                "root_cause": "Command called with invalid argument value",
                "evidence": error_message,
                "recoverable": True,
            }

        if "timeout" in error_lower:
            return {
                "failure_type": "timeout",
                "root_cause": "Command execution exceeded time limit",
                "evidence": error_message,
                "recoverable": True,
            }

        if "not found" in error_lower or "404" in error_lower:
            return {
                "failure_type": "not_found",
                "root_cause": "Requested resource does not exist",
                "evidence": error_message,
                "recoverable": True,
            }

        if "permission" in error_lower or "forbidden" in error_lower:
            return {
                "failure_type": "permission_denied",
                "root_cause": "Insufficient permissions for operation",
                "evidence": error_message,
                "recoverable": False,
            }

        # Unknown error
        return {
            "failure_type": "unknown_error",
            "root_cause": error_message,
            "evidence": error_message,
            "recoverable": True,
        }

    def _diagnose_goal_miss(
        self,
        goal_validation: Dict[str, Any],
        receipt: Dict[str, Any],
        task_spec: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Diagnose why command succeeded but goal not achieved.

        Example: Search succeeded but didn't find what we needed.
        """
        criteria_met = goal_validation.get("criteria_met", {})
        unmet_criteria = [k for k, v in criteria_met.items() if not v]

        if not unmet_criteria:
            return {
                "failure_type": "goal_validation_error",
                "root_cause": "Validation logic may be incorrect",
                "evidence": "Command succeeded, all criteria appear met, but goal marked not achieved",
                "recoverable": True,
            }

        # Identify first unmet criterion
        first_unmet = unmet_criteria[0]

        return {
            "failure_type": "goal_not_achieved",
            "root_cause": f"Criterion '{first_unmet}' not satisfied",
            "evidence": goal_validation.get("rationale", ""),
            "recoverable": True,
        }

    def _generate_patch(
        self,
        diagnosis: Dict[str, Any],
        receipt: Dict[str, Any],
        goal_validation: Dict[str, Any],
        task_spec: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Generate corrective patch based on diagnosis.
        """
        if not diagnosis.get("recoverable"):
            return None

        failure_type = diagnosis.get("failure_type")

        # Route to specific patch generator based on failure type
        if failure_type == "missing_parameter":
            return self._patch_missing_parameter(diagnosis, receipt, goal_validation)

        if failure_type == "invalid_argument":
            return self._patch_invalid_argument(diagnosis, receipt)

        if failure_type == "timeout":
            return self._patch_timeout(receipt)

        if failure_type == "not_found":
            return self._patch_not_found(receipt, task_spec)

        if failure_type == "goal_not_achieved":
            return self._patch_goal_miss(diagnosis, goal_validation, task_spec)

        # Default: retry with same approach (may not help, but worth trying)
        return {
            "patch_type": "retry_with_correction",
            "diagnosis": diagnosis.get("root_cause", "Unknown failure"),
            "corrective_action": {
                "command": receipt.get("command", {}).get("name"),
                "arguments": receipt.get("command", {}).get("arguments", {}),
                "rationale": "Retry with same parameters (no specific correction identified)",
            },
            "confidence": 0.3,
        }

    def _patch_missing_parameter(
        self,
        diagnosis: Dict[str, Any],
        receipt: Dict[str, Any],
        goal_validation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Patch for missing required parameters.

        Strategy: Identify missing param and provide default/inferred value.
        """
        # In production, this would use LLM to infer missing values
        # For demo, we suggest manual intervention
        return {
            "patch_type": "retry_with_correction",
            "diagnosis": diagnosis.get("root_cause"),
            "corrective_action": {
                "command": receipt.get("command", {}).get("name"),
                "arguments": {
                    **receipt.get("command", {}).get("arguments", {}),
                    "_note": "LLM would infer missing parameter here",
                },
                "rationale": "Add missing required parameter",
            },
            "confidence": 0.6,
        }

    def _patch_invalid_argument(
        self, diagnosis: Dict[str, Any], receipt: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Patch for invalid argument values.

        Strategy: Correct the invalid value.
        """
        return {
            "patch_type": "retry_with_correction",
            "diagnosis": diagnosis.get("root_cause"),
            "corrective_action": {
                "command": receipt.get("command", {}).get("name"),
                "arguments": {
                    **receipt.get("command", {}).get("arguments", {}),
                    "_note": "LLM would correct invalid argument here",
                },
                "rationale": "Fix invalid argument value",
            },
            "confidence": 0.5,
        }

    def _patch_timeout(self, receipt: Dict[str, Any]) -> Dict[str, Any]:
        """
        Patch for timeout errors.

        Strategy: Retry with longer timeout or simpler query.
        """
        return {
            "patch_type": "retry_with_correction",
            "diagnosis": "Command timed out",
            "corrective_action": {
                "command": receipt.get("command", {}).get("name"),
                "arguments": {
                    **receipt.get("command", {}).get("arguments", {}),
                    "timeout": 60,  # Increase timeout
                },
                "rationale": "Retry with longer timeout",
            },
            "confidence": 0.7,
        }

    def _patch_not_found(
        self, receipt: Dict[str, Any], task_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Patch for "not found" errors.

        Strategy: Try alternative approach or broader search.
        """
        return {
            "patch_type": "different_approach",
            "diagnosis": "Resource not found",
            "corrective_action": {
                "command": "search_alternative",  # Would use LLM to suggest alternative
                "arguments": {"original_query": receipt.get("command", {}).get("arguments")},
                "rationale": "Search with broader query or alternative method",
            },
            "confidence": 0.4,
        }

    def _patch_goal_miss(
        self,
        diagnosis: Dict[str, Any],
        goal_validation: Dict[str, Any],
        task_spec: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Patch for when command succeeded but goal not achieved.

        Strategy: Execute next logical step based on unmet criteria.
        """
        next_action = goal_validation.get("next_action_needed")

        return {
            "patch_type": "different_approach",
            "diagnosis": diagnosis.get("root_cause"),
            "corrective_action": {
                "command": "next_step",  # Would use LLM to determine specific command
                "arguments": {"action": next_action},
                "rationale": next_action or "Continue toward goal",
            },
            "confidence": 0.8,
        }

    def get_diagnosis_summary(self) -> str:
        """
        Generate summary of all diagnoses.
        """
        if not self.diagnosis_history:
            return "No failures diagnosed yet"

        failure_types = {}
        for entry in self.diagnosis_history:
            ftype = entry["diagnosis"].get("failure_type", "unknown")
            failure_types[ftype] = failure_types.get(ftype, 0) + 1

        summary = f"Total diagnoses: {len(self.diagnosis_history)}\n"
        for ftype, count in failure_types.items():
            summary += f"  - {ftype}: {count}\n"

        return summary
