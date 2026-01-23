# PIPE_METABLOOMS_BOOT_SEQUENCE

**Pipeline ID**: PIPE_MB_BOOT_SEQ
**Type**: BOOT_PROTOCOL
**Authority**: PRODUCTION_IMPLEMENTATION
**Execution Model**: 5-PHASE (DISCOVER, VALIDATE, CONVERGE, DECIDE, ACT)
**Source**: MetaBlooms OS actual boot implementation

## Purpose
Execute complete MetaBlooms OS boot sequence with genesis check, turn lock, state rehydration, and 24 preflight gates.

## Pipeline Contract

```python
@dataclass
class MetaBloomsBootPipeline:
    pipeline_id: str = "PIPE_MB_BOOT_SEQ"
    phases: List[str] = field(default_factory=lambda: [
        "DISCOVER",    # Genesis check + OS discovery
        "VALIDATE",    # Turn lock + index allocation
        "CONVERGE",    # State rehydration
        "DECIDE",      # Preflight gate execution
        "ACT"          # Runtime initialization
    ])
    segments_used: List[str] = field(default_factory=lambda: [
        "SEG_METABLOOMS_RUNTIME_V1",
        "SEG_METABLOOMS_PREFLIGHT_GATES_V1",
        "SEG_METABLOOMS_EVIDENCE_STORE_V1"
    ])
    required_inputs: List[str] = field(default_factory=lambda: [
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

## Phase 0: DISCOVER (Genesis Check + OS Discovery)

**Purpose**: Ensure genesis receipt exists and discover canonical OS

**Pipe Segments**:
- INGEST: Load OS root configuration
- NORMALIZE: Validate OS structure
- VALIDATE: Check genesis receipt exists

**Execution**:
```python
def phase_0_discover(os_root: Path, turn_id: str) -> BootContext:
    """
    PHASE 0: DISCOVER - Genesis check and OS discovery.

    Flow:
    1. Load canonical_root.json configuration
    2. Check if genesis receipt exists
    3. If not exists, create via genesis.ensure_genesis_receipt()
    4. Discover canonical OS ZIP via boot_auto_resolver
    5. Return boot context

    Returns:
        BootContext with OS configuration
    """
    # Load configuration
    config_path = os_root / "metablooms" / "runtime" / "canonical_root.json"
    config = json.loads(config_path.read_text())

    # Genesis check
    genesis_receipt_path = os_root / "ledgers" / "genesis" / "GENESIS_BOOT_RECEIPT.json"

    if not genesis_receipt_path.exists():
        from metablooms.runtime import genesis
        genesis.ensure_genesis_receipt(os_root)

    # Discover canonical OS
    from metablooms.boot import boot_auto_resolver
    canonical_os_path = boot_auto_resolver.resolve_canonical_os(mount_path="/mnt/data")

    return BootContext(
        os_root=os_root,
        turn_id=turn_id,
        config=config,
        canonical_os_path=canonical_os_path
    )
```

## Phase 1: VALIDATE (Turn Lock + Index Allocation)

**Purpose**: Acquire turn lock and allocate sequential turn index

**Pipe Segments**:
- MAP: Map turn_id to lock file
- EXECUTE: Acquire turn lock atomically
- VERIFY: Validate lock acquisition

**Execution**:
```python
def phase_1_validate(ctx: BootContext) -> TurnLockResult:
    """
    PHASE 1: VALIDATE - Turn lock + index allocation.

    Flow:
    1. Acquire turn lock via turn_lock.acquire_turn_lock()
    2. Allocate turn index via turn_index.allocate_turn_index()
    3. Emit turn_index_receipt.json
    4. Return lock result

    Returns:
        TurnLockResult with lock_path and turn_index

    Raises:
        BlockingIOError: If turn lock held by another process (fail-closed)
    """
    from metablooms.runtime import turn_lock, turn_index

    # Acquire turn lock
    lock_path = turn_lock.acquire_turn_lock(
        os_root=ctx.os_root,
        turn_id=ctx.turn_id,
        stale_after_s=ctx.config["stale_lock_timeout_s"]
    )

    # Allocate turn index
    turn_index_val = turn_index.allocate_turn_index(
        os_root=ctx.os_root,
        turn_id=ctx.turn_id
    )

    return TurnLockResult(
        lock_path=lock_path,
        turn_index=turn_index_val
    )
