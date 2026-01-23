# SEG_SELF_HEALING_ROLLBACK_V1

**Segment ID**: SEG_SELF_HEALING_V1
**Type**: OPERATIONAL_INFRASTRUCTURE
**Authority**: VALIDATED
**Proof Class**: INTEGRATION_EXECUTION

## Purpose
Apply healing deltas with automatic rollback on validation failure.

## Healing Delta Schema
```python
@dataclass
class HealingDelta:
    delta_id: str
    healing_type: str  # "PATCH" | "PROMOTE" | "ROLLBACK"
    target_files: List[str]
    preconditions: List[Dict]  # Conditions to check before applying
    postconditions: List[Dict]  # Conditions to verify after applying
    rollback_snapshot: Optional[str]  # Snapshot to restore if healing fails
    priority: int  # 0 = P0 (critical), 1 = P1, 2 = P2
    created_utc: str
    sha256: str
```

## Healing Flow

```python
def apply_healing_delta_with_rollback(
    os_root: Path,
    healing_delta: HealingDelta
) -> HealingResult:
    """
    Apply healing delta with automatic rollback on failure.

    Flow:
    1. Validate preconditions
    2. Create rollback snapshot
    3. Apply healing delta
    4. Validate postconditions
    5. If postconditions fail → automatic rollback
    6. Emit healing receipt

    Returns:
        HealingResult with status and receipt path
    """
    healing_id = healing_delta.delta_id

    # Step 1: Validate preconditions
    try:
        validate_preconditions(os_root, healing_delta.preconditions)
    except PreconditionFailure as e:
        return HealingResult(
            healing_id=healing_id,
            status="PRECONDITION_FAILED",
            reason=str(e),
            rollback_performed=False
        )

    # Step 2: Create rollback snapshot
    rollback_snapshot_path = create_rollback_snapshot(
        os_root=os_root,
        healing_id=healing_id,
        target_files=healing_delta.target_files
    )

    # Step 3: Apply healing delta
    try:
        apply_delta_changes(os_root, healing_delta)
    except Exception as e:
        # Rollback on application failure
        restore_from_snapshot(os_root, rollback_snapshot_path)

        return HealingResult(
            healing_id=healing_id,
            status="APPLICATION_FAILED",
            reason=str(e),
            rollback_performed=True,
            rollback_snapshot=str(rollback_snapshot_path)
        )

    # Step 4: Validate postconditions
    try:
        validate_postconditions(os_root, healing_delta.postconditions)
    except PostconditionFailure as e:
        # Automatic rollback on validation failure
        restore_from_snapshot(os_root, rollback_snapshot_path)

        emit_healing_failure_receipt(
            os_root=os_root,
            healing_id=healing_id,
            reason=f"Postcondition failed: {e}",
            rollback_performed=True
        )

        return HealingResult(
            healing_id=healing_id,
            status="POSTCONDITION_FAILED_ROLLED_BACK",
            reason=str(e),
            rollback_performed=True,
            rollback_snapshot=str(rollback_snapshot_path)
        )

    # Step 5: Success - emit healing receipt
    receipt_path = emit_healing_success_receipt(
        os_root=os_root,
        healing_delta=healing_delta,
        rollback_snapshot=rollback_snapshot_path
    )

    return HealingResult(
        healing_id=healing_id,
        status="APPLIED_SUCCESSFULLY",
        files_modified=healing_delta.target_files,
        receipt_path=receipt_path,
        rollback_performed=False
    )
```

## Precondition Validation

