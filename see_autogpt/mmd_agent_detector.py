"""
Missing Middle Detector for Autonomous Agents

Detects missing capabilities in agent implementations.
This is the meta-validator that ensures agents have all required
evidence-based components.

Just like the original MMD detects missing SEE loop components,
this variant detects missing AGENT capabilities.
"""

import os
from typing import Any, Dict, List


class AgentMissingMiddleDetector:
    """
    Detects missing middles in autonomous agent implementations.

    Validates that agent has:
    1. GOAL_SPECIFICATION: Explicit goals with success criteria
    2. EVIDENCE_CAPTURE: Commands generate receipts
    3. GOAL_VALIDATION: Success verified with evidence
    4. FAILURE_DIAGNOSIS: Errors analyzed and diagnosed
    5. PATCH_GENERATION: Corrections generated for failures
    6. REGRESSION_DETECTION: Prevents repeated errors
    7. COST_TRACKING: Budget enforcement
    8. BOUNDED_ITERATION: Terminates based on evidence, not arbitrary limits
    """

    # Detection axes specific to autonomous agents
    AGENT_AXES = [
        "GOAL_SPECIFICATION",
        "EVIDENCE_CAPTURE",
        "GOAL_VALIDATION",
        "FAILURE_DIAGNOSIS",
        "PATCH_GENERATION",
        "REGRESSION_DETECTION",
        "COST_TRACKING",
        "BOUNDED_ITERATION",
    ]

    def detect_missing_middles(self, agent_root: str) -> List[Dict[str, Any]]:
        """
        Detect missing middles in agent implementation.

        Args:
            agent_root: Root directory of agent implementation

        Returns:
            List of findings:
            [{
                "severity": "BLOCK" | "WARN",
                "category": str,
                "missing": str,
                "description": str
            }]
        """
        findings = []

        # Check each axis
        findings.extend(self._check_goal_specification(agent_root))
        findings.extend(self._check_evidence_capture(agent_root))
        findings.extend(self._check_goal_validation(agent_root))
        findings.extend(self._check_failure_diagnosis(agent_root))
        findings.extend(self._check_patch_generation(agent_root))
        findings.extend(self._check_regression_detection(agent_root))
        findings.extend(self._check_cost_tracking(agent_root))
        findings.extend(self._check_bounded_iteration(agent_root))

        return findings

    def _check_goal_specification(self, agent_root: str) -> List[Dict[str, Any]]:
        """
        GOAL_SPECIFICATION: Agent must have explicit goals with success criteria.

        AutoGPT problem: Vague objectives, no measurable success criteria.
        SEE solution: Structured task specs with success_criteria dict.
        """
        findings = []

        # Check if agent has task specification structure
        # (in production implementation, not just demo code)
        agent_files = self._get_agent_files(agent_root)

        # Look for goal/task specification handling
        has_goal_spec = False
        for filepath in agent_files:
            if self._file_contains_pattern(filepath, "success_criteria"):
                has_goal_spec = True
                break

        if not has_goal_spec:
            findings.append(
                {
                    "severity": "BLOCK",
                    "category": "GOAL_SPECIFICATION",
                    "missing": "Success criteria specification",
                    "description": "Agent has no structured goal specification with measurable success criteria. "
                    "Cannot validate goal achievement without explicit criteria.",
                }
            )

        return findings

    def _check_evidence_capture(self, agent_root: str) -> List[Dict[str, Any]]:
        """
        EVIDENCE_CAPTURE: Commands must generate SHA256-verified receipts.

        AutoGPT problem: Results are mutable strings, no audit trail.
        SEE solution: Every command generates immutable receipt with artifacts.
        """
        findings = []

        # Check if agent has evidence/receipt generation
        required_components = [
            ("command_executor", "Evidence-based command execution"),
            ("receipt", "Receipt generation with SHA256 hashes"),
        ]

        for component, description in required_components:
            if not self._has_component(agent_root, component):
                findings.append(
                    {
                        "severity": "BLOCK",
                        "category": "EVIDENCE_CAPTURE",
                        "missing": description,
                        "description": f"Agent missing: {description}. "
                        "Commands must generate immutable evidence artifacts.",
                    }
                )

        return findings

    def _check_goal_validation(self, agent_root: str) -> List[Dict[str, Any]]:
        """
        GOAL_VALIDATION: Must validate goal achievement with evidence.

        AutoGPT problem: Trusts self-reported success.
        SEE solution: GoalValidator checks evidence against criteria.
        """
        findings = []

        if not self._has_component(agent_root, "goal_validator"):
            findings.append(
                {
                    "severity": "BLOCK",
                    "category": "GOAL_VALIDATION",
                    "missing": "Goal validation system",
                    "description": "Agent has no goal validation. Cannot distinguish between "
                    "'command succeeded' and 'goal achieved'. Leads to hallucinated success.",
                }
            )

        return findings

    def _check_failure_diagnosis(self, agent_root: str) -> List[Dict[str, Any]]:
        """
        FAILURE_DIAGNOSIS: Must analyze failures and identify root causes.

        AutoGPT problem: Logs errors but doesn't analyze them.
        SEE solution: Failure diagnoser reads evidence and determines cause.
        """
        findings = []

        agent_files = self._get_agent_files(agent_root)

        # Look for diagnostic capability
        has_diagnosis = any(
            self._file_contains_pattern(f, "diagnose")
            or self._file_contains_pattern(f, "diagnosis")
            for f in agent_files
        )

        if not has_diagnosis:
            findings.append(
                {
                    "severity": "BLOCK",
                    "category": "FAILURE_DIAGNOSIS",
                    "missing": "Failure diagnosis system",
                    "description": "Agent has no failure diagnosis. Cannot learn from errors or "
                    "generate intelligent corrections.",
                }
            )

        return findings

    def _check_patch_generation(self, agent_root: str) -> List[Dict[str, Any]]:
        """
        PATCH_GENERATION: Must generate corrective actions for failures.

        AutoGPT problem: Repeats same errors infinitely.
        SEE solution: Patch provider generates corrections based on diagnosis.
        """
        findings = []

        if not self._has_component(agent_root, "patch"):
            findings.append(
                {
                    "severity": "BLOCK",
                    "category": "PATCH_GENERATION",
                    "missing": "Patch generation system",
                    "description": "Agent has no patch generation. Cannot self-correct. "
                    "Will repeat same errors infinitely.",
                }
            )

        return findings

    def _check_regression_detection(self, agent_root: str) -> List[Dict[str, Any]]:
        """
        REGRESSION_DETECTION: Must detect backward progress and repeated errors.

        AutoGPT problem: No detection of infinite loops.
        SEE solution: Regression tracker monitors progress across iterations.
        """
        findings = []

        if not self._has_component(agent_root, "regression"):
            findings.append(
                {
                    "severity": "BLOCK",
                    "category": "REGRESSION_DETECTION",
                    "missing": "Regression detection system",
                    "description": "Agent has no regression detection. Cannot detect when it's "
                    "repeating failed actions or making backward progress.",
                }
            )

        return findings

    def _check_cost_tracking(self, agent_root: str) -> List[Dict[str, Any]]:
        """
        COST_TRACKING: Must track API costs and enforce budgets.

        AutoGPT problem: Can spend $20+ on simple tasks.
        SEE solution: Cost tracker with budget enforcement.
        """
        findings = []

        agent_files = self._get_agent_files(agent_root)

        # Look for cost tracking
        has_cost_tracking = any(
            self._file_contains_pattern(f, "cost") for f in agent_files
        )

        if not has_cost_tracking:
            findings.append(
                {
                    "severity": "WARN",
                    "category": "COST_TRACKING",
                    "missing": "Cost tracking and budget enforcement",
                    "description": "Agent has no cost tracking. Cannot prevent expensive failures. "
                    "May spend excessive amounts on simple tasks.",
                }
            )

        return findings

    def _check_bounded_iteration(self, agent_root: str) -> List[Dict[str, Any]]:
        """
        BOUNDED_ITERATION: Must terminate based on evidence, not arbitrary limits.

        AutoGPT problem: Terminates after N cycles regardless of progress.
        SEE solution: Terminates when goal achieved (E3/E4) OR max iterations.
        """
        findings = []

        agent_files = self._get_agent_files(agent_root)

        # Look for evidence-based termination
        has_evidence_termination = any(
            self._file_contains_pattern(f, "goal_achieved")
            and self._file_contains_pattern(f, "evidence_level")
            for f in agent_files
        )

        if not has_evidence_termination:
            findings.append(
                {
                    "severity": "WARN",
                    "category": "BOUNDED_ITERATION",
                    "missing": "Evidence-based termination",
                    "description": "Agent may terminate based on arbitrary limits rather than "
                    "evidence of goal achievement.",
                }
            )

        return findings

    def _get_agent_files(self, agent_root: str) -> List[str]:
        """Get all Python files in agent directory."""
        python_files = []

        if not os.path.exists(agent_root):
            return python_files

        for root, dirs, files in os.walk(agent_root):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))

        return python_files

    def _has_component(self, agent_root: str, component_keyword: str) -> bool:
        """
        Check if agent has a component (file or class containing keyword).
        """
        agent_files = self._get_agent_files(agent_root)

        for filepath in agent_files:
            # Check filename
            if component_keyword.lower() in os.path.basename(filepath).lower():
                return True

            # Check file contents for class/function names
            if self._file_contains_pattern(filepath, component_keyword):
                return True

        return False

    def _file_contains_pattern(self, filepath: str, pattern: str) -> bool:
        """
        Check if file contains pattern (case-insensitive).
        """
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
                return pattern.lower() in content
        except Exception:
            return False

    def generate_report(self, findings: List[Dict[str, Any]]) -> str:
        """
        Generate human-readable MMD report.
        """
        if not findings:
            return "✅ No missing middles detected. Agent has all required capabilities."

        # Separate by severity
        blocks = [f for f in findings if f["severity"] == "BLOCK"]
        warns = [f for f in findings if f["severity"] == "WARN"]

        report = "🔍 Agent Missing Middle Detection Report\n"
        report += "=" * 60 + "\n\n"

        if blocks:
            report += f"❌ BLOCKING Issues ({len(blocks)}):\n"
            report += "-" * 60 + "\n"
            for finding in blocks:
                report += f"\n[{finding['category']}]\n"
                report += f"Missing: {finding['missing']}\n"
                report += f"Impact: {finding['description']}\n"

        if warns:
            report += f"\n⚠️  WARNINGS ({len(warns)}):\n"
            report += "-" * 60 + "\n"
            for finding in warns:
                report += f"\n[{finding['category']}]\n"
                report += f"Missing: {finding['missing']}\n"
                report += f"Impact: {finding['description']}\n"

        report += "\n" + "=" * 60 + "\n"
        report += f"Total findings: {len(findings)} ({len(blocks)} blocking, {len(warns)} warnings)\n"

        if blocks:
            report += "\n🛑 Agent CANNOT run safely until blocking issues are resolved.\n"

        return report