```

## Phase 2: CONVERGE (State Rehydration)

**Purpose**: Rehydrate state from prior turn's snapshot and receipts

**Pipe Segments**:
- NORMALIZE: Discover latest turn directory
- VALIDATE: Verify snapshot integrity
- LEDGER: Load prior state

**Execution**:
```python
def phase_2_converge(ctx: BootContext) -> RehydrateResult:
    """
    PHASE 2: CONVERGE - State rehydration.

    Flow:
    1. Discover latest turn directory
    2. Load latest snapshot via snapshot_verify
    3. Verify snapshot SHA256 integrity
    4. Rehydrate state via auto_rehydrate
    5. Emit rehydrate_receipt.json
    6. Return rehydrated state

    Returns:
        RehydrateResult with prior_state dict

    Raises:
        SnapshotVerifyError: If snapshot corrupted (fail-closed)
    """
    from metablooms.runtime import auto_rehydrate, snapshot_verify

    # Discover latest snapshot
    latest_snapshot_path = snapshot_verify.find_latest_snapshot(ctx.os_root)

    if latest_snapshot_path:
        # Verify snapshot integrity
        snapshot_verify.verify_snapshot_file(latest_snapshot_path)

    # Auto-rehydrate
    prior_state = auto_rehydrate.auto_rehydrate(ctx.os_root)

    return RehydrateResult(
        prior_state=prior_state,
        rehydrate_receipt_path=ctx.os_root / "ledgers" / "turns" / ctx.turn_id / "rehydrate_receipt.json"
    )
```

## Phase 3: DECIDE (Preflight Gate Execution)

**Purpose**: Execute all 24 preflight gates in sequence

**Pipe Segments**:
- MAP: Map gates to execution order
- EXECUTE: Run each gate with fail-fast
- VERIFY: Validate all gates passed

**Execution**:
```python
def phase_3_decide(ctx: BootContext) -> PreflightResult:
    """
    PHASE 3: DECIDE - Preflight gate execution.

    Flow:
    1. Load gate registry (24 gates)
    2. For each gate in order:
       a. Import gate module
       b. Call gate_module.run_gate(ctx)
       c. Emit gate receipt
       d. If gate fails, STOP (fail-fast)
    3. Return preflight result with all gates passed

    Returns:
        PreflightResult with gates_passed count

    Raises:
        RuntimeError: If any gate fails (fail-closed)
    """
    from metablooms.preflight.gates import (
        mb_gate_p0_os_state_truth_v1,
        gate_single_active_turn,
        gate_snapshot_integrity,
        gate_turn_index_continuity,
        gate_receipt_hash_chain,
        # ... all 24 gates
    )

    gates = [
        ("P0.OS.STATE.TRUTH.V1", mb_gate_p0_os_state_truth_v1),
        ("GATE.SINGLE_ACTIVE_TURN", gate_single_active_turn),
        ("GATE.SNAPSHOT_INTEGRITY", gate_snapshot_integrity),
        ("GATE.TURN_INDEX_CONTINUITY", gate_turn_index_continuity),
        ("GATE.RECEIPT_HASH_CHAIN", gate_receipt_hash_chain),
        # ... all 24 gates
    ]

    gates_passed = 0
    gate_receipts = []

    for gate_id, gate_module in gates:
        try:
            gate_module.run_gate(ctx)
            gates_passed += 1

            # Emit gate receipt
            gate_receipt_path = emit_gate_receipt(
                os_root=ctx.os_root,
                turn_id=ctx.turn_id,
                gate_id=gate_id,
                status="PASSED"
            )
            gate_receipts.append(gate_receipt_path)

        except Exception as e:
            # Gate failed - emit failure receipt and stop
            emit_gate_receipt(
                os_root=ctx.os_root,
                turn_id=ctx.turn_id,
                gate_id=gate_id,
                status="FAILED",
                reason=str(e)
            )

            raise RuntimeError(f"GATE_FAILED: {gate_id} - {e}")

    return PreflightResult(
        gates_passed=gates_passed,
        gate_receipts=gate_receipts
    )
