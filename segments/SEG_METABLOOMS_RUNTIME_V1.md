# SEG_METABLOOMS_RUNTIME_V1

**Segment ID**: SEG_MB_RUNTIME_V1
**Type**: OPERATIONAL_INFRASTRUCTURE
**Authority**: PRODUCTION_IMPLEMENTATION
**Proof Class**: RUNTIME_EXECUTION
**Source**: MetaBlooms OS `/home/user/metablooms-os-debug/metablooms/runtime/`

## Purpose
Document the 10 core runtime modules that manage turn-based execution, state rehydration, concurrency, and evidence capture in MetaBlooms OS.

## Core Runtime Modules

### auto_rehydrate.py

**Purpose**: Auto-rehydrate state from prior turn before any other logic

**Functions**:
```python
def auto_rehydrate(os_root: Path) -> Dict:
    """
    Discover latest turn and rehydrate state.

    Flow:
    1. Call discover_latest_turn_dir()
    2. Load prior turn's snapshot
    3. Verify snapshot integrity via snapshot_verify
    4. Emit rehydrate_receipt.json

    Returns:
        Rehydrated state dict

    Raises:
        RehydrateError: Fail-closed if no prior state or corruption
    """

def discover_latest_turn_dir(os_root: Path) -> Optional[Path]:
    """
    Discover latest turn directory by sorting ledgers/turns/*

    Returns:
        Path to latest TURN_* directory or None if genesis
    """
```

**Evidence**: Writes `ledgers/turns/<TURN_ID>/rehydrate_receipt.json`

**Contract**: Fail-closed if no prior receipt (except genesis)

**Integration**: Calls `snapshot_verify.verify_snapshot_file()` as P0 check

---

### turn_lock.py

**Purpose**: Crash-safe single-writer concurrency using atomic file locking

**Functions**:
```python
def acquire_turn_lock(
    os_root: Path,
    turn_id: str,
    stale_after_s: int = 900
) -> Path:
    """
    Acquire turn lock with stale recovery.

    Platforms:
    - Unix: fcntl.flock() for atomic locking
    - Windows: PID-based with staleness check

    Stale Recovery:
    1. Check if existing lock is stale (> stale_after_s seconds old)
    2. If stale, write turn_lock_recovery_receipt.json
    3. Take over lock

    Returns:
        Path to lock file

    Raises:
        BlockingIOError: If lock held by another process (fail-closed)
    """

def release_turn_lock(lock_path: Path) -> None:
    """Release turn lock and delete lock file."""
```

**Evidence**:
- Writes `ledgers/TURN_LOCK.json` (lock holder info)
- Writes `turn_lock_recovery_receipt.json` on stale recovery

**Contract**: Fail-closed on concurrent access

**Implementation**:
```python
# Unix (atomic)
import fcntl
_LOCK_FILE_HANDLE = open(lock_path, "w+")
fcntl.flock(_LOCK_FILE_HANDLE.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

# Windows (PID-based)
if lock_path.exists():
    lock_data = json.loads(lock_path.read_text())
    if is_process_running(lock_data["pid"]):
        raise BlockingIOError("Turn lock held by another process")
    # Stale recovery logic
```

---

### turn_index.py

**Purpose**: Allocate sequential turn indices for audit trail

**Functions**:
```python
def allocate_turn_index(os_root: Path, turn_id: str) -> int:
    """
    Allocate next sequential turn index.

    Flow:
    1. Call discover_latest_boot_receipt()
    2. Read turn_index from boot_receipt.json
    3. Increment by 1
    4. Write turn_index_receipt.json with new index

    Returns:
        Allocated turn index (integer)
    """

def discover_latest_boot_receipt(os_root: Path) -> Optional[Path]:
    """
    Search for latest boot_receipt.json in ledgers/turns/*/

    File Naming Contract:
    - Reads: boot_receipt.json
    - Writes: turn_index_receipt.json

    Returns:
        Path to latest boot receipt or None
    """
```

**Evidence**: Writes `ledgers/turns/<TURN_ID>/turn_index_receipt.json`

**Integration**: Maintains sequential turn progression

---

### sandbox_exec_v1.py

**Purpose**: Execute commands with evidence capture and sandbox protections

