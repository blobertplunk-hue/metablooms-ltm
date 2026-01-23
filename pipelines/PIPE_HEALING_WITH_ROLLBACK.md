# PIPE_HEALING_WITH_ROLLBACK

**Pipeline ID**: PIPE_HEALING_WITH_ROLLBACK
**Type**: HEALING_PROTOCOL
**Authority**: VALIDATED
**Execution Model**: 5-PHASE (DISCOVER, VALIDATE, CONVERGE, DECIDE, ACT)

## Purpose
Apply healing deltas with automatic rollback on validation failure.

## Pipeline Contract

```python
@dataclass
class HealingWithRollbackPipeline:
    pipeline_id: str = "PIPE_HEALING_WITH_ROLLBACK"
    phases: List[str] = field(default_factory=lambda: [
        "DISCOVER",
        "VALIDATE",
        "CONVERGE",
        "DECIDE",
        "ACT"
    ])
    segments_used: List[str] = field(default_factory=lambda: [
        "SEG_SELF_HEALING_ROLLBACK_V1",
        "SEG_HEALING_RECEIPT_CHAIN_V1",
        "SEG_EXECUTION_TEST_HARNESS_V1"
    ])
    required_inputs: List[str] = field(default_factory=lambda: [
        "os_root",
        "healing_delta_path",
        "validation_mode"
    ])
    output_artifacts: List[str] = field(default_factory=lambda: [
        "healing_receipt",
        "rollback_snapshot",
        "validation_results"
    ])
```

## Phase 0: DISCOVER (Load Healing Delta)

**Purpose**: Load and parse healing delta artifact

**Pipe Segments**:
- INGEST: Load healing delta from path
- NORMALIZE: Parse delta manifest and preconditions
- VALIDATE: Verify delta structure and integrity

**Execution**:
```python
def phase_0_discover(os_root: Path, healing_delta_path: Path) -> HealingDelta:
    """
    PHASE 0: DISCOVER - Load healing delta.

    Flow:
    1. Load delta from path
    2. Verify SHA256 hash
    3. Parse manifest (preconditions, postconditions, targets)
    4. Validate delta structure

    Returns:
        HealingDelta object
    """
    # Load delta
    delta_content = read_text(healing_delta_path)
    delta_hash = sha256_text(delta_content)

    delta_manifest = json.loads(delta_content)

    # Validate structure
    required_fields = ["delta_id", "healing_type", "target_files", "preconditions", "postconditions"]
    for field in required_fields:
        ensure(field in delta_manifest, f"Missing required field: {field}")

    # Build HealingDelta object
    healing_delta = HealingDelta(
        delta_id=delta_manifest["delta_id"],
        healing_type=delta_manifest["healing_type"],
        target_files=delta_manifest["target_files"],
        preconditions=delta_manifest.get("preconditions", []),
        postconditions=delta_manifest.get("postconditions", []),
        rollback_snapshot=None,  # Will be created in ACT phase
        priority=classify_delta_priority(delta_manifest),
        created_utc=delta_manifest.get("created_utc", utcnow()),
        sha256=delta_hash
    )

    return healing_delta
```

## Phase 1: VALIDATE (Precondition Check)

**Purpose**: Validate all preconditions before applying healing

**Pipe Segments**:
- MAP: Map preconditions to validation functions
- EXECUTE: Run each precondition validator
- VERIFY: Ensure all preconditions satisfied

**Execution**:
```python
def phase_1_validate(healing_delta: HealingDelta, os_root: Path) -> PreconditionValidationResult:
    """
    PHASE 1: VALIDATE - Check all preconditions.

    Flow:
    1. For each precondition in healing delta:
       a. Run appropriate validator (file_exists, file_hash, etc.)
       b. Record pass/fail status
    2. If any precondition fails → return FAILED status
    3. If all pass → proceed to CONVERGE

    Returns:
        PreconditionValidationResult with validation status
    """
    validation_results = []

    for precond in healing_delta.preconditions:
        try:
            validate_precondition(os_root, precond)
            validation_results.append({
                "precondition": precond,
                "status": "PASSED"
            })
        except PreconditionFailure as e:
            validation_results.append({
                "precondition": precond,
                "status": "FAILED",
                "reason": str(e)
            })

    all_passed = all(r["status"] == "PASSED" for r in validation_results)

    return PreconditionValidationResult(
        all_passed=all_passed,
        results=validation_results
    )


def validate_precondition(os_root: Path, precond: Dict) -> None:
    """
    Validate single precondition.

    Supported types:
    - file_exists
    - file_hash
    - delta_applied
    - registry_version
    - gate_pass

    Raises:
        PreconditionFailure if validation fails
    """
    # (Implementation from SEG_SELF_HEALING_ROLLBACK_V1)
    # See segment for full implementation
    pass
```

