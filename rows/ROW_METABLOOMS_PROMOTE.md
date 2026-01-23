# ROW_METABLOOMS_PROMOTE

**Row ID**: ROW_MB_PROMOTE
**Type**: INTENT_ROUTING
**Authority**: PRODUCTION_IMPLEMENTATION
**Pipeline Activation**: PIPE_METABLOOMS_PROMOTION

## Purpose
Route artifact promotion requests to the enforced promotion gate pipeline.

## Intent Patterns

```python
INTENT_PATTERNS = [
    "promote to canonical",
    "promote to trusted",
    "run promotion gate",
    "promote artifact",
    "canonical promotion"
]
```

## Row Contract

```python
@dataclass
class MetaBloomsPromoteRow:
    row_id: str = "ROW_MB_PROMOTE"
    intent_patterns: List[str] = field(default_factory=lambda: INTENT_PATTERNS)
    activated_pipeline: str = "PIPE_METABLOOMS_PROMOTION"
    required_context: List[str] = field(default_factory=lambda: [
        "os_root",
        "candidate_path",
        "promotion_mode"  # "CANONICAL" | "TRUSTED" | "EXPERIMENTAL"
    ])
    output_artifacts: List[str] = field(default_factory=lambda: [
        "evidence_pack",
        "promotion_receipt",
        "promoted_artifact_path"
    ])
```

## Intent Matching

```python
def match_intent(user_message: str) -> float:
    """
    Match user message against promotion intent.

    Returns:
        Confidence score 0.0-1.0
    """
    message_lower = user_message.lower()

    # High confidence triggers
    if "promote" in message_lower and "canonical" in message_lower:
        return 0.95

    if "promotion gate" in message_lower:
        return 0.95

    # Medium confidence triggers
    if "promote" in message_lower and ("trusted" in message_lower or "experimental" in message_lower):
        return 0.85

    if "promote artifact" in message_lower:
        return 0.8

    # Partial matches
    if "promote" in message_lower:
        return 0.6

    return 0.0
```

## Pipeline Invocation

```python
def invoke_pipeline(ctx: RowContext) -> PipelineResult:
    """
    Invoke MetaBlooms promotion pipeline.

    Flow:
    1. Validate required context
    2. Resolve promotion mode
    3. Execute enforced promotion gate:
       - Internal SEE verification
       - External items validation
       - MMD anomaly detection
       - Evidence pack generation
       - Decision enforcement
    4. If allowed, copy to registry
    5. Return promotion result

    Returns:
        PipelineResult with promotion status

    Raises:
        PromotionBlocked: If gate rejects
    """
    # Validate required context
    ensure(ctx.has("os_root"), "Missing os_root in context")
    ensure(ctx.has("candidate_path"), "Missing candidate_path in context")
    ensure(ctx.has("promotion_mode"), "Missing promotion_mode in context")

    promotion_mode = ctx.get("promotion_mode")
    if promotion_mode not in ["CANONICAL", "TRUSTED", "EXPERIMENTAL"]:
        raise ValueError(f"Invalid promotion mode: {promotion_mode}")

    # Initialize pipeline
    pipeline = PIPE_METABLOOMS_PROMOTION(
        os_root=ctx.get("os_root"),
        candidate_path=ctx.get("candidate_path"),
        promotion_mode=promotion_mode
    )

    # Execute pipeline
    result = pipeline.execute()

    # Package artifacts
    return PipelineResult(
        status=result.status,
        artifacts={
            "evidence_pack": result.evidence_pack_path,
            "promotion_receipt": result.promotion_receipt_path,
            "promoted_artifact_path": result.promoted_artifact_path
        },
        metadata={
            "promotion_mode": promotion_mode,
            "see_internal_passed": result.see_internal_passed,
            "external_items_count": result.external_items_count,
            "mmd_anomalies_count": result.mmd_anomalies_count
        }
    )
```

## Routing Decision Tree

```
User Intent: "Promote artifact to canonical registry"
    │
    ├─> Match confidence: 0.95
    │
    ├─> Activate: PIPE_METABLOOMS_PROMOTION
    │
    └─> Required Context:
        ├─> os_root: Path to MetaBlooms OS
        ├─> candidate_path: Path to candidate artifact
        └─> promotion_mode: CANONICAL | TRUSTED | EXPERIMENTAL
```

## Integration Points

**Upstream Rows**:
- ROW_MB_BOOT → Boot completes before promotion
- ROW_MB_RUN_GOVERNANCE → Governance loop generates candidates

**Downstream Rows**:
- ROW_MB_REGISTRY_UPDATE → Update registry index after promotion

**Segments Used**:
- SEG_METABLOOMS_PROMOTION_GATE_V1
- SEG_METABLOOMS_EVIDENCE_STORE_V1

**Pipelines Activated**:
- PIPE_METABLOOMS_PROMOTION (primary)

## Governance Rules
- P0: Row MUST run enforced promotion gate
- P0: Row MUST generate evidence pack
- P0: Row MUST be fail-closed (block on rejection)
- P1: Row SHOULD validate candidate integrity before promotion
- P1: Row SHOULD emit promotion receipt

## Anti-Patterns (FORBIDDEN)
- ❌ Bypassing promotion gate
- ❌ Promoting without evidence pack
- ❌ Ignoring MMD anomalies in CANONICAL mode
- ❌ Promoting with insufficient external items
- ❌ Manual registry updates without gate
