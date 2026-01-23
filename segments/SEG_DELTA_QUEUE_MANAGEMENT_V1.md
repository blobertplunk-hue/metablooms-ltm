# SEG_DELTA_QUEUE_MANAGEMENT_V1

**Segment ID**: SEG_DELTA_QUEUE_V1
**Type**: OPERATIONAL_INFRASTRUCTURE
**Authority**: VALIDATED
**Proof Class**: INTEGRATION_EXECUTION

## Purpose
Manage delta application with priority, dependencies, and superseding.

## Delta Queue Entry Schema
```python
@dataclass
class DeltaQueueEntry:
    delta_id: str
    priority: int  # 0 = P0 (highest), 1 = P1, 2 = P2
    created_utc: str
    dependencies: List[str]  # Must apply after these delta_ids
    supersedes: List[str]    # Replaces these delta_ids
    status: str  # "queued" | "applying" | "applied" | "failed" | "superseded"
    targets: List[str]  # Files this delta modifies
    sha256: str  # Delta artifact hash
```

## Priority Classification
```python
def classify_delta_priority(delta: Delta) -> int:
    """
    Assign priority based on delta targets.

    P0 (priority=0): Affects boot, security, or governance
    P1 (priority=1): Affects core runtime, gates, or pipelines
    P2 (priority=2): Documentation, examples, or optional features
    """
    boot_critical = [
        "RUN_METABLOOMS.py",
        "BOOT_METABLOOMS.py",
        "metablooms/runtime/runtime_entrypoint.py",
        "metablooms/preflight/gates/"
    ]

    runtime_critical = [
        "metablooms/runtime/",
        "metablooms/preflight/",
        "pipelines/"
    ]

    # P0: Any boot-critical file
    if any(target.startswith(bc) for bc in boot_critical
           for target in delta.targets):
        return 0

    # P1: Any runtime-critical file
    if any(target.startswith(rc) for rc in runtime_critical
           for target in delta.targets):
        return 1

    # P2: Everything else
    return 2
```

## Dependency Resolution
```python
def extract_dependencies(delta: Delta) -> List[str]:
    """
    Extract delta dependencies from manifest.

    Manifest format:
    {
      "preconditions": [
        {"type": "delta_applied", "delta_id": "DELTA_XYZ"},
        {"type": "file_exists", "path": "schemas/foo.json"}
      ]
    }
    """
    deps = []
    for precond in delta.manifest.get("preconditions", []):
        if precond["type"] == "delta_applied":
            deps.append(precond["delta_id"])
    return deps

def all_dependencies_satisfied(entry: DeltaQueueEntry,
                               applied_deltas: Set[str]) -> bool:
    """Check if all dependency deltas have been applied."""
    return all(dep in applied_deltas for dep in entry.dependencies)
```

## Superseding Detection
```python
def detect_superseding(delta: Delta, existing_queue: List[DeltaQueueEntry]) -> List[str]:
    """
    Detect if this delta supersedes older deltas.

    Rules:
    1. Explicit superseding: delta manifest declares "supersedes": [...]
    2. Implicit superseding: Same file targets + newer timestamp
    """
    supersedes = []

    # Explicit superseding
    if "supersedes" in delta.manifest:
        supersedes.extend(delta.manifest["supersedes"])

    # Implicit superseding (80% target overlap)
    for old_entry in existing_queue:
        if old_entry.status in ["queued", "failed"]:
            overlap = len(set(delta.targets) & set(old_entry.targets))
            overlap_ratio = overlap / max(len(delta.targets), len(old_entry.targets))

            if overlap_ratio >= 0.8:
                if delta.created_utc > old_entry.created_utc:
                    supersedes.append(old_entry.delta_id)

    return supersedes

def mark_superseded(delta_id: str, queue_path: Path):
    """Update queue entry status to 'superseded'."""
    queue = load_delta_queue(queue_path)

    for entry in queue:
        if entry.delta_id == delta_id:
            entry.status = "superseded"

    write_delta_queue(queue_path, queue)
```

## Queue Operations

