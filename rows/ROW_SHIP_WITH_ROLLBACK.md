# ROW_SHIP_WITH_ROLLBACK

**Row ID**: ROW_SHIP_ROLLBACK
**Type**: INTENT_ROUTING
**Authority**: VALIDATED
**Pipeline Activation**: PIPE_SHIP_WITH_ROLLBACK

## Purpose
Route shipping operations to rollback-safe shipping pipeline with conflict detection.

## Intent Patterns

```python
INTENT_PATTERNS = [
    "ship with rollback",
    "safe shipping",
    "ship with conflict detection",
    "atomic shipping",
    "ship with validation",
    "rollback-safe deployment"
]
```

## Row Contract

```python
@dataclass
class ShipWithRollbackRow:
    row_id: str = "ROW_SHIP_ROLLBACK"
    intent_patterns: List[str] = field(default_factory=lambda: INTENT_PATTERNS)
    activated_pipeline: str = "PIPE_SHIP_WITH_ROLLBACK"
    required_context: List[str] = field(default_factory=lambda: [
        "os_root",
        "ship_artifact_path",
        "conflict_policy",  # "reject" | "stage" | "force"
        "validation_gates"  # List of gate names to run
    ])
    output_artifacts: List[str] = field(default_factory=lambda: [
        "ship_receipt",
        "conflict_report",
        "rollback_snapshot",
        "validation_results"
    ])
```

## Intent Matching

```python
def match_intent(user_message: str) -> float:
    """
    Match user message against shipping with rollback intent.

    Returns:
        Confidence score 0.0-1.0
    """
    message_lower = user_message.lower()

    # High confidence triggers
    if "ship" in message_lower and "rollback" in message_lower:
        return 0.95

    if "atomic ship" in message_lower or "safe ship" in message_lower:
        return 0.9

    # Medium confidence triggers
    if "ship" in message_lower and "conflict" in message_lower:
        return 0.8

    if "ship" in message_lower and "validation" in message_lower:
        return 0.75

    # Partial matches
    if "deploy" in message_lower and "safe" in message_lower:
        return 0.6

    return 0.0
```

## Pipeline Invocation

```python
def invoke_pipeline(ctx: RowContext) -> PipelineResult:
    """
    Invoke rollback-safe shipping pipeline.

    Flow:
    1. Validate required context
    2. Load ship artifact
    3. Detect conflicts with existing state
    4. Stage changes to temporary location
    5. Run validation gates
    6. If validation passes → commit changes
    7. If validation fails → automatic rollback
    8. Emit ship receipt

    Returns:
        PipelineResult with shipping status and artifacts
    """
    # Validate required context
    ensure(ctx.has("os_root"), "Missing os_root in context")
    ensure(ctx.has("ship_artifact_path"), "Missing ship_artifact_path in context")

    # Default policies if not specified
    conflict_policy = ctx.get("conflict_policy", "reject")
    validation_gates = ctx.get("validation_gates", [
        "gate_receipt_hash_chain",
        "gate_snapshot_integrity"
    ])

    # Initialize pipeline
    pipeline = PIPE_SHIP_WITH_ROLLBACK(
        os_root=ctx.get("os_root"),
        ship_artifact_path=ctx.get("ship_artifact_path"),
        conflict_policy=conflict_policy,
        validation_gates=validation_gates
    )

    # Execute pipeline
    result = pipeline.execute()

    # Package artifacts
    return PipelineResult(
        status=result.status,
        artifacts={
            "ship_receipt": result.ship_receipt_path,
            "conflict_report": result.conflict_report_path,
            "rollback_snapshot": result.rollback_snapshot_path,
            "validation_results": result.validation_results_path
        },
        metadata={
            "ship_id": result.ship_id,
            "conflicts_detected": result.conflicts_detected,
            "conflicts_resolved": result.conflicts_resolved,
            "rollback_performed": result.rollback_performed,
            "gates_passed": result.gates_passed,
            "gates_failed": result.gates_failed
        }
    )
```

## Routing Decision Tree

```
User Intent: "Ship artifact with automatic rollback on validation failure"
    │
    ├─> Match confidence: 0.95
    │
    ├─> Activate: PIPE_SHIP_WITH_ROLLBACK
    │
    └─> Required Context:
        ├─> os_root: Path to MetaBlooms OS
        ├─> ship_artifact_path: Path to ship artifact
        ├─> conflict_policy: "reject" | "stage" | "force"
        └─> validation_gates: List of gates to run
```

## Integration Points

**Upstream Rows**:
- ROW_DEBUG_P0_CRITICAL → Generates ship artifacts from patches
- ROW_MANAGE_DELTA_QUEUE → Generates ship artifacts from deltas
- ROW_CREATE_BUNDLE → Generates ship artifacts from bundles

**Downstream Rows**:
- ROW_VALIDATE_SHIP_CHAIN → Verify ship receipt chain
- ROW_RUN_TESTS → Verify shipped changes work
- ROW_UPDATE_REGISTRY → Promote shipped changes to registry
- ROW_CREATE_PR → Create PR for shipped changes

**Segments Used**:
- SEG_ROLLBACK_SAFE_SHIPPING_V1
- SEG_HEALING_RECEIPT_CHAIN_V1
- SEG_EXECUTION_TEST_HARNESS_V1

**Pipelines Activated**:
- PIPE_SHIP_WITH_ROLLBACK (primary)
- PIPE_DETECT_CONFLICTS (sub-pipeline)
- PIPE_RUN_VALIDATION_GATES (sub-pipeline)
- PIPE_COMMIT_OR_ROLLBACK (sub-pipeline)

## Conflict Policies

```python
CONFLICT_POLICIES = {
    "reject": "Reject shipping if any conflicts detected",
    "stage": "Stage conflicting files for manual resolution",
    "force": "Force overwrite conflicting files (DANGEROUS)"
}
```

## Example Invocation

```python
# User message: "Ship artifact SHIP_001 with conflict detection and validation"

row_context = RowContext(
    os_root=Path("/home/user/metablooms-os"),
    ship_artifact_path=Path("/home/user/ships/SHIP_001.zip"),
    conflict_policy="reject",
    validation_gates=[
        "gate_receipt_hash_chain",
        "gate_snapshot_integrity",
        "gate_turn_index_continuity"
    ]
)

row = ShipWithRollbackRow()
match_score = row.match_intent("Ship artifact SHIP_001 with conflict detection and validation")
# match_score = 0.8

if match_score > 0.7:
    result = row.invoke_pipeline(row_context)
    # result.status = "SHIPPED_SUCCESSFULLY" | "ROLLED_BACK" | "CONFLICTS_DETECTED"
    # result.metadata["conflicts_detected"] = 0
    # result.metadata["rollback_performed"] = False
    # result.metadata["gates_passed"] = 3
```

## Governance Rules
- P0: Row MUST detect conflicts before committing changes
- P0: Row MUST create rollback snapshot before modification
- P0: Row MUST rollback on validation failure
- P0: Row MUST emit ship receipt regardless of outcome
- P1: Row SHOULD run validation gates before commit
- P1: Row SHOULD support configurable conflict policies

## Anti-Patterns (FORBIDDEN)
- ❌ Shipping without conflict detection
- ❌ Committing changes without rollback snapshot
- ❌ Ignoring validation gate failures
- ❌ Using "force" conflict policy without explicit user approval
- ❌ Skipping ship receipt emission
- ❌ Manual rollback instead of automatic
