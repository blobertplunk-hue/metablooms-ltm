# SEG_METABLOOMS_PREFLIGHT_GATES_V1

**Segment ID**: SEG_MB_PREFLIGHT_V1
**Type**: OPERATIONAL_INFRASTRUCTURE
**Authority**: PRODUCTION_IMPLEMENTATION
**Proof Class**: RUNTIME_EXECUTION
**Source**: MetaBlooms OS `/home/user/metablooms-os-debug/metablooms/preflight/gates/`

## Purpose
Document the 24 production preflight gates in MetaBlooms OS that enforce P0/P1/P2 invariants before boot.

## Gate Hierarchy

### P0 Gates (Critical - Boot-Blocking)

**mb_gate_p0_os_state_truth_v1.py**
- Gate ID: `P0.OS.STATE.TRUTH.V1`
- Purpose: Verify canonical OS ZIP integrity and rehydrate if needed
- Security: Path traversal protection via `_validate_zip_entry()`
- Functions: `_find_canonical_zip()`, `_safe_extract()`, `run_gate()`
- Fail-Closed: Blocks boot if ZIP missing or corrupted
- Integration: Searches `/mnt/data/MetaBlooms_OS_WHOLEOS_*.zip`

**mb_gate_byte_truth_v2.py**
- Gate ID: `P0.BYTE_TRUTH.V2`
- Purpose: Verify on-disk bytes match expected state
- Fail-Closed: Blocks boot on hash mismatch

**mb_gate_docs_fail_to_fix_v1.py**
- Gate ID: `GATE.P0.DOCS.FAIL_TO_FIX.V1`
- Purpose: Enforce documentation quality standards
- Ledger: Writes evidence to ledger on failure
- Fail-Closed: Blocks promotion if docs inadequate

**mb_gate_docs_hardening_fail_to_fix_v1.py**
- Gate ID: `GATE.P0.DOCS.HARDENING.FAIL_TO_FIX.V1`
- Purpose: Enforce hardening documentation
- Fail-Closed: Blocks if security hardening not documented

**mb_gate_phase1_metagates_registered_v1.py**
- Gate ID: `GATE.P0.PHASE1.METAGATES.REGISTERED.V1`
- Purpose: Verify Phase 1 metagates are registered
- Fail-Closed: Ensures metagate enforcement active

### Concurrency & State Gates

**gate_single_active_turn.py**
- Purpose: Enforce single-writer concurrency
- Integration: Calls `runtime/turn_lock.py:acquire_turn_lock()`
- Contract: Only one turn may execute at a time
- Fail-Closed: Raises `BlockingIOError` on concurrent access

**gate_snapshot_integrity.py**
- Purpose: Verify latest snapshot SHA256 integrity
- Integration: Calls `runtime/snapshot_verify.py:verify_snapshot_file()`
- Fail-Closed: Blocks boot if snapshot corrupted

**gate_turn_index_continuity.py**
- Purpose: Ensure sequential turn index progression
- Integration: Works with `runtime/turn_index.py`
- Prevents: Turn index gaps or duplicates

**gate_receipt_hash_chain.py**
- Purpose: Maintain receipt hash chain for audit trail
- Validation: Verifies prior_receipt_hash matches previous receipt
- Fail-Closed: Blocks on broken chain

### Evidence & Semantics Gates

**mb_gate_evidence_see_loop_v1.py**
- Gate ID: `GATE.EVIDENCE.SEE.LOOP.V1`
- Purpose: Enforce SEE loop evidence requirements

**mb_gate_semantic_segments_required_v1.py**
- Gate ID: `GATE.SEMANTIC.SEGMENTS.REQUIRED.V1`
- Purpose: Require semantic segments for work products

**mb_gate_semantic_segments_coverage_v1.py**
- Gate ID: `GATE.SEMANTIC.SEGMENTS.COVERAGE.V1`
- Purpose: Enforce minimum segment coverage

**mb_gate_autosave_keep_drop_why_v1.py**
- Gate ID: `GATE.AUTOSAVE.KEEP_DROP_WHY.V1`
- Purpose: Require explicit rationale for keeping/dropping autosaves

### Quality & Contract Gates