### Enqueue
```python
def enqueue_delta(delta: Delta, queue_path: Path) -> DeltaQueueEntry:
    """
    Add delta to queue with automatic priority and superseding.

    Returns:
        DeltaQueueEntry with assigned priority and dependencies
    """
    existing_queue = load_delta_queue(queue_path)

    priority = classify_delta_priority(delta)
    dependencies = extract_dependencies(delta)
    supersedes = detect_superseding(delta, existing_queue)

    entry = DeltaQueueEntry(
        delta_id=delta.delta_id,
        priority=priority,
        created_utc=utcnow(),
        dependencies=dependencies,
        supersedes=supersedes,
        status="queued",
        targets=delta.targets,
        sha256=compute_sha256(delta.artifact_path)
    )

    # Mark superseded deltas
    for old_delta_id in entry.supersedes:
        mark_superseded(old_delta_id, queue_path)

    # Append to queue ledger (append-only)
    append_to_ledger(queue_path, entry)

    return entry
```

### Process Queue
```python
def process_delta_queue(queue_path: Path, os_root: Path) -> List[DeltaResult]:
    """
    Process queued deltas in priority order, respecting dependencies.

    Returns:
        List of DeltaResult (applied, failed, skipped)
    """
    queue = load_delta_queue(queue_path)
    applied_deltas = load_applied_deltas_set(os_root)
    results = []

    # Sort: P0 first, then by creation time within priority
    sorted_queue = sorted(
        [e for e in queue if e.status == "queued"],
        key=lambda e: (e.priority, e.created_utc)
    )

    for entry in sorted_queue:
        # Check dependencies satisfied
        if not all_dependencies_satisfied(entry, applied_deltas):
            results.append(DeltaResult(
                delta_id=entry.delta_id,
                status="skipped",
                reason="dependencies_not_satisfied"
            ))
            continue

        # Apply delta
        try:
            update_queue_status(entry.delta_id, "applying", queue_path)

            apply_result = apply_delta_with_receipt(
                os_root=os_root,
                delta_path=resolve_delta_path(entry.delta_id),
                receipt_path=os_root / "ledgers" / "deltas" / f"{entry.delta_id}.json"
            )

            if apply_result.success:
                update_queue_status(entry.delta_id, "applied", queue_path)
                applied_deltas.add(entry.delta_id)

                results.append(DeltaResult(
                    delta_id=entry.delta_id,
                    status="applied",
                    files_modified=apply_result.files_modified,
                    receipt_path=apply_result.receipt_path
                ))

            else:
                update_queue_status(entry.delta_id, "failed", queue_path)
                emit_failure_receipt(entry.delta_id, apply_result.reason)

                results.append(DeltaResult(
                    delta_id=entry.delta_id,
                    status="failed",
                    reason=apply_result.reason
                ))

        except Exception as e:
            update_queue_status(entry.delta_id, "failed", queue_path)
            emit_failure_receipt(entry.delta_id, str(e))

            results.append(DeltaResult(
                delta_id=entry.delta_id,
                status="failed",
                reason=str(e)
            ))

    return results
```

## Queue Persistence Format (JSONL)
```
# deltas/delta_queue.jsonl (append-only ledger)
{"delta_id": "DELTA_001", "priority": 0, "status": "applied", "timestamp": "2026-01-22T10:00:00Z"}
{"delta_id": "DELTA_002", "priority": 1, "status": "queued", "timestamp": "2026-01-22T11:00:00Z"}
{"delta_id": "DELTA_003", "priority": 0, "status": "superseded", "timestamp": "2026-01-22T12:00:00Z"}
```

## Queue Queries
```python
def get_pending_deltas(queue_path: Path) -> List[DeltaQueueEntry]:
    """Get all queued deltas ready to apply."""
    queue = load_delta_queue(queue_path)
    return [e for e in queue if e.status == "queued"]

def get_failed_deltas(queue_path: Path) -> List[DeltaQueueEntry]:
    """Get all failed deltas for investigation."""
    queue = load_delta_queue(queue_path)
    return [e for e in queue if e.status == "failed"]

def get_delta_status(delta_id: str, queue_path: Path) -> str:
    """Get current status of specific delta."""
    queue = load_delta_queue(queue_path)
    for entry in queue:
        if entry.delta_id == delta_id:
            return entry.status
    return "not_found"
```

## Governance Rules
- P0: Queue operations must be idempotent
- P0: Queue must be append-only ledger (no deletions)
- P0: Dependencies must be validated before application
- P0: Superseding must mark old deltas (not delete them)
- P1: P0 deltas must be applied before P1/P2
- P1: Failed deltas must emit failure receipts

## Anti-Patterns (FORBIDDEN)
- ❌ Deleting queue entries (use status updates instead)
- ❌ Applying deltas with unsatisfied dependencies
- ❌ Ignoring priority ordering
- ❌ Silent failures (all failures must be receipted)
- ❌ Applying superseded deltas
