# SEG_ROLLBACK_SAFE_SHIPPING_V1

**Segment ID**: SEG_SHIP_ROLLBACK_V1
**Type**: OPERATIONAL_INFRASTRUCTURE
**Authority**: VALIDATED
**Proof Class**: INTEGRATION_EXECUTION

## Purpose
Ship OS bundles with atomic rollback on validation failure.

## Canonical Shipping Flow

### 1. Pre-Ship Conflict Detection Gate
```python
def detect_delta_conflicts(baseline_files, delta_files):
    """
    Detect overlapping delta targets before shipping.

    Returns:
        conflicts: dict of file -> list of delta_ids
        risk_level: P0 | P1 | P2
    """
    overlap_map = defaultdict(list)

    for delta in delta_files:
        for target in delta.targets:
            overlap_map[target].append(delta.delta_id)

    conflicts = {k: v for k, v in overlap_map.items() if len(v) > 1}

    # Fail-closed: P0 if conflicts affect boot files
    boot_critical = [
        "BOOT_METABLOOMS.py",
        "RUN_METABLOOMS.py",
        "metablooms/runtime/runtime_entrypoint.py"
    ]

    if any(f in conflicts for f in boot_critical):
        return conflicts, "P0"

    return conflicts, "P1" if conflicts else "P2"
```

### 2. Staging + Rollback Pattern
```python
def ship_with_rollback(baseline, deltas, output_path):
    """
    Ship with atomic rollback if boot validation fails.

    Phases:
    1. Extract baseline to staging
    2. Compute baseline inventory (pre-delta state)
    3. Apply deltas with tracking
    4. Compute final inventory
    5. Boot validation (P0)
    6. IF validation passes → create output ZIP
    7. IF validation fails → rollback (delete staging)

    Returns:
        ShipResult with status, receipts, inventory
    """
    staging_dir = tempfile.mkdtemp(prefix="metablooms_staging_")

    try:
        # Extract baseline
        extract_zip(baseline, staging_dir)

        # Pre-apply inventory (baseline state)
        baseline_inventory = compute_sha256_inventory(staging_dir)

        # Apply deltas with tracking
        delta_receipts = []
        for delta in deltas:
            receipt = apply_delta_with_receipt(staging_dir, delta)
            delta_receipts.append(receipt)

        # Post-apply inventory
        final_inventory = compute_sha256_inventory(staging_dir)

        # Boot validation (P0 fail-closed)
        boot_result = run_boot_validation(staging_dir)

        if boot_result.status != "BOOT_OK":
            # ROLLBACK: Remove staging, raise error
            shutil.rmtree(staging_dir)
            raise ShippingError(
                f"Boot failed: {boot_result.reason}",
                rollback_triggered=True
            )

        # Ship only if validation passed
        create_zip_with_inventory(staging_dir, output_path, final_inventory)

        return ShipResult(
            status="SHIP_OK",
            baseline_path=baseline,
            output_path=output_path,
            deltas_applied=delta_receipts,
            baseline_inventory=baseline_inventory,
            final_inventory=final_inventory,
            boot_validation=boot_result,
            rollback_triggered=False
        )

    except ShippingError as e:
        return ShipResult(
            status="SHIP_FAILED",
            reason=str(e),
            rollback_triggered=e.rollback_triggered
        )

    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
```

### 3. Ship Receipt Schema
```json
{
  "receipt_type": "SHIP_RECEIPT",
  "ship_id": "SHIP_20260122_...",
  "timestamp_utc": "2026-01-22T12:00:00Z",
  "baseline_used": {
    "path": "MetaBlooms_OS_v1.2.3.zip",
    "sha256": "abc123..."
  },
  "deltas_applied": [
    {
      "delta_id": "DELTA_XYZ",
      "files_modified": ["file1.py", "file2.py"],
      "sha256": "def456..."
    }
  ],
  "boot_validation": {
    "status": "BOOT_OK",
    "duration_ms": 1234,
    "gates_passed": ["gate1", "gate2"]
  },
  "inventory_delta": {
    "files_added": 5,
    "files_modified": 12,
    "files_removed": 2,
    "total_files": 1250
  },
  "output_artifact": {
    "path": "MetaBlooms_OS_v1.2.4.zip",
    "sha256": "ghi789...",
    "size_bytes": 555000
  },
  "rollback_triggered": false,
  "receipt_hash": "jkl012..."
}
```

## Validation Gates

### Pre-Ship Gates (Run Before Shipping)
1. **Delta Conflict Detection** (P0)
   - Detect overlapping file targets
   - Fail if boot-critical files conflict

2. **Delta Dependency Check** (P1)
   - Verify all delta preconditions met
   - Verify dependency order

3. **Baseline Integrity** (P0)
   - Verify baseline SHA256 matches expected
   - Verify baseline boots successfully

### Post-Ship Gates (Run After Shipping)
1. **Boot Validation** (P0 fail-closed)
   - Must run `RUN_METABLOOMS.py` in staging
   - Must emit boot receipt
   - Must pass all P0 gates
   - Exit code must be 0

2. **Inventory Verification** (P1)
   - Compare baseline → final delta
   - Verify no unexpected changes
   - Verify all delta targets present

## Inventory Format
```json
{
  "inventory_id": "INV_20260122_...",
  "timestamp_utc": "2026-01-22T12:00:00Z",
  "total_files": 1250,
  "files": {
    "RUN_METABLOOMS.py": {
      "sha256": "abc123...",
      "size_bytes": 1234,
      "modified_by_delta": "DELTA_XYZ"
    }
  }
}
```

## Governance Rules
- P0: No ship without boot validation passing
- P0: Rollback MUST occur if validation fails (no partial ships)
- P0: Ship receipt MUST be emitted on success
- P0: Staging directory MUST be cleaned up (finally block)
- P1: Baseline inventory MUST be computed before deltas applied
- P1: Final inventory MUST be included in ship receipt

## Failure Modes & Recovery

### Boot Validation Failure
- **Trigger**: `boot_result.status != "BOOT_OK"`
- **Action**: Rollback (delete staging), emit failure receipt
- **Recovery**: Fix delta, re-ship

### Delta Application Failure
- **Trigger**: `apply_delta()` raises exception
- **Action**: Rollback, emit failure receipt with delta ID
- **Recovery**: Fix delta manifest, re-ship

### Zip Creation Failure
- **Trigger**: `create_zip()` raises exception (disk full, permissions)
- **Action**: Rollback, emit failure receipt
- **Recovery**: Fix environment, re-ship

## Anti-Patterns (FORBIDDEN)
- ❌ Shipping without boot validation
- ❌ Partial rollback (leaving staging files)
- ❌ Overwriting baseline on failure
- ❌ Silent failures (all errors must emit receipts)
- ❌ Shipping with P0 gate failures ignored
