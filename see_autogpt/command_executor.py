"""
Evidence-Based Command Execution

Wraps agent commands with evidence capture, receipt generation,
and SHA256 verification. This is the foundation that prevents
AutoGPT's "hallucinated success" problem.
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional

# Add metablooms to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metablooms.evidence.store_v1 import EvidenceStore


class SEECommandExecutor:
    """
    Evidence-based command executor for autonomous agents.

    Every command execution generates:
    - Immutable evidence artifacts (stdout/stderr)
    - SHA256-verified receipts
    - Cost tracking
    - Evidence level classification

    This prevents:
    - Hallucinated success (requires proof)
    - Missing audit trail (all artifacts logged)
    - Mutable results (SHA256 hashes enforce immutability)
    """

    def __init__(self, evidence_root: str):
        """
        Initialize command executor.

        Args:
            evidence_root: Directory to store evidence artifacts
        """
        self.evidence_store = EvidenceStore(evidence_root)
        self.cumulative_cost_usd = 0.0

    def execute_with_evidence(
        self,
        command_name: str,
        command_callable: Callable,
        arguments: dict,
        task_spec: dict,
        iteration: int,
        llm_cost_tracker: Optional[Callable] = None,
    ) -> dict:
        """
        Execute a command and generate evidence receipt.

        Args:
            command_name: Name of command being executed
            command_callable: Function to execute
            arguments: Arguments to pass to command
            task_spec: Task specification with goal and criteria
            iteration: Current iteration number
            llm_cost_tracker: Optional function to track LLM API costs

        Returns:
            {
                "success": bool,
                "receipt_path": str,
                "evidence_level": "E0" | "E1" | "E2" | "E3" | "E4",
                "cost_usd": float,
                "duration_ms": int,
                "result_summary": str
            }
        """
        task_id = task_spec.get("task_id", "unknown")
        attempt_dir = self.evidence_store.alloc_attempt_dir(task_id, iteration)

        # Prepare output files
        stdout_path = os.path.join(attempt_dir, "stdout.txt")
        stderr_path = os.path.join(attempt_dir, "stderr.txt")
        result_path = os.path.join(attempt_dir, "result.json")

        # Track execution
        start_time = time.time()
        start_time_iso = datetime.utcnow().isoformat() + "Z"

        success = False
        error_message = None
        result_value = None

        try:
            # Execute command
            result_value = command_callable(**arguments)

            # Check if result indicates success
            # Different commands have different success indicators
            success = self._check_command_success(result_value)

            # Write result to file
            with open(result_path, "w") as f:
                json.dump(
                    {
                        "command": command_name,
                        "arguments": arguments,
                        "result": str(result_value),
                        "success": success,
                    },
                    f,
                    indent=2,
                )

            # Write stdout
            with open(stdout_path, "w") as f:
                f.write(str(result_value) if result_value else "")

        except Exception as e:
            success = False
            error_message = str(e)

            # Write error to stderr
            with open(stderr_path, "w") as f:
                f.write(f"Command: {command_name}\n")
                f.write(f"Arguments: {json.dumps(arguments, indent=2)}\n")
                f.write(f"Error: {error_message}\n")

            # Write error result
            with open(result_path, "w") as f:
                json.dump(
                    {
                        "command": command_name,
                        "arguments": arguments,
                        "error": error_message,
                        "success": False,
                    },
                    f,
                    indent=2,
                )

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Calculate cost
        iteration_cost = 0.0
        if llm_cost_tracker:
            iteration_cost = llm_cost_tracker(command_name, arguments, result_value)
        self.cumulative_cost_usd += iteration_cost

        # Generate evidence artifacts with hashes
        artifacts = []
        for path in [stdout_path, stderr_path, result_path]:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                artifacts.append(
                    {
                        "path": path,
                        "sha256": self.evidence_store.sha256(path),
                        "size_bytes": os.path.getsize(path),
                    }
                )

        # Classify evidence level
        evidence_level = self._classify_evidence_level(success, error_message)

        # Generate receipt
        receipt = {
            "receipt_version": "SEE_AGENT_RECEIPT_V1",
            "task_id": task_id,
            "iteration": iteration,
            "command": {
                "name": command_name,
                "arguments": arguments,
                "timestamp": start_time_iso,
            },
            "execution": {
                "success": success,
                "duration_ms": duration_ms,
                "error": error_message,
            },
            "cost": {
                "iteration_usd": iteration_cost,
                "cumulative_usd": self.cumulative_cost_usd,
            },
            "evidence_level_claimed": evidence_level,
            "artifacts": artifacts,
            "environment": {
                "python": sys.version.split()[0],
                "platform": sys.platform,
            },
        }

        receipt_path = os.path.join(attempt_dir, "receipt.json")
        with open(receipt_path, "w") as f:
            json.dump(receipt, f, indent=2)

        # Generate summary
        result_summary = self._generate_summary(
            command_name, success, result_value, error_message
        )

        return {
            "success": success,
            "receipt_path": receipt_path,
            "evidence_level": evidence_level,
            "cost_usd": iteration_cost,
            "cumulative_cost_usd": self.cumulative_cost_usd,
            "duration_ms": duration_ms,
            "result_summary": result_summary,
            "result_value": result_value,
        }

    def _check_command_success(self, result_value: Any) -> bool:
        """
        Determine if command result indicates success.

        Different commands have different success indicators:
        - Some return True/False
        - Some return data (success if not None)
        - Some raise exceptions on failure
        """
        if result_value is None:
            return False
        if isinstance(result_value, bool):
            return result_value
        if isinstance(result_value, dict):
            # Check for common success indicators
            if "success" in result_value:
                return result_value["success"]
            if "error" in result_value:
                return False
            # Non-empty dict is usually success
            return len(result_value) > 0
        if isinstance(result_value, str):
            # Non-empty string usually indicates output
            return len(result_value.strip()) > 0

        # Default: if we got a result, consider it success
        return True

    def _classify_evidence_level(
        self, success: bool, error_message: Optional[str]
    ) -> str:
        """
        Classify evidence level based on execution outcome.

        E0: Contradicted (failed with clear error)
        E1: Inferred (no direct evidence)
        E2: Partial (executed but failed)
        E3: Validated in isolation (executed successfully)
        E4: Validated in system (goal achieved - checked elsewhere)
        """
        if error_message:
            # Clear failure evidence
            return "E2"  # Partial: we tried, but failed

        if success:
            # Command executed successfully
            return "E3"  # Validated in isolation

        # Ambiguous result
        return "E1"  # Inferred only

    def _generate_summary(
        self,
        command_name: str,
        success: bool,
        result_value: Any,
        error_message: Optional[str],
    ) -> str:
        """Generate human-readable summary of execution."""
        if error_message:
            return f"❌ {command_name} failed: {error_message}"

        if success:
            # Truncate long results
            result_str = str(result_value)
            if len(result_str) > 200:
                result_str = result_str[:200] + "..."
            return f"✅ {command_name} succeeded: {result_str}"

        return f"⚠️  {command_name} completed with ambiguous result"

    def get_cumulative_cost(self) -> float:
        """Get total cost across all commands executed."""
        return self.cumulative_cost_usd

    def check_budget(self, budget_usd: float) -> bool:
        """
        Check if cumulative cost is within budget.

        Returns:
            True if within budget, False if exceeded
        """
        return self.cumulative_cost_usd <= budget_usd


def default_cost_tracker(
    command_name: str, arguments: dict, result_value: Any
) -> float:
    """
    Default cost tracking function.

    In a real implementation, this would:
    - Track LLM API token usage
    - Account for other API calls (web search, image gen, etc.)
    - Calculate costs based on provider pricing

    For this demo, we use simple estimates.
    """
    # Rough cost estimates (in USD)
    cost_map = {
        "web_search": 0.01,  # Google API
        "web_scrape": 0.005,  # Scraping service
        "llm_completion": 0.05,  # GPT-4 call
        "image_generate": 0.02,  # DALL-E
        "code_execute": 0.001,  # Local execution
    }

    # Default cost for unknown commands
    return cost_map.get(command_name, 0.01)
