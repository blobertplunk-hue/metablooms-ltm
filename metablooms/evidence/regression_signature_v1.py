class RegressionTracker:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.seen_hashes = set()

    def observe(self, result: dict) -> None:
        receipt = result.get("receipt_path")
        if receipt:
            self.seen_hashes.add(receipt)

    def is_stable(self) -> bool:
        return len(self.seen_hashes) >= 1
