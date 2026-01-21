"""
Benchmark Task Definitions

Each task represents a realistic multi-step challenge that requires:
- Multiple attempts to succeed
- Learning from failures
- Evidence-based validation
"""

from typing import Dict, Any, List, Callable
import random


class BenchmarkTask:
    """Base class for benchmark tasks."""

    def __init__(self, task_id: str, description: str, success_criteria: Dict[str, Any]):
        self.task_id = task_id
        self.description = description
        self.success_criteria = success_criteria
        self.reset()

    def reset(self):
        """Reset task state for new run."""
        self.state = {}
        self.attempt_count = 0

    def get_task_spec(self) -> Dict[str, Any]:
        """Get task specification for agent."""
        return {
            "task_id": self.task_id,
            "goal": self.description,
            "success_criteria": self.success_criteria,
        }

    def get_available_commands(self) -> Dict[str, Callable]:
        """Get available commands for this task."""
        raise NotImplementedError

    def validate_success(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate if task succeeded based on evidence."""
        raise NotImplementedError


class MultiStepSearchTask(BenchmarkTask):
    """
    Task: Find a specific item by searching, filtering, and selecting.

    Requires 3 steps:
    1. Search with query
    2. Add location filter
    3. Select specific item

    Common failure modes:
    - Search without location (incomplete results)
    - Select without verifying availability
    - Wrong item selected
    """

    def __init__(self):
        super().__init__(
            task_id="multi_step_search",
            description="Find the best rated pizza restaurant in downtown that delivers",
            success_criteria={
                "search_performed": True,
                "location_filtered": True,
                "rating_verified": True,
                "delivery_confirmed": True,
            }
        )
        self.restaurants = [
            {"name": "Mario's Pizza", "rating": 3.5, "location": "uptown", "delivers": False},
            {"name": "Joe's Pizza", "rating": 4.8, "location": "downtown", "delivers": True},
            {"name": "Pizza Palace", "rating": 4.2, "location": "downtown", "delivers": False},
            {"name": "Best Pizza", "rating": 4.9, "location": "midtown", "delivers": True},
        ]

    def reset(self):
        super().reset()
        self.state = {
            "search_performed": False,
            "location_filtered": False,
            "rating_verified": False,
            "delivery_confirmed": False,
            "selected_restaurant": None,
        }

    def get_available_commands(self) -> Dict[str, Callable]:
        """Available commands for this task."""
        return {
            "search": self._search,
            "search_with_location": self._search_with_location,
            "select_restaurant": self._select_restaurant,
            "verify_delivery": self._verify_delivery,
        }

    def _search(self, query: str) -> Dict[str, Any]:
        """Basic search (returns all restaurants)."""
        self.attempt_count += 1
        self.state["search_performed"] = True

        return {
            "success": True,
            "results": self.restaurants,
            "count": len(self.restaurants),
            # Evidence
            "search_performed": True,
            "location_filtered": False,
            "rating_verified": False,
            "delivery_confirmed": False,
        }

    def _search_with_location(self, query: str, location: str) -> Dict[str, Any]:
        """Search with location filter (better results)."""
        self.attempt_count += 1
        self.state["search_performed"] = True
        self.state["location_filtered"] = True

        filtered = [r for r in self.restaurants if r["location"] == location]

        return {
            "success": True,
            "results": filtered,
            "count": len(filtered),
            # Evidence
            "search_performed": True,
            "location_filtered": True,
            "rating_verified": False,
            "delivery_confirmed": False,
        }

    def _select_restaurant(self, restaurant_name: str) -> Dict[str, Any]:
        """Select a specific restaurant."""
        self.attempt_count += 1

        restaurant = next((r for r in self.restaurants if r["name"] == restaurant_name), None)

        if not restaurant:
            return {
                "success": False,
                "error": "Restaurant not found",
                # Evidence
                "search_performed": self.state["search_performed"],
                "location_filtered": self.state["location_filtered"],
                "rating_verified": False,
                "delivery_confirmed": False,
            }

        self.state["selected_restaurant"] = restaurant
        self.state["rating_verified"] = True

        return {
            "success": True,
            "restaurant": restaurant,
            # Evidence
            "search_performed": self.state["search_performed"],
            "location_filtered": self.state["location_filtered"],
            "rating_verified": True,
            "delivery_confirmed": False,
        }

    def _verify_delivery(self, restaurant_name: str) -> Dict[str, Any]:
        """Verify if restaurant delivers."""
        self.attempt_count += 1

        restaurant = next((r for r in self.restaurants if r["name"] == restaurant_name), None)

        if not restaurant:
            return {
                "success": False,
                "error": "Restaurant not found",
                # Evidence
                "search_performed": self.state["search_performed"],
                "location_filtered": self.state["location_filtered"],
                "rating_verified": self.state["rating_verified"],
                "delivery_confirmed": False,
            }

        delivers = restaurant["delivers"]
        if delivers:
            self.state["delivery_confirmed"] = True

        return {
            "success": delivers,
            "delivers": delivers,
            # Evidence
            "search_performed": self.state["search_performed"],
            "location_filtered": self.state["location_filtered"],
            "rating_verified": self.state["rating_verified"],
            "delivery_confirmed": delivers,
        }

    def validate_success(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Check if all criteria met."""
        criteria_met = {
            criterion: state.get(criterion, False)
            for criterion in self.success_criteria
        }

        all_met = all(criteria_met.values())

        # Check if correct restaurant selected
        correct_selection = False
        if state.get("selected_restaurant"):
            restaurant = state["selected_restaurant"]
            correct_selection = (
                restaurant["location"] == "downtown" and
                restaurant["delivers"] and
                restaurant["rating"] >= 4.5
            )

        return {
            "success": all_met and correct_selection,
            "criteria_met": criteria_met,
            "correct_selection": correct_selection,
            "attempts": self.attempt_count,
        }


class FormValidationTask(BenchmarkTask):
    """
    Task: Fill out a form with validation requirements.

    Requires:
    1. Fill email (must be valid format)
    2. Fill password (must meet complexity requirements)
    3. Confirm password (must match)
    4. Submit form

    Common failure modes:
    - Invalid email format
    - Weak password
    - Password mismatch
    - Submit before all fields valid
    """

    def __init__(self):
        super().__init__(
            task_id="form_validation",
            description="Register account with valid email and strong password",
            success_criteria={
                "email_valid": True,
                "password_strong": True,
                "passwords_match": True,
                "form_submitted": True,
            }
        )

    def reset(self):
        super().reset()
        self.state = {
            "email": None,
            "password": None,
            "password_confirm": None,
            "email_valid": False,
            "password_strong": False,
            "passwords_match": False,
            "form_submitted": False,
        }

    def get_available_commands(self) -> Dict[str, Callable]:
        return {
            "set_email": self._set_email,
            "set_password": self._set_password,
            "confirm_password": self._confirm_password,
            "submit_form": self._submit_form,
        }

    def _set_email(self, email: str) -> Dict[str, Any]:
        """Set email field."""
        self.attempt_count += 1
        self.state["email"] = email

        # Validate email format
        valid = "@" in email and "." in email.split("@")[1]
        self.state["email_valid"] = valid

        return {
            "success": valid,
            "message": "Email valid" if valid else "Invalid email format",
            # Evidence
            "email_valid": valid,
            "password_strong": self.state["password_strong"],
            "passwords_match": self.state["passwords_match"],
            "form_submitted": False,
        }

    def _set_password(self, password: str) -> Dict[str, Any]:
        """Set password field."""
        self.attempt_count += 1
        self.state["password"] = password

        # Check password strength
        strong = (
            len(password) >= 8 and
            any(c.isupper() for c in password) and
            any(c.isdigit() for c in password)
        )
        self.state["password_strong"] = strong

        # Re-check match if confirm exists
        if self.state["password_confirm"]:
            self.state["passwords_match"] = (password == self.state["password_confirm"])

        return {
            "success": strong,
            "message": "Password strong" if strong else "Password too weak",
            # Evidence
            "email_valid": self.state["email_valid"],
            "password_strong": strong,
            "passwords_match": self.state["passwords_match"],
            "form_submitted": False,
        }

    def _confirm_password(self, password_confirm: str) -> Dict[str, Any]:
        """Confirm password field."""
        self.attempt_count += 1
        self.state["password_confirm"] = password_confirm

        match = (self.state["password"] == password_confirm) if self.state["password"] else False
        self.state["passwords_match"] = match

        return {
            "success": match,
            "message": "Passwords match" if match else "Passwords do not match",
            # Evidence
            "email_valid": self.state["email_valid"],
            "password_strong": self.state["password_strong"],
            "passwords_match": match,
            "form_submitted": False,
        }

    def _submit_form(self) -> Dict[str, Any]:
        """Submit the form."""
        self.attempt_count += 1

        # Check all validations
        can_submit = (
            self.state["email_valid"] and
            self.state["password_strong"] and
            self.state["passwords_match"]
        )

        if can_submit:
            self.state["form_submitted"] = True

        return {
            "success": can_submit,
            "message": "Form submitted" if can_submit else "Form validation failed",
            # Evidence
            "email_valid": self.state["email_valid"],
            "password_strong": self.state["password_strong"],
            "passwords_match": self.state["passwords_match"],
            "form_submitted": can_submit,
        }

    def validate_success(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Check if form successfully submitted."""
        criteria_met = {
            criterion: state.get(criterion, False)
            for criterion in self.success_criteria
        }

        return {
            "success": all(criteria_met.values()),
            "criteria_met": criteria_met,
            "attempts": self.attempt_count,
        }


class APIRetryTask(BenchmarkTask):
    """
    Task: Make API request that requires specific parameters.

    Requires:
    1. Include API key
    2. Include required parameters
    3. Handle rate limit (retry with backoff)
    4. Verify response

    Common failure modes:
    - Missing API key
    - Missing required parameters
    - No retry on rate limit
    - Accept partial response
    """

    def __init__(self):
        super().__init__(
            task_id="api_retry",
            description="Fetch user data from API with proper authentication and error handling",
            success_criteria={
                "auth_provided": True,
                "params_complete": True,
                "rate_limit_handled": True,
                "response_verified": True,
            }
        )
        self.rate_limit_count = 0

    def reset(self):
        super().reset()
        self.state = {
            "auth_provided": False,
            "params_complete": False,
            "rate_limit_handled": False,
            "response_verified": False,
        }
        self.rate_limit_count = 0

    def get_available_commands(self) -> Dict[str, Callable]:
        return {
            "api_request": self._api_request,
            "api_request_with_auth": self._api_request_with_auth,
            "api_request_full": self._api_request_full,
        }

    def _api_request(self, endpoint: str) -> Dict[str, Any]:
        """Basic API request (no auth)."""
        self.attempt_count += 1

        return {
            "success": False,
            "error": "Authentication required",
            # Evidence
            "auth_provided": False,
            "params_complete": False,
            "rate_limit_handled": False,
            "response_verified": False,
        }

    def _api_request_with_auth(self, endpoint: str, api_key: str) -> Dict[str, Any]:
        """API request with auth (missing params)."""
        self.attempt_count += 1
        self.state["auth_provided"] = True

        return {
            "success": False,
            "error": "Missing required parameters: user_id, fields",
            # Evidence
            "auth_provided": True,
            "params_complete": False,
            "rate_limit_handled": False,
            "response_verified": False,
        }

    def _api_request_full(self, endpoint: str, api_key: str, user_id: str, fields: List[str]) -> Dict[str, Any]:
        """Full API request with all parameters."""
        self.attempt_count += 1
        self.state["auth_provided"] = True
        self.state["params_complete"] = True

        # Simulate rate limit on first 2 attempts
        if self.rate_limit_count < 2:
            self.rate_limit_count += 1
            return {
                "success": False,
                "error": "Rate limit exceeded. Retry after 1 second.",
                "retry_after": 1,
                # Evidence
                "auth_provided": True,
                "params_complete": True,
                "rate_limit_handled": False,
                "response_verified": False,
            }

        # Success on 3rd attempt
        self.state["rate_limit_handled"] = True
        self.state["response_verified"] = True

        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "name": "John Doe",
                "email": "john@example.com",
            },
            # Evidence
            "auth_provided": True,
            "params_complete": True,
            "rate_limit_handled": True,
            "response_verified": True,
        }

    def validate_success(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Check if API request succeeded."""
        criteria_met = {
            criterion: state.get(criterion, False)
            for criterion in self.success_criteria
        }

        return {
            "success": all(criteria_met.values()),
            "criteria_met": criteria_met,
            "attempts": self.attempt_count,
        }


# Benchmark task suite
BENCHMARK_TASKS = [
    MultiStepSearchTask,
    FormValidationTask,
    APIRetryTask,
]


def get_all_tasks() -> List[BenchmarkTask]:
    """Get all benchmark tasks."""
    return [task_class() for task_class in BENCHMARK_TASKS]