```

## Phase 4: ACT (Runtime Initialization)

**Purpose**: Initialize runtime components and emit boot receipt

**Pipe Segments**:
- EXECUTE: Initialize runtime modules
- VERIFY: Validate initialization
- LEDGER: Emit boot receipt
- EMIT: Signal boot complete

**Execution**:
```python
def phase_4_act(
    ctx: BootContext,
    lock_result: TurnLockResult,
    rehydrate_result: RehydrateResult,
    preflight_result: PreflightResult
) -> BootResult:
    """
    PHASE 4: ACT - Runtime initialization and boot receipt.

    Flow:
    1. Initialize evidence store
    2. Initialize decision trace
    3. Check snapshot cadence via boot_hooks
    4. Emit boot_receipt.json with:
       - turn_id
       - turn_index
       - prior_receipt_hash
       - gates_passed
       - receipt_hash
    5. Return boot result

    Returns:
        BootResult with boot_receipt_path
    """
    from metablooms.evidence import store_v1
    from metablooms.runtime import decision_trace, boot_hooks

    # Initialize evidence store
    evidence_store = store_v1.EvidenceStore(
        root=ctx.os_root / "evidence",
        min_free_bytes=ctx.config["evidence_quota"]["min_free_bytes"],
        max_artifact_bytes=ctx.config["evidence_quota"]["max_artifact_bytes"],
        max_total_task_bytes=ctx.config["evidence_quota"]["max_total_task_bytes"]
    )

    # Check snapshot cadence
    boot_hooks.snapshot_and_prune_if_due(ctx)

    # Build boot receipt
    boot_receipt = {
        "receipt_type": "BOOT_RECEIPT",
        "turn_id": ctx.turn_id,
        "turn_index": lock_result.turn_index,
        "timestamp_utc": utcnow(),
        "gates_passed": preflight_result.gates_passed,
        "prior_receipt_hash": get_prior_receipt_hash(ctx.os_root)
    }

    boot_receipt_hash = sha256_json(boot_receipt)
    boot_receipt["receipt_hash"] = boot_receipt_hash

    # Write boot receipt
    boot_receipt_path = ctx.os_root / "ledgers" / "turns" / ctx.turn_id / "boot_receipt.json"
    boot_receipt_path.parent.mkdir(parents=True, exist_ok=True)
    boot_receipt_path.write_text(json.dumps(boot_receipt, indent=2), encoding="utf-8")

    return BootResult(
        status="BOOT_SUCCESS",
        boot_receipt_path=boot_receipt_path,
        turn_index=lock_result.turn_index,
        gates_passed=preflight_result.gates_passed,
        boot_duration_ms=compute_boot_duration(ctx)
    )
```

## Pipeline Execution

```python
def execute_pipeline(os_root: Path, turn_id: str) -> PipelineResult:
    """
    Execute complete MetaBlooms OS boot sequence.

    Returns:
        PipelineResult with boot status and artifacts
    """
    start_time = time.time()

    # Phase 0: DISCOVER
    ctx = phase_0_discover(os_root, turn_id)

    # Phase 1: VALIDATE
    lock_result = phase_1_validate(ctx)

    # Phase 2: CONVERGE
    rehydrate_result = phase_2_converge(ctx)

    # Phase 3: DECIDE
    preflight_result = phase_3_decide(ctx)

    # Phase 4: ACT
    boot_result = phase_4_act(ctx, lock_result, rehydrate_result, preflight_result)

    boot_duration_ms = int((time.time() - start_time) * 1000)

    return PipelineResult(
        status="BOOT_SUCCESS",
        artifacts={
            "boot_receipt": boot_result.boot_receipt_path,
            "turn_lock": lock_result.lock_path,
            "rehydrate_receipt": rehydrate_result.rehydrate_receipt_path,
            "preflight_receipts": preflight_result.gate_receipts
        },
        metadata={
            "turn_index": boot_result.turn_index,
            "gates_passed": boot_result.gates_passed,
            "boot_duration_ms": boot_duration_ms
        }
    )
```

## Governance Rules
- P0: Pipeline MUST execute all 5 phases in order
- P0: Pipeline MUST acquire turn lock before proceeding
- P0: Pipeline MUST run all preflight gates (fail-fast)
- P0: Pipeline MUST emit boot receipt with receipt_hash
- P0: Pipeline MUST be fail-closed (stop on any error)
- P1: Pipeline SHOULD rehydrate state from prior turn
- P1: Pipeline SHOULD emit receipts for each phase

## Anti-Patterns (FORBIDDEN)
- ❌ Skipping phases
- ❌ Running gates in parallel (order matters)
- ❌ Continuing after gate failure
- ❌ Bypassing turn lock
- ❌ Missing boot receipt
- ❌ Concurrent boots without proper locking
