# ROW_APPLY_HEALING_DELTA

**Row ID**: ROW_APPLY_HEALING
**Type**: INTENT_ROUTING
**Authority**: VALIDATED
**Pipeline Activation**: PIPE_HEALING_WITH_ROLLBACK

## Purpose
Route healing delta application requests to rollback-safe healing pipeline.

## Intent Patterns

```python
INTENT_PATTERNS = [
    "apply healing delta",
    "heal with rollback",
    "apply patch with safety",
    "healing with automatic rollback",
    "safe delta application",
    "apply healing with validation"
]
```

## Row Contract

```python
@dataclass
class ApplyHealingDeltaRow:
    row_id: str = "ROW_APPLY_HEALING"
    intent_patterns: List[str] = field(default_factory=lambda: INTENT_PATTERNS)
    activated_pipeline: str = "PIPE_HEALING_WITH_ROLLBACK"
    required_context: List[str] = field(default_factory=lambda: [
        "os_root",
        "healing_delta_path",
        "validation_mode"  # "strict" | "permissive"
    ])
    output_artifacts: List[str] = field(default_factory=lambda: [
        "healing_receipt",
        "rollback_snapshot",
        "validation_results"
    ])
```

## Intent Matching

```python
def match_intent(user_message: str) -> float:
    """
    Match user message against healing delta application intent.

    Returns:
        Confidence score 0.0-1.0
    """
    message_lower = user_message.lower()

    # High confidence triggers
    if "healing delta" in message_lower and "apply" in message_lower:
        return 0.95

    if "healing" in message_lower and "rollback" in message_lower:
        return 0.9

    # Medium confidence triggers
    if "safe delta" in message_lower or "safe patch" in message_lower:
        return 0.75

    if "apply" in message_lower and "validation" in message_lower:
        return 0.7

    # Partial matches
    if "healing" in message_lower:
        return 0.5

    return 0.0
```

## Pipeline Invocation

```python
def invoke_pipeline(ctx: RowContext) -> PipelineResult:
    """
    Invoke healing with rollback pipeline.

    Flow:
    1. Validate required context
    2. Load healing delta
    3. Execute healing with rollback protection
    4. Return healing receipt and artifacts

    Returns:
        PipelineResult with healing status and artifacts
    """
    # Validate required context
    ensure(ctx.has("os_root"), "Missing os_root in context")
    ensure(ctx.has("healing_delta_path"), "Missing healing_delta_path in context")

    # Default validation mode if not specified
    validation_mode = ctx.get("validation_mode", "strict")

    # Initialize pipeline
    pipeline = PIPE_HEALING_WITH_ROLLBACK(
        os_root=ctx.get("os_root"),
        healing_delta_path=ctx.get("healing_delta_path"),
        validation_mode=validation_mode
    )

    # Execute pipeline
    result = pipeline.execute()

    # Package artifacts
    return PipelineResult(
        status=result.status,
        artifacts={
            "healing_receipt": result.healing_receipt_path,
            "rollback_snapshot": result.rollback_snapshot_path,
            "validation_results": result.validation_results_path
        },
        metadata={
            "healing_id": result.healing_id,
            "files_modified": result.files_modified,
            "rollback_performed": result.rollback_performed,
            "healing_type": result.healing_type
        }
    )
```

## Routing Decision Tree

```
User Intent: "Apply healing delta with automatic rollback"
    │
    ├─> Match confidence: 0.9
    │
    ├─> Activate: PIPE_HEALING_WITH_ROLLBACK
    │
    └─> Required Context:
        ├─> os_root: Path to MetaBlooms OS
        ├─> healing_delta_path: Path to healing delta artifact
        └─> validation_mode: "strict" | "permissive"
```

## Integration Points

**Upstream Rows**:
- ROW_DEBUG_P0_CRITICAL → Generates healing deltas
- ROW_ENQUEUE_DELTA → Selects delta from queue

**Downstream Rows**:
- ROW_VALIDATE_HEALING_CHAIN → Verify receipt chain
- ROW_RUN_TESTS → Verify healing didn't break system
- ROW_UPDATE_REGISTRY → Promote healing to registry

**Segments Used**:
- SEG_SELF_HEALING_ROLLBACK_V1
- SEG_HEALING_RECEIPT_CHAIN_V1
- SEG_EXECUTION_TEST_HARNESS_V1

**Pipelines Activated**:
- PIPE_HEALING_WITH_ROLLBACK (primary)
- PIPE_VALIDATE_CHAIN (conditional)
- PIPE_RUN_TESTS (conditional)

## Example Invocation

```python
# User message: "Apply healing delta HEAL_001 with rollback protection"

row_context = RowContext(
    os_root=Path("/home/user/metablooms-os"),
    healing_delta_path=Path("/home/user/deltas/HEAL_001.json"),
    validation_mode="strict"
)

row = ApplyHealingDeltaRow()
match_score = row.match_intent("Apply healing delta HEAL_001 with rollback protection")
# match_score = 0.95

if match_score > 0.7:
    result = row.invoke_pipeline(row_context)
    # result.status = "APPLIED_SUCCESSFULLY" | "ROLLED_BACK" | "FAILED"
    # result.metadata["rollback_performed"] = True/False
```

## Governance Rules
- P0: Row MUST ensure rollback snapshot created before healing
- P0: Row MUST rollback on postcondition failure
- P0: Row MUST emit healing receipt regardless of outcome
- P1: Row SHOULD validate healing chain after application
- P1: Row SHOULD trigger downstream testing

## Anti-Patterns (FORBIDDEN)
- ❌ Applying healing without rollback snapshot
- ❌ Ignoring postcondition failures
- ❌ Skipping healing receipt emission
- ❌ Applying healing without precondition validation
- ❌ Manual rollback instead of automatic