**Functions**:
```python
def sandbox_execute(task_spec: Dict, iteration: int) -> Dict:
    """
    Execute task with sandboxing and evidence capture.

    Security:
    1. Validate workdir via _validate_workdir()
    2. Enforce timeout bounds (1-3600 seconds)
    3. Isolate environment variables
    4. Capture stdout/stderr with SHA256

    Evidence Levels:
    - E1: Timeout (command exceeded timeout)
    - E2: Non-zero exit (command failed)
    - E3: Success (command succeeded)

    Returns:
        Execution receipt with evidence paths
    """

def _validate_workdir(workdir: str, evidence_root: str) -> Path:
    """
    Validate workdir is safe for execution.

    Forbidden directories:
    - / (root)
    - /etc (system config)
    - /bin, /usr/bin (system binaries)

    Raises:
        ValueError: If workdir is forbidden
    """

def _validate_timeout(timeout_s: int) -> None:
    """
    Validate timeout is within bounds [1, 3600].

    Raises:
        ValueError: If timeout out of range
    """
```

**Evidence**: Writes to evidence store:
- `stdout.txt` with SHA256
- `stderr.txt` with SHA256
- `receipt.json` with exit code, duration, evidence refs

**Security**: Path traversal protection, timeout enforcement, env isolation

---

### decision_trace.py

**Purpose**: Write sanitized decision records to append-only JSONL ledger

**Functions**:
```python
def record_decision(
    objective_key: str,
    decision: str,
    rationale: str,
    evidence_refs: List[str],
    assumptions: Optional[List[str]] = None,
    failure_surfaces: Optional[List[str]] = None,
    actor: str = "SYSTEM"
) -> str:
    """
    Record decision to append-only ledger.

    Ledger Path: metablooms/governance/DECISION_TRACE_APPEND_ONLY.jsonl

    Record Structure:
    {
      "ts_utc": "2026-01-23T12:00:00Z",
      "objective_key": "OBJECTIVE_001",
      "decision_id": "DEC_abc123",
      "decision": "Apply patch P0.1",
      "rationale": "P0 bug in turn_lock.py requires atomic locking",
      "assumptions": ["Unix platform available", "fcntl module works"],
      "failure_surfaces": ["fcntl unavailable on platform"],
      "evidence_refs": ["governance/audits/SEE_BLOCK.json"],
      "actor": "CLAUDE_CODE"
    }

    Returns:
        Decision ID for later reference
    """

def get_ledger_path(os_root: Path) -> Path:
    """Return path to decision trace ledger."""
```

**Contract**: NOT a chain-of-thought exporter; evidence-first design

**Integration**: Used by governance loop and promotion gates

---

### genesis.py

**Purpose**: Create initial boot receipt for first turn

**Functions**:
```python
def ensure_genesis_receipt(os_root: Path) -> Path:
    """
    Create genesis boot receipt if none exists.

    Genesis Receipt:
    {
      "receipt_type": "GENESIS_BOOT_RECEIPT",
      "turn_id": "GENESIS",
      "turn_index": 0,
      "timestamp_utc": "2026-01-23T10:00:00Z",
      "prior_receipt_hash": null,
      "policy": "INITIAL_BOOT_EXCEPTION",
      "receipt_hash": "abc123..."
    }

    Output: ledgers/genesis/GENESIS_BOOT_RECEIPT.json

    Returns:
        Path to genesis receipt
    """
```

**Policy**: `INITIAL_BOOT_EXCEPTION` - allows genesis without prior state

**Contract**: Genesis receipt has no prior_receipt_hash (start of chain)

---

### receipt_hash.py

**Purpose**: Generate SHA256 hashes for receipts and maintain hash chains

**Functions**:
```python
def hash_receipt(receipt: Dict) -> str:
    """
    Compute SHA256 hash of receipt (excluding receipt_hash field).

    Algorithm:
    1. Copy receipt without "receipt_hash" field
    2. Serialize to canonical JSON (sorted keys)
    3. Compute SHA256

    Returns:
        SHA256 hex string
    """

def chain_receipt(current_receipt: Dict, prior_receipt: Dict) -> Dict:
    """
    Chain current receipt to prior receipt via hash.

    Flow:
    1. Extract prior_receipt["receipt_hash"]
    2. Set current_receipt["prior_receipt_hash"]
    3. Compute current_receipt["receipt_hash"]

    Returns:
        Chained receipt with both hashes
    """
```