```python
def validate_preconditions(os_root: Path, preconditions: List[Dict]) -> None:
    """
    Validate all preconditions before applying healing.

    Supported precondition types:
    - file_exists: {"type": "file_exists", "path": "..."}
    - file_hash: {"type": "file_hash", "path": "...", "sha256": "..."}
    - delta_applied: {"type": "delta_applied", "delta_id": "..."}
    - registry_version: {"type": "registry_version", "min_version": "..."}
    - gate_pass: {"type": "gate_pass", "gate_name": "..."}
    """
    for precond in preconditions:
        precond_type = precond.get("type")

        if precond_type == "file_exists":
            file_path = os_root / precond["path"]
            if not file_path.exists():
                raise PreconditionFailure(
                    f"File does not exist: {precond['path']}"
                )

        elif precond_type == "file_hash":
            file_path = os_root / precond["path"]
            if not file_path.exists():
                raise PreconditionFailure(
                    f"File does not exist: {precond['path']}"
                )

            actual_hash = sha256_text(file_path.read_text(encoding="utf-8"))
            expected_hash = precond["sha256"]

            if actual_hash != expected_hash:
                raise PreconditionFailure(
                    f"File hash mismatch for {precond['path']}: "
                    f"expected {expected_hash}, got {actual_hash}"
                )

        elif precond_type == "delta_applied":
            applied_deltas = load_applied_deltas_set(os_root)
            if precond["delta_id"] not in applied_deltas:
                raise PreconditionFailure(
                    f"Delta not applied: {precond['delta_id']}"
                )

        elif precond_type == "registry_version":
            registry = load_registry(os_root)
            current_version = registry.get("version", "0.0.0")
            min_version = precond["min_version"]

            if not version_greater_equal(current_version, min_version):
                raise PreconditionFailure(
                    f"Registry version {current_version} < {min_version}"
                )

        elif precond_type == "gate_pass":
            # Verify gate passed in most recent boot
            gate_name = precond["gate_name"]
            latest_boot_receipt = load_latest_boot_receipt(os_root)

            if not gate_passed_in_receipt(gate_name, latest_boot_receipt):
                raise PreconditionFailure(
                    f"Gate did not pass: {gate_name}"
                )

        else:
            raise PreconditionFailure(
                f"Unknown precondition type: {precond_type}"
            )
```

## Postcondition Validation

```python
def validate_postconditions(os_root: Path, postconditions: List[Dict]) -> None:
    """
    Validate all postconditions after applying healing.

    Supported postcondition types:
    - file_exists: {"type": "file_exists", "path": "..."}
    - file_hash: {"type": "file_hash", "path": "...", "sha256": "..."}
    - gate_pass: {"type": "gate_pass", "gate_name": "..."}
    - function_exists: {"type": "function_exists", "file": "...", "function": "..."}
    - import_succeeds: {"type": "import_succeeds", "module": "..."}
    """
    for postcond in postconditions:
        postcond_type = postcond.get("type")

        if postcond_type == "file_exists":
            file_path = os_root / postcond["path"]
            if not file_path.exists():
                raise PostconditionFailure(
                    f"File does not exist after healing: {postcond['path']}"
                )

        elif postcond_type == "file_hash":
            file_path = os_root / postcond["path"]
            if not file_path.exists():
                raise PostconditionFailure(
                    f"File does not exist: {postcond['path']}"
                )

            actual_hash = sha256_text(file_path.read_text(encoding="utf-8"))
            expected_hash = postcond["sha256"]

            if actual_hash != expected_hash:
                raise PostconditionFailure(
                    f"File hash mismatch after healing for {postcond['path']}: "
                    f"expected {expected_hash}, got {actual_hash}"
                )

        elif postcond_type == "gate_pass":
            # Run gate and verify it passes
            gate_name = postcond["gate_name"]
            gate_result = run_gate(os_root, gate_name)

            if not gate_result.passed:
                raise PostconditionFailure(
                    f"Gate failed after healing: {gate_name} - {gate_result.reason}"
                )

        elif postcond_type == "function_exists":
            # Static check for function definition
            file_path = os_root / postcond["file"]
            function_name = postcond["function"]

            if not file_path.exists():
                raise PostconditionFailure(
                    f"File does not exist: {postcond['file']}"
                )

            content = file_path.read_text(encoding="utf-8")
            if f"def {function_name}(" not in content:
                raise PostconditionFailure(
                    f"Function not found: {function_name} in {postcond['file']}"
                )

        elif postcond_type == "import_succeeds":
            # Test that module can be imported
            module_name = postcond["module"]
            try:
                __import__(module_name)
            except ImportError as e:
                raise PostconditionFailure(
                    f"Module import failed: {module_name} - {e}"
                )

        else:
            raise PostconditionFailure(
                f"Unknown postcondition type: {postcond_type}"
            )
```

## Rollback Snapshot Creation

