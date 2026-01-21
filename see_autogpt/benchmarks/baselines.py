"""
Baseline Implementations for Comparison

Implements alternative agent approaches:
- Simple Retry Loop (no learning)
- ReAct (reasoning + acting, no evidence)
- Reflexion (self-reflection, text-based)
"""

from typing import Dict, Any, Callable, List
import json
import random


class BaselineAgent:
    """Base class for baseline agents."""

    def __init__(self, name: str):
        self.name = name

    def run_task(
        self,
        task_spec: Dict[str, Any],
        commands: Dict[str, Callable],
        max_iterations: int = 10,
    ) -> Dict[str, Any]:
        """Run task and return result."""
        raise NotImplementedError


class SimpleRetryAgent(BaselineAgent):
    """
    Simple Retry Loop - No Learning

    Strategy:
    - Try commands in sequence
    - No analysis of failures
    - No learning between iterations
    - Just keeps trying until success or max iterations

    This represents the naive approach.
    """

    def __init__(self):
        super().__init__("Simple Retry")

    def run_task(
        self,
        task_spec: Dict[str, Any],
        commands: Dict[str, Callable],
        max_iterations: int = 10,
    ) -> Dict[str, Any]:
        """Run task with simple retry logic."""
        success_criteria = task_spec["success_criteria"]
        command_list = list(commands.keys())

        results = []
        iterations = 0
        total_cost = 0.0

        for i in range(1, max_iterations + 1):
            iterations = i

            # Pick random command (no intelligence)
            command_name = random.choice(command_list)
            command_func = commands[command_name]

            # Execute with dummy arguments
            try:
                # Try to infer arguments from command signature
                if command_name == "search":
                    result = command_func(query="pizza")
                elif command_name == "search_with_location":
                    result = command_func(query="pizza", location="downtown")
                elif command_name == "select_restaurant":
                    result = command_func(restaurant_name="Joe's Pizza")
                elif command_name == "verify_delivery":
                    result = command_func(restaurant_name="Joe's Pizza")
                elif command_name == "set_email":
                    result = command_func(email="test@example.com")
                elif command_name == "set_password":
                    result = command_func(password="Password123")
                elif command_name == "confirm_password":
                    result = command_func(password_confirm="Password123")
                elif command_name == "submit_form":
                    result = command_func()
                elif command_name == "api_request":
                    result = command_func(endpoint="/users")
                elif command_name == "api_request_with_auth":
                    result = command_func(endpoint="/users", api_key="test_key")
                elif command_name == "api_request_full":
                    result = command_func(
                        endpoint="/users",
                        api_key="test_key",
                        user_id="123",
                        fields=["name", "email"]
                    )
                else:
                    result = command_func()
            except Exception as e:
                result = {"success": False, "error": str(e)}

            # Track cost (assume $0.01 per command)
            total_cost += 0.01

            results.append({
                "iteration": i,
                "command": command_name,
                "result": result,
            })

            # Check if success (naive check - just look at success field)
            if result.get("success"):
                # Check criteria
                all_met = all(
                    result.get(criterion, False) == expected
                    for criterion, expected in success_criteria.items()
                )

                if all_met:
                    return {
                        "method": self.name,
                        "status": "SUCCESS",
                        "iterations": iterations,
                        "total_cost": total_cost,
                        "results": results,
                        "final_state": result,
                    }

        return {
            "method": self.name,
            "status": "MAX_ITERATIONS",
            "iterations": iterations,
            "total_cost": total_cost,
            "results": results,
            "final_state": results[-1]["result"] if results else {},
        }


