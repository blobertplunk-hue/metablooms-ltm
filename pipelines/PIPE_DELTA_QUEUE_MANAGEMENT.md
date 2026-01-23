# PIPE_DELTA_QUEUE_MANAGEMENT

**Pipeline ID**: PIPE_DELTA_QUEUE_MGMT
**Type**: OPERATIONAL_INFRASTRUCTURE
**Authority**: VALIDATED
**Execution Model**: 5-PHASE (DISCOVER, VALIDATE, CONVERGE, DECIDE, ACT)

## Purpose
Manage delta queue with priority-based processing, dependency resolution, and superseding detection.

## Pipeline Contract

```python
@dataclass
class DeltaQueueManagementPipeline:
    pipeline_id: str = "PIPE_DELTA_QUEUE_MGMT"
    phases: List[str] = field(default_factory=lambda: [
        "DISCOVER",
        "VALIDATE",
        "CONVERGE",
        "DECIDE",
        "ACT"
    ])
    segments_used: List[str] = field(default_factory=lambda: [
        "SEG_DELTA_QUEUE_MANAGEMENT_V1",
        "SEG_SELF_HEALING_ROLLBACK_V1"
    ])
    required_inputs: List[str] = field(default_factory=lambda: [
        "os_root",
        "operation"  # "enqueue" | "process" | "query"
    ])
    output_artifacts: List[str] = field(default_factory=lambda: [
        "queue_receipt",
        "application_results"
    ])
```

## Operations

### Operation 1: ENQUEUE

**Purpose**: Add delta to queue with automatic priority and superseding

#### Phase 0: DISCOVER (Load Delta)

```python
def enqueue_phase_0_discover(os_root: Path, delta_path: Path) -> Delta:
    """
    PHASE 0: DISCOVER - Load delta for enqueuing.

    Flow:
    1. Load delta from path
    2. Parse manifest
    3. Extract targets, dependencies, supersedes
    4. Compute delta hash

    Returns:
        Delta object
    """
    delta_content = read_text(delta_path)
    delta_hash = sha256_text(delta_content)

    delta_manifest = json.loads(delta_content)

    return Delta(
        delta_id=delta_manifest["delta_id"],
        targets=delta_manifest["targets"],
        manifest=delta_manifest,
        artifact_path=delta_path,
        sha256=delta_hash
    )
```

#### Phase 1: VALIDATE (Check Queue State)

```python
def enqueue_phase_1_validate(delta: Delta, os_root: Path) -> QueueState:
    """
    PHASE 1: VALIDATE - Load existing queue state.

    Flow:
    1. Load delta queue from ledger
    2. Load applied deltas set
    3. Validate delta not already in queue
    4. Return current queue state

    Returns:
        QueueState with existing queue entries
    """
    queue_path = os_root / "ledgers" / "deltas" / "delta_queue.jsonl"
    existing_queue = load_delta_queue(queue_path)

    # Check if delta already in queue
    for entry in existing_queue:
        if entry.delta_id == delta.delta_id:
            raise ValueError(f"Delta {delta.delta_id} already in queue")

    applied_deltas = load_applied_deltas_set(os_root)

    return QueueState(
        existing_queue=existing_queue,
        applied_deltas=applied_deltas
    )
```

#### Phase 2: CONVERGE (Classify Priority + Detect Superseding)

```python
def enqueue_phase_2_converge(delta: Delta, queue_state: QueueState) -> DeltaQueueEntry:
    """
    PHASE 2: CONVERGE - Classify priority and detect superseding.

    Flow:
    1. Classify delta priority (P0/P1/P2) based on targets
    2. Extract dependencies from manifest
    3. Detect superseding (explicit + implicit)
    4. Create queue entry

    Returns:
        DeltaQueueEntry with priority and superseding info
    """
    # Classify priority
    priority = classify_delta_priority(delta)

    # Extract dependencies
    dependencies = extract_dependencies(delta)

    # Detect superseding
    supersedes = detect_superseding(delta, queue_state.existing_queue)

    # Create queue entry
    entry = DeltaQueueEntry(
        delta_id=delta.delta_id,
        priority=priority,
        created_utc=utcnow(),
        dependencies=dependencies,
        supersedes=supersedes,
        status="queued",
        targets=delta.targets,
        sha256=delta.sha256
    )

    return entry
```