**Integration**: Ensures audit trail integrity via SHA256 chaining

**Validation**: Gates verify prior_receipt_hash matches actual prior receipt

---

### snapshot_verify.py

**Purpose**: Verify snapshot SHA256 integrity before rehydration

**Functions**:
```python
def verify_snapshot_file(snapshot_path: Path) -> bool:
    """
    Verify snapshot file SHA256 matches declared hash.

    Flow:
    1. Load snapshot JSON
    2. Extract declared sha256 field
    3. Recompute SHA256 of snapshot (excluding sha256 field)
    4. Compare

    Returns:
        True if hashes match

    Raises:
        SnapshotVerifyError: Fail-closed on mismatch
    """

def find_latest_snapshot(os_root: Path) -> Optional[Path]:
    """
    Find latest snapshot by sorting metablooms/state/snapshots/SNAPSHOT_TURN_*.json

    Returns:
        Path to latest snapshot or None
    """
```

**Path**: `metablooms/state/snapshots/SNAPSHOT_TURN_*.json`

**Contract**: Fail-closed on hash mismatch

---

### boot_hooks.py

**Purpose**: Snapshot cadence hook for periodic state persistence

**Functions**:
```python
def snapshot_and_prune_if_due(ctx: Dict) -> None:
    """
    Check snapshot cadence and trigger if due.

    Cadence: Every ctx.snapshot_interval turns (e.g., 10)

    Flow:
    1. Check if current_turn_index % snapshot_interval == 0
    2. If due:
       a. Call snapshot_writer.write_snapshot()
       b. Call delta_pruner.prune_deltas()
    3. Emit snapshot receipt

    Returns:
        None (side effects: snapshot + pruning)
    """
```

**Integration**:
- Calls `state/snapshot_writer.py:write_snapshot()`
- Calls `state/delta_pruner.py:prune_deltas()`

**Policy**: Keep configurable number of latest deltas after snapshot

---

### canonical_root.json

**Purpose**: Canonical root manifest for OS configuration

**Schema**:
```json
{
  "canonical_root": "/mnt/data/metablooms_os",
  "snapshot_interval": 10,
  "delta_retention_count": 50,
  "stale_lock_timeout_s": 900,
  "evidence_quota": {
    "min_free_bytes": 1073741824,
    "max_artifact_bytes": 104857600,
    "max_total_task_bytes": 1073741824
  }
}
```

**Validation**: Gate `mb_gate_canonical_root_manifest_v1.py` validates this file

---

## Runtime Execution Flow

```python
# Boot sequence (simplified)
def boot_turn():
    # 1. Genesis check
    genesis.ensure_genesis_receipt(os_root)

    # 2. Acquire turn lock
    lock_path = turn_lock.acquire_turn_lock(os_root, turn_id)

    # 3. Allocate turn index
    turn_index = turn_index.allocate_turn_index(os_root, turn_id)

    # 4. Rehydrate from prior turn
    prior_state = auto_rehydrate.auto_rehydrate(os_root)

    # 5. Run preflight gates (see SEG_METABLOOMS_PREFLIGHT_GATES_V1)
    run_preflight_gates(ctx)

    # 6. Execute turn logic
    result = execute_turn(ctx)

    # 7. Snapshot if due
    boot_hooks.snapshot_and_prune_if_due(ctx)

    # 8. Release turn lock
    turn_lock.release_turn_lock(lock_path)

    return result
```

## Governance Rules
- P0: Runtime modules MUST be fail-closed on errors
- P0: Turn lock MUST prevent concurrent execution
- P0: Receipts MUST be hash-chained for audit
- P0: Snapshots MUST be SHA256-verified before rehydration
- P1: Decision trace MUST be append-only
- P1: Evidence MUST be captured for all sandbox executions

## Anti-Patterns (FORBIDDEN)
- ❌ Skipping turn lock acquisition
- ❌ Modifying prior turn receipts
- ❌ Deleting decision trace entries
- ❌ Bypassing snapshot verification
- ❌ Running sandboxed commands without evidence capture
- ❌ Using non-atomic file operations for turn lock