## Phase 2: CONVERGE (Create Rollback Snapshot)

**Purpose**: Create rollback snapshot before applying healing

**Pipe Segments**:
- NORMALIZE: Normalize target file paths
- VALIDATE: Verify target files exist (if modifying existing)
- LEDGER: Create rollback snapshot with file backups

**Execution**:
```python
def phase_2_converge(healing_delta: HealingDelta, os_root: Path) -> Path:
    """
    PHASE 2: CONVERGE - Create rollback snapshot.

    Flow:
    1. For each target file:
       a. If exists, backup content
       b. If not exists, mark as "to be deleted on rollback"
    2. Backup registry state
    3. Write rollback manifest

    Returns:
        Path to rollback snapshot manifest
    """
    rollback_snapshot_path = create_rollback_snapshot(
        os_root=os_root,
        healing_id=healing_delta.delta_id,
        target_files=healing_delta.target_files
    )

    # Update healing delta with rollback snapshot reference
    healing_delta.rollback_snapshot = str(rollback_snapshot_path)

    return rollback_snapshot_path
```

## Phase 3: DECIDE (Healing Strategy)

**Purpose**: Determine healing application strategy

**Pipe Segments**:
- MAP: Map healing type to application strategy
- EXECUTE: Generate application plan
- VERIFY: Validate application plan

**Execution**:
```python
def phase_3_decide(healing_delta: HealingDelta, os_root: Path) -> HealingApplicationPlan:
    """
    PHASE 3: DECIDE - Plan healing application.

    Healing types:
    - PATCH: Apply diff to existing files
    - PROMOTE: Promote files from staging to production
    - ROLLBACK: Restore files from snapshot

    Returns:
        HealingApplicationPlan with strategy
    """
    if healing_delta.healing_type == "PATCH":
        strategy = "apply_diffs"
        diffs = extract_diffs_from_delta(healing_delta)

    elif healing_delta.healing_type == "PROMOTE":
        strategy = "copy_from_staging"
        source_files = extract_staging_files(healing_delta)

    elif healing_delta.healing_type == "ROLLBACK":
        strategy = "restore_from_snapshot"
        snapshot_ref = extract_snapshot_reference(healing_delta)

    else:
        raise ValueError(f"Unknown healing type: {healing_delta.healing_type}")

    return HealingApplicationPlan(
        strategy=strategy,
        healing_type=healing_delta.healing_type,
        target_files=healing_delta.target_files,
        application_steps=generate_application_steps(strategy, healing_delta)
    )
```

## Phase 4: ACT (Apply + Validate + Rollback on Failure)

**Purpose**: Apply healing, validate postconditions, rollback if validation fails

**Pipe Segments**:
- EXECUTE: Apply healing changes
- VERIFY: Validate postconditions
- LEDGER: Emit healing receipt
- EMIT: Automatic rollback if verification fails