#### Phase 3: DECIDE (Mark Superseded)

```python
def enqueue_phase_3_decide(entry: DeltaQueueEntry, queue_path: Path) -> List[str]:
    """
    PHASE 3: DECIDE - Mark superseded deltas.

    Flow:
    1. For each delta_id in entry.supersedes:
       a. Update queue entry status to "superseded"
       b. Append status update to queue ledger
    2. Return list of superseded delta IDs

    Returns:
        List of superseded delta IDs
    """
    superseded_ids = []

    for old_delta_id in entry.supersedes:
        mark_superseded(old_delta_id, queue_path)
        superseded_ids.append(old_delta_id)

    return superseded_ids
```

#### Phase 4: ACT (Enqueue Delta)

```python
def enqueue_phase_4_act(entry: DeltaQueueEntry, queue_path: Path) -> Path:
    """
    PHASE 4: ACT - Append delta to queue ledger.

    Flow:
    1. Append entry to queue ledger (JSONL format)
    2. Emit queue receipt
    3. Return receipt path

    Returns:
        Path to queue receipt
    """
    # Append to queue ledger
    append_to_ledger(queue_path, entry)

    # Emit queue receipt
    receipt_path = emit_queue_receipt(entry)

    return receipt_path
```

### Operation 2: PROCESS

**Purpose**: Process all queued deltas in priority order with dependency resolution

#### Phase 0: DISCOVER (Load Queue)

```python
def process_phase_0_discover(os_root: Path) -> Tuple[List[DeltaQueueEntry], Set[str]]:
    """
    PHASE 0: DISCOVER - Load queue and applied deltas.

    Returns:
        Tuple of (queue entries, applied delta IDs)
    """
    queue_path = os_root / "ledgers" / "deltas" / "delta_queue.jsonl"
    queue = load_delta_queue(queue_path)

    applied_deltas = load_applied_deltas_set(os_root)

    return queue, applied_deltas
```

#### Phase 1: VALIDATE (Filter Applicable)

```python
def process_phase_1_validate(
    queue: List[DeltaQueueEntry],
    applied_deltas: Set[str]
) -> List[DeltaQueueEntry]:
    """
    PHASE 1: VALIDATE - Filter to applicable deltas.

    Flow:
    1. Filter to status="queued" entries only
    2. Check dependencies satisfied
    3. Return sorted list (P0 first, then by creation time)

    Returns:
        Sorted list of applicable deltas
    """
    applicable = [e for e in queue if e.status == "queued"]

    # Sort: P0 first, then by creation time
    applicable.sort(key=lambda e: (e.priority, e.created_utc))

    return applicable
```

#### Phase 2: CONVERGE (Dependency Resolution)

```python
def process_phase_2_converge(
    applicable: List[DeltaQueueEntry],
    applied_deltas: Set[str]
) -> List[DeltaQueueEntry]:
    """
    PHASE 2: CONVERGE - Resolve dependencies.

    Flow:
    1. For each delta, check if dependencies satisfied
    2. Build execution plan (dependencies first)
    3. Return ordered list

    Returns:
        Dependency-ordered list of deltas to apply
    """
    execution_plan = []

    for entry in applicable:
        if all_dependencies_satisfied(entry, applied_deltas):
            execution_plan.append(entry)

    return execution_plan
```

#### Phase 3: DECIDE (Application Strategy)

```python
def process_phase_3_decide(execution_plan: List[DeltaQueueEntry]) -> ApplicationStrategy:
    """
    PHASE 3: DECIDE - Determine application strategy.

    Strategies:
    - sequential: Apply deltas one at a time (safe, slow)
    - batch: Apply multiple deltas in transaction (fast, complex)

    Returns:
        ApplicationStrategy
    """
    # For now, always use sequential for safety
    return ApplicationStrategy(
        mode="sequential",
        deltas=execution_plan
    )
```

#### Phase 4: ACT (Apply Deltas)

