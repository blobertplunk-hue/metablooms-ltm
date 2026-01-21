def diagnose(task_spec: dict, result: dict) -> dict:
    return {
        "exit_code": result.get("exit_code"),
        "stderr": result.get("stderr"),
        "rule": "NONZERO_EXIT" if result.get("exit_code") != 0 else "UNKNOWN",
    }
