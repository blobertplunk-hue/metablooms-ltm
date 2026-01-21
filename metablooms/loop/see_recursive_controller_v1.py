from typing import Dict, Any, Callable, Optional
from metablooms.evidence.receipt_validate_v1 import validate_receipt
from metablooms.evidence.regression_signature_v1 import RegressionTracker

class LoopAbort(Exception):
    pass

def run_see_loop(
    task_spec: Dict[str, Any],
    executor: Callable[[Dict[str, Any], int], Dict[str, Any]],
    diagnoser: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]],
    patch_provider: Callable[[Dict[str, Any]], Optional[Dict[str, Any]]],
    max_iterations: int = 3,
) -> Dict[str, Any]:
    """
    Deterministic SEE recursive loop controller.
    Enforces bounded retries, evidence receipts, and stop conditions.
    """
    tracker = RegressionTracker(task_spec.get("task_id"))
    last_result: Optional[Dict[str, Any]] = None

    for iteration in range(1, max_iterations + 1):
        result = executor(task_spec, iteration)
        receipt_path = result.get("receipt_path")
        if not receipt_path:
            raise LoopAbort("MISSING_RECEIPT_PATH")

        validate_receipt(receipt_path)

        tracker.observe(result)

        if result.get("success") is True:
            if not tracker.is_stable():
                raise LoopAbort("REGRESSION_DETECTED")
            return {
                "status": "PASS",
                "iterations": iteration,
                "final_receipt": receipt_path,
            }

        diagnosis = diagnoser(task_spec, result)
        patch = patch_provider(diagnosis)

        if not patch:
            return {
                "status": "FAIL",
                "iterations": iteration,
                "final_receipt": receipt_path,
                "reason": "NO_PATCH_AVAILABLE",
            }

        last_result = result

    return {
        "status": "FAIL",
        "iterations": max_iterations,
        "final_receipt": last_result.get("receipt_path") if last_result else None,
        "reason": "MAX_ITERATIONS_EXCEEDED",
    }
