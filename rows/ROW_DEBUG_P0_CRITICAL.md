# ROW_DEBUG_P0_CRITICAL

**Row ID**: ROW_DEBUG_P0
**Type**: INTENT_ROUTING
**Authority**: VALIDATED
**Pipeline Activation**: PIPE_SEE_MMD_ECL_DEBUG

## Purpose
Route P0 CRITICAL debugging requests to governed debugging pipeline.

## Intent Patterns

```python
INTENT_PATTERNS = [
    "debug P0 CRITICAL bugs",
    "fix P0 CRITICAL issues",
    "run SEE/MMD/ECL protocol",
    "systematic P0 debugging",
    "governed debugging session",
    "audit and patch P0 bugs"
]
```

## Row Contract

```python
@dataclass
class DebugP0CriticalRow:
    row_id: str = "ROW_DEBUG_P0"
    intent_patterns: List[str] = field(default_factory=lambda: INTENT_PATTERNS)
    activated_pipeline: str = "PIPE_SEE_MMD_ECL_DEBUG"
    required_context: List[str] = field(default_factory=lambda: [
        "os_root",
        "target_codebase",
        "scope_definition"
    ])
    output_artifacts: List[str] = field(default_factory=lambda: [
        "governance_bundle",
        "patch_receipts",
        "ecl_final_status"
    ])
```

## Intent Matching

```python
def match_intent(user_message: str) -> float:
    """
    Match user message against debug P0 intent patterns.

    Returns:
        Confidence score 0.0-1.0
    """
    message_lower = user_message.lower()

    # High confidence triggers
    if "p0 critical" in message_lower and any(kw in message_lower for kw in ["debug", "fix", "patch"]):
        return 0.95

    if "see/mmd/ecl" in message_lower or "see mmd ecl" in message_lower:
        return 0.95

    # Medium confidence triggers
    if "systematic debug" in message_lower:
        return 0.75

    if "governed debug" in message_lower:
        return 0.75

    # Partial matches
    if "p0" in message_lower and "bug" in message_lower:
        return 0.6

    return 0.0
```

## Pipeline Invocation

```python
def invoke_pipeline(ctx: RowContext) -> PipelineResult:
    """
    Invoke SEE/MMD/ECL debugging pipeline.

    Flow:
    1. Validate required context
    2. Initialize pipeline with scope
    3. Execute 7-phase SEE/MMD/ECL protocol
    4. Return governance bundle

    Returns:
        PipelineResult with artifacts and status
    """
    # Validate required context
    ensure(ctx.has("os_root"), "Missing os_root in context")
    ensure(ctx.has("target_codebase"), "Missing target_codebase in context")
    ensure(ctx.has("scope_definition"), "Missing scope_definition in context")

    # Initialize pipeline
    pipeline = PIPE_SEE_MMD_ECL_DEBUG(
        os_root=ctx.get("os_root"),
        target_codebase=ctx.get("target_codebase"),
        scope=ctx.get("scope_definition")
    )

    # Execute pipeline
    result = pipeline.execute()

    # Package artifacts
    return PipelineResult(
        status=result.status,
        artifacts={
            "governance_bundle": result.governance_bundle_path,
            "patch_receipts": result.patch_receipt_paths,
            "ecl_final_status": result.ecl_status
        },
        metadata={
            "bugs_found": result.bugs_found,
            "bugs_resolved": result.bugs_resolved,
            "proof_class": result.proof_class
        }
    )
```

## Routing Decision Tree

```
User Intent: "Debug P0 CRITICAL bugs using SEE/MMD/ECL"
    │
    ├─> Match confidence: 0.95
    │
    ├─> Activate: PIPE_SEE_MMD_ECL_DEBUG
    │
    └─> Required Context:
        ├─> os_root: Path to MetaBlooms OS
        ├─> target_codebase: Path to code to debug
        └─> scope_definition: P0 scope (e.g., "boot-critical", "security")
```

## Integration Points

**Upstream Rows**: None (terminal intent)

**Downstream Rows**:
- ROW_APPLY_HEALING → If healing deltas generated
- ROW_CREATE_PR → If patches ready for merge
- ROW_RUN_TESTS → If runtime tests needed

**Segments Used**:
- SEG_P0_DEBUG_PROTOCOL_V1
- SEG_EXECUTION_TEST_HARNESS_V1
- SEG_GOVERNANCE_BUNDLE_V1

**Pipelines Activated**:
- PIPE_SEE_MMD_ECL_DEBUG (primary)
- PIPE_APPLY_PATCHES (conditional)
- PIPE_GENERATE_BUNDLE (always)

## Example Invocation

```python
# User message: "Debug P0 CRITICAL bugs in MetaBlooms OS"

row_context = RowContext(
    os_root=Path("/home/user/metablooms-os"),
    target_codebase=Path("/home/user/metablooms-os"),
    scope_definition="P0_CRITICAL"
)

row = DebugP0CriticalRow()
match_score = row.match_intent("Debug P0 CRITICAL bugs in MetaBlooms OS")
# match_score = 0.95

if match_score > 0.7:
    result = row.invoke_pipeline(row_context)
    # result.status = "COMPLETED"
    # result.artifacts["governance_bundle"] = "governance/bundles/BUNDLE_001/BUNDLE_001.json"
```

## Governance Rules
- P0: Row MUST validate required context before pipeline invocation
- P0: Row MUST return governance bundle on completion
- P1: Row MUST record intent match confidence
- P1: Row SHOULD route to downstream rows based on results

## Anti-Patterns (FORBIDDEN)
- ❌ Invoking pipeline without required context
- ❌ Silently failing on low confidence match
- ❌ Skipping governance bundle generation
- ❌ Returning success when bugs remain unresolved
