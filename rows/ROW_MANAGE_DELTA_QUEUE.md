# ROW_MANAGE_DELTA_QUEUE

**Row ID**: ROW_DELTA_QUEUE
**Type**: INTENT_ROUTING
**Authority**: VALIDATED
**Pipeline Activation**: PIPE_DELTA_QUEUE_MANAGEMENT

## Purpose
Route delta queue operations to priority-based delta management pipeline.

## Intent Patterns

```python
INTENT_PATTERNS = [
    "enqueue delta",
    "process delta queue",
    "apply queued deltas",
    "manage delta priority",
    "check delta dependencies",
    "resolve superseding deltas"
]
```

## Row Contract

```python
@dataclass
class ManageDeltaQueueRow:
    row_id: str = "ROW_DELTA_QUEUE"
    intent_patterns: List[str] = field(default_factory=lambda: INTENT_PATTERNS)
    activated_pipeline: str = "PIPE_DELTA_QUEUE_MANAGEMENT"
    required_context: List[str] = field(default_factory=lambda: [
        "os_root",
        "operation",  # "enqueue" | "process" | "query"
        "delta_path"  # Required for "enqueue"
    ])
    output_artifacts: List[str] = field(default_factory=lambda: [
        "queue_receipt",
        "application_results",
        "superseded_deltas"
    ])
```

## Intent Matching

```python
def match_intent(user_message: str) -> float:
    """
    Match user message against delta queue management intent.

    Returns:
        Confidence score 0.0-1.0
    """
    message_lower = user_message.lower()

    # High confidence triggers
    if "delta queue" in message_lower:
        return 0.95

    if "enqueue delta" in message_lower:
        return 0.95

    if "process" in message_lower and "queue" in message_lower:
        return 0.9

    # Medium confidence triggers
    if "delta" in message_lower and "priority" in message_lower:
        return 0.75

    if "delta" in message_lower and "dependencies" in message_lower:
        return 0.75

    # Partial matches
    if "queue" in message_lower and ("apply" in message_lower or "manage" in message_lower):
        return 0.6

    return 0.0
```

## Pipeline Invocation

```python
def invoke_pipeline(ctx: RowContext) -> PipelineResult:
    """
    Invoke delta queue management pipeline.

    Supported operations:
    - enqueue: Add delta to queue with priority/dependencies
    - process: Process all queued deltas in priority order
    - query: Query queue status

    Returns:
        PipelineResult with operation results
    """
    # Validate required context
    ensure(ctx.has("os_root"), "Missing os_root in context")
    ensure(ctx.has("operation"), "Missing operation in context")

    operation = ctx.get("operation")

    # Initialize pipeline
    pipeline = PIPE_DELTA_QUEUE_MANAGEMENT(
        os_root=ctx.get("os_root"),
        operation=operation
    )

    # Operation-specific validation
    if operation == "enqueue":
        ensure(ctx.has("delta_path"), "Missing delta_path for enqueue operation")
        pipeline.set_delta_path(ctx.get("delta_path"))

    # Execute pipeline
    result = pipeline.execute()

    # Package artifacts based on operation
    if operation == "enqueue":
        return PipelineResult(
            status=result.status,
            artifacts={
                "queue_receipt": result.queue_entry_path,
                "superseded_deltas": result.superseded_delta_ids
            },
            metadata={
                "delta_id": result.delta_id,
                "priority": result.priority,
                "dependencies": result.dependencies
            }
        )

    elif operation == "process":
        return PipelineResult(
            status=result.status,
            artifacts={
                "application_results": result.application_results_path
            },
            metadata={
                "deltas_applied": result.deltas_applied,
                "deltas_failed": result.deltas_failed,
                "deltas_skipped": result.deltas_skipped
            }
        )

    elif operation == "query":
        return PipelineResult(
            status=result.status,
            artifacts={},
            metadata={
                "pending_deltas": result.pending_count,
                "failed_deltas": result.failed_count,
                "applied_deltas": result.applied_count
            }
        )

    else:
        raise ValueError(f"Unknown operation: {operation}")
```

## Routing Decision Tree

```
User Intent: "Enqueue delta DELTA_001 with P0 priority"
    │
    ├─> Match confidence: 0.95
    │
    ├─> Activate: PIPE_DELTA_QUEUE_MANAGEMENT
    │
    └─> Required Context:
        ├─> os_root: Path to MetaBlooms OS
        ├─> operation: "enqueue"
        └─> delta_path: Path to delta artifact

User Intent: "Process all queued deltas"
    │
    ├─> Match confidence: 0.9
    │
    ├─> Activate: PIPE_DELTA_QUEUE_MANAGEMENT
    │
    └─> Required Context:
        ├─> os_root: Path to MetaBlooms OS
        └─> operation: "process"
```

## Integration Points

**Upstream Rows**:
- ROW_DEBUG_P0_CRITICAL → Generates deltas for queueing
- ROW_SHIP_WITH_ROLLBACK → Generates deltas from shipping

**Downstream Rows**:
- ROW_APPLY_HEALING_DELTA → Apply selected delta from queue
- ROW_VALIDATE_DELTA_CHAIN → Verify delta application chain
- ROW_UPDATE_REGISTRY → Promote applied deltas

**Segments Used**:
- SEG_DELTA_QUEUE_MANAGEMENT_V1
- SEG_SELF_HEALING_ROLLBACK_V1
- SEG_EXECUTION_TEST_HARNESS_V1

**Pipelines Activated**:
- PIPE_DELTA_QUEUE_MANAGEMENT (primary)
- PIPE_APPLY_DELTA (conditional, for each queued delta)
- PIPE_DETECT_SUPERSEDING (conditional)

## Example Invocation

```python
# User message: "Enqueue delta DELTA_001 with automatic priority detection"

row_context = RowContext(
    os_root=Path("/home/user/metablooms-os"),
    operation="enqueue",
    delta_path=Path("/home/user/deltas/DELTA_001.json")
)

row = ManageDeltaQueueRow()
match_score = row.match_intent("Enqueue delta DELTA_001 with automatic priority detection")
# match_score = 0.95

if match_score > 0.7:
    result = row.invoke_pipeline(row_context)
    # result.status = "ENQUEUED"
    # result.metadata["priority"] = 0  # P0
    # result.metadata["dependencies"] = []
    # result.artifacts["superseded_deltas"] = ["DELTA_000"]
```

## Governance Rules
- P0: Row MUST classify delta priority automatically
- P0: Row MUST detect and mark superseded deltas
- P0: Row MUST respect dependency ordering during processing
- P1: Row SHOULD emit queue receipt for audit
- P1: Row SHOULD validate delta integrity before enqueuing

## Anti-Patterns (FORBIDDEN)
- ❌ Enqueuing delta without priority classification
- ❌ Applying delta with unsatisfied dependencies
- ❌ Ignoring superseding relationships
- ❌ Deleting queue entries (use status updates)
- ❌ Processing out of priority order