**Execution**:
```python
def phase_4_act(
    healing_delta: HealingDelta,
    application_plan: HealingApplicationPlan,
    rollback_snapshot_path: Path,
    os_root: Path
) -> HealingResult:
    """
    PHASE 4: ACT - Apply healing with rollback protection.

    Flow:
    1. Apply healing changes according to plan
    2. Validate postconditions
    3. If postconditions pass:
       a. Emit healing success receipt
       b. Append to healing receipt chain
       c. Return success
    4. If postconditions fail:
       a. Automatic rollback from snapshot
       b. Emit healing failure receipt
       c. Return failure with rollback performed

    Returns:
        HealingResult with status and rollback info
    """
    # Step 1: Apply healing changes
    try:
        apply_delta_changes(os_root, healing_delta)
    except Exception as e:
        # Rollback on application failure
        restore_from_snapshot(os_root, rollback_snapshot_path)

        return HealingResult(
            healing_id=healing_delta.delta_id,
            status="APPLICATION_FAILED",
            reason=str(e),
            rollback_performed=True,
            rollback_snapshot=str(rollback_snapshot_path)
        )

    # Step 2: Validate postconditions
    try:
        validate_postconditions(os_root, healing_delta.postconditions)
    except PostconditionFailure as e:
        # Automatic rollback on validation failure
        restore_from_snapshot(os_root, rollback_snapshot_path)

        emit_healing_failure_receipt(
            os_root=os_root,
            healing_id=healing_delta.delta_id,
            reason=f"Postcondition failed: {e}",
            rollback_performed=True
        )

        return HealingResult(
            healing_id=healing_delta.delta_id,
            status="POSTCONDITION_FAILED_ROLLED_BACK",
            reason=str(e),
            rollback_performed=True,
            rollback_snapshot=str(rollback_snapshot_path)
        )

    # Step 3: Success - emit healing receipt and append to chain
    receipt_path = emit_healing_success_receipt(
        os_root=os_root,
        healing_delta=healing_delta,
        rollback_snapshot=rollback_snapshot_path
    )

    append_healing_receipt(
        os_root=os_root,
        healing_id=healing_delta.delta_id,
        healing_type=healing_delta.healing_type,
        status="APPLIED",
        target_files=healing_delta.target_files,
        rollback_performed=False
    )

    return HealingResult(
        healing_id=healing_delta.delta_id,
        status="APPLIED_SUCCESSFULLY",
        files_modified=healing_delta.target_files,
        receipt_path=receipt_path,
        rollback_performed=False
    )
```

## Pipeline Execution

```python
def execute_pipeline(
    os_root: Path,
    healing_delta_path: Path,
    validation_mode: str = "strict"
) -> PipelineResult:
    """
    Execute complete healing with rollback pipeline.

    Returns:
        PipelineResult with healing status and artifacts
    """
    # Phase 0: DISCOVER
    healing_delta = phase_0_discover(os_root, healing_delta_path)

    # Phase 1: VALIDATE (Preconditions)
    precond_result = phase_1_validate(healing_delta, os_root)

    if not precond_result.all_passed:
        return PipelineResult(
            status="PRECONDITION_FAILED",
            reason=f"Preconditions not satisfied: {precond_result.results}",
            artifacts={},
            metadata={"precondition_results": precond_result.results}
        )

    # Phase 2: CONVERGE (Create Rollback Snapshot)
    rollback_snapshot_path = phase_2_converge(healing_delta, os_root)

    # Phase 3: DECIDE (Application Plan)
    application_plan = phase_3_decide(healing_delta, os_root)

    # Phase 4: ACT (Apply + Validate + Rollback on Failure)
    healing_result = phase_4_act(
        healing_delta,
        application_plan,
        rollback_snapshot_path,
        os_root
    )

    return PipelineResult(
        status=healing_result.status,
        artifacts={
            "healing_receipt": healing_result.receipt_path,
            "rollback_snapshot": str(rollback_snapshot_path)
        },
        metadata={
            "healing_id": healing_result.healing_id,
            "files_modified": healing_result.files_modified,
            "rollback_performed": healing_result.rollback_performed
        }
    )
```

## Governance Rules
- P0: Pipeline MUST validate preconditions before application
- P0: Pipeline MUST create rollback snapshot before modification
- P0: Pipeline MUST rollback on postcondition failure
- P0: Pipeline MUST emit healing receipt regardless of outcome
- P1: Pipeline SHOULD append to healing receipt chain
- P1: Pipeline SHOULD retain rollback snapshots for audit

## Anti-Patterns (FORBIDDEN)
- ❌ Applying healing without precondition check
- ❌ Skipping rollback snapshot creation
- ❌ Ignoring postcondition failures
- ❌ Manual rollback (must be automatic)
- ❌ Silent failures (must emit failure receipts)