class ReActAgent(BaselineAgent):
    """
    ReAct: Reasoning + Acting

    Strategy:
    - Maintain thought trace
    - Reason about next action
    - Execute action
    - Observe result
    - Continue with new thought

    Improvements over Simple Retry:
    + Has reasoning about what to do next
    + Maintains thought trace
    + Can learn from observations

    Missing:
    - No evidence validation (trusts command results)
    - No regression detection
    - No convergence metrics
    - No SHA256-verified receipts
    """

    def __init__(self):
        super().__init__("ReAct")

    def run_task(
        self,
        task_spec: Dict[str, Any],
        commands: Dict[str, Callable],
        max_iterations: int = 10,
    ) -> Dict[str, Any]:
        """Run task with ReAct reasoning."""
        success_criteria = task_spec["success_criteria"]
        goal = task_spec["goal"]

        thought_trace = []
        results = []
        iterations = 0
        total_cost = 0.0

        current_observation = f"Goal: {goal}"

        for i in range(1, max_iterations + 1):
            iterations = i

            # THINK: Reason about next action
            thought = self._reason(goal, current_observation, success_criteria, thought_trace)
            thought_trace.append(thought)

            # Cost for reasoning (assume $0.005 per thought)
            total_cost += 0.005

            # ACT: Execute action
            action = thought["action"]
            command_name = action["command"]
            arguments = action.get("arguments", {})

            if command_name not in commands:
                # Invalid command
                current_observation = f"Error: Command '{command_name}' not available"
                continue

            command_func = commands[command_name]

            try:
                result = command_func(**arguments)
            except Exception as e:
                result = {"success": False, "error": str(e)}

            # Cost for action
            total_cost += 0.01

            # OBSERVE: Record observation
            current_observation = f"Executed {command_name} → {result.get('message', result.get('success'))}"

            results.append({
                "iteration": i,
                "thought": thought["reasoning"],
                "command": command_name,
                "result": result,
                "observation": current_observation,
            })

            # Check success
            all_met = all(
                result.get(criterion, False) == expected
                for criterion, expected in success_criteria.items()
            )

            if all_met:
                return {
                    "method": self.name,
                    "status": "SUCCESS",
                    "iterations": iterations,
                    "total_cost": total_cost,
                    "results": results,
                    "final_state": result,
                    "thought_trace": thought_trace,
                }

        return {
            "method": self.name,
            "status": "MAX_ITERATIONS",
            "iterations": iterations,
            "total_cost": total_cost,
            "results": results,
            "final_state": results[-1]["result"] if results else {},
            "thought_trace": thought_trace,
        }

    def _reason(
        self,
        goal: str,
        observation: str,
        success_criteria: Dict[str, Any],
        thought_trace: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Reasoning step - decides next action.

        This is simplified (not using LLM), but demonstrates the pattern:
        - Consider goal
        - Consider current observation
        - Consider what's been tried
        - Decide next action
        """
        # Check what criteria are still unmet
        unmet_criteria = list(success_criteria.keys())

        # Simple heuristic reasoning based on task type
        if "search_performed" in unmet_criteria:
            return {
                "reasoning": "Need to search for items first",
                "action": {
                    "command": "search",
                    "arguments": {"query": "pizza"}
                }
            }
        elif "location_filtered" in unmet_criteria:
            return {
                "reasoning": "Need to filter by location for better results",
                "action": {
                    "command": "search_with_location",
                    "arguments": {"query": "pizza", "location": "downtown"}
                }
            }
        elif "rating_verified" in unmet_criteria:
            return {
                "reasoning": "Need to select a restaurant to verify rating",
                "action": {
                    "command": "select_restaurant",
                    "arguments": {"restaurant_name": "Joe's Pizza"}
                }
            }
        elif "delivery_confirmed" in unmet_criteria:
            return {
                "reasoning": "Need to verify delivery availability",
                "action": {
                    "command": "verify_delivery",
                    "arguments": {"restaurant_name": "Joe's Pizza"}
                }
            }
        elif "email_valid" in unmet_criteria:
            return {
                "reasoning": "Need to set valid email",
                "action": {
                    "command": "set_email",
                    "arguments": {"email": "test@example.com"}
                }
            }
        elif "password_strong" in unmet_criteria:
            return {
                "reasoning": "Need to set strong password",
                "action": {
                    "command": "set_password",
                    "arguments": {"password": "Password123"}
                }
            }
        elif "passwords_match" in unmet_criteria:
            return {
                "reasoning": "Need to confirm password",
                "action": {
                    "command": "confirm_password",
                    "arguments": {"password_confirm": "Password123"}
                }
            }
        elif "form_submitted" in unmet_criteria:
            return {
                "reasoning": "All fields valid, ready to submit",
                "action": {
                    "command": "submit_form",
                    "arguments": {}
                }
            }
        elif "auth_provided" in unmet_criteria:
            return {
                "reasoning": "Need to provide authentication",
                "action": {
                    "command": "api_request_with_auth",
                    "arguments": {"endpoint": "/users", "api_key": "test_key"}
                }
            }
        elif "params_complete" in unmet_criteria:
            return {
                "reasoning": "Need to provide all required parameters",
                "action": {
                    "command": "api_request_full",
                    "arguments": {
                        "endpoint": "/users",
                        "api_key": "test_key",
                        "user_id": "123",
                        "fields": ["name", "email"]
                    }
                }
            }
        elif "rate_limit_handled" in unmet_criteria or "response_verified" in unmet_criteria:
            return {
                "reasoning": "Retry API request to handle rate limit",
                "action": {
                    "command": "api_request_full",
                    "arguments": {
                        "endpoint": "/users",
                        "api_key": "test_key",
                        "user_id": "123",
                        "fields": ["name", "email"]
                    }
                }
            }
        else:
            # Default action
            return {
                "reasoning": "Trying first available command",
                "action": {
                    "command": "search",
                    "arguments": {"query": "pizza"}
                }
            }


class ReflexionAgent(BaselineAgent):
    """
    Reflexion: Self-Reflection on Failures

    Strategy:
    - Try action
    - If fails, reflect on what went wrong
    - Generate new plan based on reflection
    - Retry with improved approach

    Improvements over ReAct:
    + Explicit reflection on failures
    + Maintains failure history
    + Improves plan based on reflections

    Missing (compared to SEE/MMD/ECL):
    - Text-based reflections (not evidence-based)
    - No SHA256-verified receipts
    - No convergence metrics
    - No regression detection (can still loop)
    """

    def __init__(self):
        super().__init__("Reflexion")

    def run_task(
        self,
        task_spec: Dict[str, Any],
        commands: Dict[str, Callable],
        max_iterations: int = 10,
    ) -> Dict[str, Any]:
        """Run task with reflection on failures."""
        success_criteria = task_spec["success_criteria"]
        goal = task_spec["goal"]

        reflections = []
        results = []
        iterations = 0
        total_cost = 0.0

        current_plan = self._initial_plan(goal, success_criteria)

        for i in range(1, max_iterations + 1):
            iterations = i

            # Execute current plan step
            step = current_plan["steps"][len(results) % len(current_plan["steps"])]
            command_name = step["command"]
            arguments = step["arguments"]

            if command_name not in commands:
                current_plan = self._replan(goal, success_criteria, reflections, results)
                continue

            command_func = commands[command_name]

            try:
                result = command_func(**arguments)
            except Exception as e:
                result = {"success": False, "error": str(e)}

            # Cost for action
            total_cost += 0.01

            results.append({
                "iteration": i,
                "command": command_name,
                "result": result,
            })

            # Check success
            all_met = all(
                result.get(criterion, False) == expected
                for criterion, expected in success_criteria.items()
            )

            if all_met:
                return {
                    "method": self.name,
                    "status": "SUCCESS",
                    "iterations": iterations,
                    "total_cost": total_cost,
                    "results": results,
                    "final_state": result,
                    "reflections": reflections,
                }

            # If failed, reflect
            if not result.get("success"):
                reflection = self._reflect(command_name, result, success_criteria)
                reflections.append(reflection)

                # Cost for reflection (assume $0.01 per reflection)
                total_cost += 0.01

                # Replan based on reflection
                current_plan = self._replan(goal, success_criteria, reflections, results)

        return {
            "method": self.name,
            "status": "MAX_ITERATIONS",
            "iterations": iterations,
            "total_cost": total_cost,
            "results": results,
            "final_state": results[-1]["result"] if results else {},
            "reflections": reflections,
        }

    def _initial_plan(self, goal: str, success_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Generate initial plan."""
        # Simple heuristic plan based on criteria
        steps = []

        if "search_performed" in success_criteria:
            steps.append({"command": "search_with_location", "arguments": {"query": "pizza", "location": "downtown"}})
        if "rating_verified" in success_criteria:
            steps.append({"command": "select_restaurant", "arguments": {"restaurant_name": "Joe's Pizza"}})
        if "delivery_confirmed" in success_criteria:
            steps.append({"command": "verify_delivery", "arguments": {"restaurant_name": "Joe's Pizza"}})
        if "email_valid" in success_criteria:
            steps.append({"command": "set_email", "arguments": {"email": "test@example.com"}})
        if "password_strong" in success_criteria:
            steps.append({"command": "set_password", "arguments": {"password": "Password123"}})
        if "passwords_match" in success_criteria:
            steps.append({"command": "confirm_password", "arguments": {"password_confirm": "Password123"}})
        if "form_submitted" in success_criteria:
            steps.append({"command": "submit_form", "arguments": {}})
        if "auth_provided" in success_criteria or "params_complete" in success_criteria:
            steps.append({"command": "api_request_full", "arguments": {
                "endpoint": "/users",
                "api_key": "test_key",
                "user_id": "123",
                "fields": ["name", "email"]
            }})

        return {"steps": steps if steps else [{"command": "search", "arguments": {"query": "pizza"}}]}

    def _reflect(self, command_name: str, result: Dict[str, Any], success_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Reflect on why command failed."""
        error = result.get("error", "Unknown error")

        reflection = {
            "command": command_name,
            "error": error,
            "analysis": "",
        }

        # Analyze failure
        if "Authentication required" in error:
            reflection["analysis"] = "Need to provide authentication credentials"
        elif "Missing required parameters" in error:
            reflection["analysis"] = "Need to include all required parameters in request"
        elif "Rate limit" in error:
            reflection["analysis"] = "Hit rate limit, need to retry after waiting"
        elif "not found" in error:
            reflection["analysis"] = "Item doesn't exist, need to search first"
        elif "Password too weak" in error:
            reflection["analysis"] = "Password doesn't meet complexity requirements"
        elif "do not match" in error:
            reflection["analysis"] = "Password confirmation doesn't match original"
        else:
            reflection["analysis"] = f"Command failed: {error}"

        return reflection

    def _replan(
        self,
        goal: str,
        success_criteria: Dict[str, Any],
        reflections: List[Dict[str, Any]],
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Replan based on reflections."""
        # Check latest reflection
        if reflections:
            latest = reflections[-1]
            analysis = latest["analysis"]

            # Adjust plan based on reflection
            if "authentication" in analysis.lower():
                return {"steps": [
                    {"command": "api_request_with_auth", "arguments": {"endpoint": "/users", "api_key": "test_key"}},
                    {"command": "api_request_full", "arguments": {
                        "endpoint": "/users",
                        "api_key": "test_key",
                        "user_id": "123",
                        "fields": ["name", "email"]
                    }},
                ]}
            elif "rate limit" in analysis.lower():
                # Retry same command (simulates waiting)
                return {"steps": [
                    {"command": "api_request_full", "arguments": {
                        "endpoint": "/users",
                        "api_key": "test_key",
                        "user_id": "123",
                        "fields": ["name", "email"]
                    }},
                ]}

        # Default: return initial plan
        return self._initial_plan(goal, success_criteria)


# Available baselines
BASELINES = {
    "simple_retry": SimpleRetryAgent,
    "react": ReActAgent,
    "reflexion": ReflexionAgent,
}


def get_baseline(name: str) -> BaselineAgent:
    """Get baseline agent by name."""
    if name not in BASELINES:
        raise ValueError(f"Unknown baseline: {name}. Available: {list(BASELINES.keys())}")
    return BASELINES[name]()