```python
def process_phase_4_act(
    strategy: ApplicationStrategy,
    os_root: Path,
    queue_path: Path
) -> List[DeltaResult]:
    """
    PHASE 4: ACT - Apply deltas with receipting.

    Flow:
    1. For each delta in execution plan:
       a. Update queue status to "applying"
       b. Apply delta with receipt
       c. Update queue status to "applied" or "failed"
       d. Add to applied_deltas set if successful
    2. Return list of results

    Returns:
        List of DeltaResult for each delta
    """
    results = []
    applied_deltas = load_applied_deltas_set(os_root)

    for entry in strategy.deltas:
        # Update status to "applying"
        update_queue_status(entry.delta_id, "applying", queue_path)

        # Apply delta
        try:
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

### Operation 3: QUERY

**Purpose**: Query queue status and statistics

```python
def query_operation(os_root: Path) -> QueueQueryResult:
    """
    Query delta queue status.

    Returns:
        QueueQueryResult with statistics
    """
    queue_path = os_root / "ledgers" / "deltas" / "delta_queue.jsonl"
    queue = load_delta_queue(queue_path)

    pending = [e for e in queue if e.status == "queued"]
    failed = [e for e in queue if e.status == "failed"]
    applied = [e for e in queue if e.status == "applied"]
    superseded = [e for e in queue if e.status == "superseded"]

    return QueueQueryResult(
        pending_count=len(pending),
        failed_count=len(failed),
        applied_count=len(applied),
        superseded_count=len(superseded),
        pending_deltas=pending,
        failed_deltas=failed
    )
```

## Pipeline Execution Dispatcher

```python
def execute_pipeline(os_root: Path, operation: str, **kwargs) -> PipelineResult:
    """
    Execute delta queue management pipeline.

    Dispatches to appropriate operation handler.

    Returns:
        PipelineResult with operation-specific artifacts
    """
    if operation == "enqueue":
        delta_path = kwargs.get("delta_path")
        ensure(delta_path is not None, "delta_path required for enqueue operation")

        # Execute enqueue operation
        delta = enqueue_phase_0_discover(os_root, delta_path)
        queue_state = enqueue_phase_1_validate(delta, os_root)
        entry = enqueue_phase_2_converge(delta, queue_state)
        superseded = enqueue_phase_3_decide(entry, os_root / "ledgers" / "deltas" / "delta_queue.jsonl")
        receipt_path = enqueue_phase_4_act(entry, os_root / "ledgers" / "deltas" / "delta_queue.jsonl")

        return PipelineResult(
            status="ENQUEUED",
            artifacts={"queue_receipt": receipt_path},
            metadata={
                "delta_id": entry.delta_id,
                "priority": entry.priority,
                "superseded_deltas": superseded
            }
        )

    elif operation == "process":
        # Execute process operation
        queue, applied_deltas = process_phase_0_discover(os_root)
        applicable = process_phase_1_validate(queue, applied_deltas)
        execution_plan = process_phase_2_converge(applicable, applied_deltas)
        strategy = process_phase_3_decide(execution_plan)
        results = process_phase_4_act(strategy, os_root, os_root / "ledgers" / "deltas" / "delta_queue.jsonl")

        return PipelineResult(
            status="PROCESSED",
            artifacts={"application_results": results},
            metadata={
                "deltas_applied": len([r for r in results if r.status == "applied"]),
                "deltas_failed": len([r for r in results if r.status == "failed"]),
                "deltas_skipped": len(applicable) - len(execution_plan)
            }
        )

    elif operation == "query":
        # Execute query operation
        result = query_operation(os_root)

        return PipelineResult(
            status="QUERY_COMPLETE",
            artifacts={},
            metadata={
                "pending_count": result.pending_count,
                "failed_count": result.failed_count,
                "applied_count": result.applied_count,
                "superseded_count": result.superseded_count
            }
        )

    else:
        raise ValueError(f"Unknown operation: {operation}")
```

## Governance Rules
- P0: Pipeline MUST classify delta priority automatically
- P0: Pipeline MUST detect and mark superseded deltas
- P0: Pipeline MUST respect dependency ordering
- P0: Pipeline MUST update queue status atomically
- P1: Pipeline SHOULD emit receipts for all operations
- P1: Pipeline SHOULD use append-only queue ledger

## Anti-Patterns (FORBIDDEN)
- ❌ Enqueuing without priority classification
- ❌ Applying deltas out of priority order
- ❌ Ignoring dependencies
- ❌ Deleting queue entries (use status updates)
- ❌ Applying superseded deltas