**mb_gate_decision_trace_wiring_v1.py**
- Gate ID: `GATE.DECISION.TRACE.WIRING.V1`
- Purpose: Verify decision trace wiring is correct
- Integration: Validates `governance/DECISION_TRACE_APPEND_ONLY.jsonl`

**mb_gate_decision_trace_schema_validate_v1.py**
- Gate ID: `GATE.DECISION.TRACE.SCHEMA.VALIDATE.V1`
- Purpose: Validate decision trace schema compliance
- Schema Fields: ts_utc, objective_key, decision_id, decision, rationale, evidence_refs

**mb_gate_preflight_chain_schema_v1.py**
- Gate ID: `GATE.CHAIN.SCHEMA.V1`
- Purpose: Validate preflight gate chain schema

**mb_gate_canonical_root_manifest_v1.py**
- Purpose: Validate canonical root manifest
- File: `runtime/canonical_root.json`

**mb_gate_provenance_minimal_v1.py**
- Gate ID: `GATE.PROVENANCE.MIN3.V1`
- Purpose: Require minimum provenance evidence (3 items)

**mb_gate_no_placeholders_v1.py**
- Gate ID: `GATE.CODE.NO_PLACEHOLDERS.V1`
- Purpose: Detect placeholder code (TODO, FIXME, NotImplemented)
- Fail-Closed: Blocks if placeholders found in production code

**mb_gate_no_swallowed_exceptions_v1.py**
- Gate ID: `GATE.CODE.NO_SWALLOWED_EXCEPTIONS.V1`
- Purpose: Detect swallowed exceptions (bare except, pass)
- Fail-Closed: Blocks if silent error handling found

**mb_gate_subcausal_sentry_v1.py**
- Gate ID: `GATE.SUBCAUSAL_SENTRY.V1`
- Purpose: Monitor subcausal execution patterns

**mb_gate_excode_ecl_v1.py**
- Gate ID: `GATE.EXCODE.ECL.V1`
- Purpose: ECL constraints on exit codes
- Integration: Validates exit code semantics

**mb_gate_ec_auto.py**
- Gate ID: `GATE.EC_AUTO.V1`
- Purpose: Automated exit code analysis

**mb_gate_file_handling_contract_v1.py**
- Purpose: Enforce file handling contracts
- Contract: All file I/O must be atomic or fail-closed

## Gate Execution Interface

All gates implement standardized interface:

```python
def run_gate(context: Dict) -> None:
    """
    Execute gate validation.

    Args:
        context: Dictionary with os_root, turn_id, etc.

    Raises:
        RuntimeError: If gate fails validation
    """
    pass  # Gate-specific logic
```

## Integration with Boot Sequence

```python
# From RUN_METABLOOMS.py boot sequence
def run_preflight_gates(ctx):
    gates = [
        "mb_gate_p0_os_state_truth_v1",
        "gate_single_active_turn",
        "gate_snapshot_integrity",
        "gate_turn_index_continuity",
        "gate_receipt_hash_chain",
        # ... all 24 gates
    ]

    for gate_name in gates:
        try:
            gate_module = import_gate(gate_name)
            gate_module.run_gate(ctx)
        except Exception as e:
            emit_failure_receipt(gate_name, str(e))
            return False  # Fail-closed

    return True  # All gates passed
```

## Gate Receipt Schema

```json
{
  "receipt_type": "PREFLIGHT_GATE_RECEIPT",
  "gate_id": "P0.OS.STATE.TRUTH.V1",
  "timestamp_utc": "2026-01-23T12:00:00Z",
  "status": "PASSED",
  "turn_id": "TURN_001",
  "evidence": {
    "canonical_zip_sha256": "abc123...",
    "extraction_verified": true
  },
  "receipt_hash": "def456..."
}
```

## Governance Rules
- P0: All P0 gates MUST pass before boot
- P0: Gate failures MUST emit receipts
- P0: Gates MUST be fail-closed (reject on uncertainty)
- P1: Gate execution MUST be sequential and ordered
- P1: Gate receipts MUST be hash-chained

## Anti-Patterns (FORBIDDEN)
- ❌ Skipping gates on failure
- ❌ Silently catching gate exceptions
- ❌ Conditional gate execution based on environment
- ❌ Modifying gate results after execution
- ❌ Running gates in parallel (order matters)
