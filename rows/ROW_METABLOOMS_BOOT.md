# ROW_METABLOOMS_BOOT

**Row ID**: ROW_MB_BOOT
**Type**: INTENT_ROUTING
**Authority**: PRODUCTION_IMPLEMENTATION
**Pipeline Activation**: PIPE_METABLOOMS_BOOT_SEQUENCE

## Purpose
Route MetaBlooms OS boot requests to the full boot sequence pipeline with preflight gates, runtime initialization, and state rehydration.

## Intent Patterns

```python
INTENT_PATTERNS = [
    "boot metablooms os",
    "start metablooms turn",
    "initialize metablooms runtime",
    "run metablooms boot sequence"
]
```

## Row Contract

```python
@dataclass
class MetaBloomsBootRow:
    row_id: str = "ROW_MB_BOOT"
    intent_patterns: List[str] = field(default_factory=lambda: INTENT_PATTERNS)
    activated_pipeline: str = "PIPE_METABLOOMS_BOOT_SEQUENCE"
    required_context: List[str] = field(default_factory=lambda: [
        "os_root",
        "turn_id"
    ])
    output_artifacts: List[str] = field(default_factory=lambda: [
        "boot_receipt",
        "turn_lock",
        "rehydrate_receipt",
        "preflight_receipts"
    ])
```

## Intent Matching

```python
def match_intent(user_message: str) -> float:
    """
    Match user message against MetaBlooms OS boot intent.

    Returns:
        Confidence score 0.0-1.0
    """
    message_lower = user_message.lower()

    # High confidence triggers
    if "boot" in message_lower and "metablooms" in message_lower:
        return 0.95

    if "start" in message_lower and "turn" in message_lower:
        return 0.9

    # Medium confidence triggers
    if "initialize" in message_lower and "runtime" in message_lower:
        return 0.75

    # Partial matches
    if "metablooms" in message_lower:
        return 0.5

    return 0.0
```

## Pipeline Invocation

```python
def invoke_pipeline(ctx: RowContext) -> PipelineResult:
    """
    Invoke MetaBlooms OS boot sequence pipeline.

    Flow:
    1. Validate required context
    2. Execute boot pipeline:
       - Genesis check
       - Turn lock acquisition
       - Turn index allocation
       - State rehydration
       - Preflight gates (24 gates)
       - Runtime initialization
    3. Return boot result with receipts

    Returns:
        PipelineResult with boot status and artifacts
    """
    # Validate required context
    ensure(ctx.has("os_root"), "Missing os_root in context")
    ensure(ctx.has("turn_id"), "Missing turn_id in context")

    # Initialize pipeline
    pipeline = PIPE_METABLOOMS_BOOT_SEQUENCE(
        os_root=ctx.get("os_root"),
        turn_id=ctx.get("turn_id")
    )

    # Execute pipeline
    result = pipeline.execute()

    # Package artifacts
    return PipelineResult(
        status=result.status,
        artifacts={
            "boot_receipt": result.boot_receipt_path,
            "turn_lock": result.turn_lock_path,
            "rehydrate_receipt": result.rehydrate_receipt_path,
            "preflight_receipts": result.preflight_receipts_paths
        },
        metadata={
            "turn_index": result.turn_index,
            "gates_passed": result.gates_passed,
            "boot_duration_ms": result.boot_duration_ms
        }
    )
```

## Routing Decision Tree

```
User Intent: "Boot MetaBlooms OS for turn TURN_001"
    │
    ├─> Match confidence: 0.95
    │
    ├─> Activate: PIPE_METABLOOMS_BOOT_SEQUENCE
    │
    └─> Required Context:
        ├─> os_root: Path to MetaBlooms OS root
        └─> turn_id: Unique turn identifier
```

## Integration Points

**Upstream Rows**: None (boot is terminal entry point)

**Downstream Rows**:
- ROW_MB_EXECUTE_TURN → Execute turn logic after boot
- ROW_MB_RUN_GOVERNANCE → Run governance loop after boot
- ROW_MB_PROMOTE → Promote artifacts after turn

**Segments Used**:
- SEG_METABLOOMS_PREFLIGHT_GATES_V1
- SEG_METABLOOMS_RUNTIME_V1
- SEG_METABLOOMS_EVIDENCE_STORE_V1

**Pipelines Activated**:
- PIPE_METABLOOMS_BOOT_SEQUENCE (primary)

## Example Invocation

```python
# User message: "Boot MetaBlooms OS for turn TURN_001"

row_context = RowContext(
    os_root=Path("/mnt/data/metablooms_os"),
    turn_id="TURN_001"
)

row = MetaBloomsBootRow()
match_score = row.match_intent("Boot MetaBlooms OS for turn TURN_001")
# match_score = 0.95

if match_score > 0.7:
    result = row.invoke_pipeline(row_context)
    # result.status = "BOOT_SUCCESS"
    # result.metadata["turn_index"] = 42
    # result.metadata["gates_passed"] = 24
```

## Governance Rules
- P0: Row MUST acquire turn lock before boot
- P0: Row MUST run all preflight gates
- P0: Row MUST rehydrate state from prior turn (except genesis)
- P0: Row MUST emit boot receipt
- P1: Row SHOULD validate turn_id format
- P1: Row SHOULD emit receipts for each boot phase

## Anti-Patterns (FORBIDDEN)
- ❌ Booting without turn lock
- ❌ Skipping preflight gates
- ❌ Bypassing state rehydration
- ❌ Starting turn without boot receipt
- ❌ Concurrent boots without lock