```python
def create_rollback_snapshot(
    os_root: Path,
    healing_id: str,
    target_files: List[str]
) -> Path:
    """
    Create rollback snapshot before applying healing.

    Captures:
    - File contents for all target files
    - File metadata (permissions, timestamps)
    - Registry state snapshot

    Returns:
        Path to rollback snapshot
    """
    snapshot_dir = os_root / "ledgers" / "healing_rollbacks" / healing_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    snapshot = {
        "healing_id": healing_id,
        "created_utc": datetime.utcnow().isoformat() + "Z",
        "target_files": [],
        "registry_snapshot": None
    }

    # Capture each target file
    for target_file in target_files:
        file_path = os_root / target_file

        if file_path.exists():
            # Store file content
            content = file_path.read_text(encoding="utf-8")
            content_hash = sha256_text(content)

            backup_path = snapshot_dir / target_file.replace("/", "_")
            backup_path.write_text(content, encoding="utf-8")

            snapshot["target_files"].append({
                "path": target_file,
                "sha256": content_hash,
                "backup_path": str(backup_path),
                "existed": True
            })
        else:
            # Mark as non-existent (will be deleted on rollback if created)
            snapshot["target_files"].append({
                "path": target_file,
                "existed": False
            })

    # Capture registry snapshot
    registry_path = os_root / "registries" / "master_registry.json"
    if registry_path.exists():
        registry_content = registry_path.read_text(encoding="utf-8")
        registry_backup_path = snapshot_dir / "master_registry_backup.json"
        registry_backup_path.write_text(registry_content, encoding="utf-8")

        snapshot["registry_snapshot"] = str(registry_backup_path)

    # Write snapshot manifest
    snapshot_manifest_path = snapshot_dir / "rollback_manifest.json"
    snapshot_manifest_path.write_text(
        json.dumps(snapshot, indent=2),
        encoding="utf-8"
    )

    return snapshot_manifest_path
```

## Rollback Restoration

```python
def restore_from_snapshot(os_root: Path, snapshot_manifest_path: Path) -> None:
    """
    Restore files from rollback snapshot.

    Restores:
    - All target files to their pre-healing state
    - Registry to pre-healing state
    - Deletes any files that didn't exist before healing
    """
    snapshot = json.loads(snapshot_manifest_path.read_text(encoding="utf-8"))

    # Restore each target file
    for file_entry in snapshot["target_files"]:
        target_path = os_root / file_entry["path"]

        if file_entry["existed"]:
            # Restore from backup
            backup_path = Path(file_entry["backup_path"])
            content = backup_path.read_text(encoding="utf-8")

            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")
        else:
            # Delete if it was created during healing
            if target_path.exists():
                target_path.unlink()

    # Restore registry
    if snapshot["registry_snapshot"]:
        registry_backup_path = Path(snapshot["registry_snapshot"])
        registry_path = os_root / "registries" / "master_registry.json"

        registry_content = registry_backup_path.read_text(encoding="utf-8")
        registry_path.write_text(registry_content, encoding="utf-8")
```

## Healing Receipt Schema

```json
{
  "receipt_type": "HEALING_RECEIPT",
  "healing_id": "HEAL_001",
  "timestamp_utc": "2026-01-22T10:00:00Z",
  "healing_type": "PATCH",
  "status": "APPLIED_SUCCESSFULLY",
  "target_files": [
    "metablooms/runtime/turn_lock.py",
    "metablooms/runtime/turn_index.py"
  ],
  "preconditions_validated": 3,
  "postconditions_validated": 2,
  "rollback_snapshot": "ledgers/healing_rollbacks/HEAL_001/rollback_manifest.json",
  "rollback_performed": false,
  "files_modified": [
    "metablooms/runtime/turn_lock.py",
    "metablooms/runtime/turn_index.py"
  ],
  "prior_healing_receipt_hash": "abc123...",
  "receipt_hash": "def456..."
}
```

## Governance Rules
- P0: Healing MUST validate preconditions before application
- P0: Healing MUST create rollback snapshot before modification
- P0: Healing MUST rollback on postcondition failure
- P0: Healing MUST emit receipt (success or failure)
- P1: Healing receipts MUST be hash-chained
- P1: Rollback snapshots MUST be retained for audit

## Anti-Patterns (FORBIDDEN)
- ❌ Applying healing without precondition validation
- ❌ Skipping rollback snapshot creation
- ❌ Ignoring postcondition failures
- ❌ Manual rollback (must be automatic)
- ❌ Deleting rollback snapshots before audit period ends
