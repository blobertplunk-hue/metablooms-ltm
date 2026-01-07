#!/usr/bin/env python3
"""
Generate ledger entries for MetaBlooms self-analysis session
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
LEDGER = ROOT / "ledger" / "ledger.ndjson"


def hash_entry(entry):
    """Calculate SHA256 of ledger entry"""
    canonical = json.dumps(entry, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode()).hexdigest()


def get_last_hash():
    """Get hash of last ledger entry"""
    if not LEDGER.exists():
        return None

    with open(LEDGER) as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        return None

    last = json.loads(lines[-1])
    return last.get("sha256")


def get_next_event_id():
    """Get next sequential event ID"""
    if not LEDGER.exists():
        return "evt_000002"

    with open(LEDGER) as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        return "evt_000002"

    last = json.loads(lines[-1])
    last_id = last.get("event_id", "evt_000001")
    num = int(last_id.split("_")[1]) + 1
    return f"evt_{num:06d}"


def create_entry(event_type, payload, prev_hash):
    """Create ledger entry with proper chaining"""
    entry = {
        "event_id": get_next_event_id(),
        "ts_utc": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "event_type": event_type,
        "payload": payload,
        "sha256": None,  # Will be calculated
        "prev_sha256": prev_hash
    }

    # Calculate hash
    entry_for_hash = {k: v for k, v in entry.items() if k != "sha256"}
    entry["sha256"] = hash_entry(entry_for_hash)

    return entry


def append_entry(entry):
    """Append entry to ledger"""
    with open(LEDGER, "a") as f:
        f.write(json.dumps(entry, separators=(',', ':')) + "\n")

    return entry["sha256"]


def main():
    print("Generating ledger entries for self-analysis session...")
    print(f"Ledger: {LEDGER}")

    prev_hash = get_last_hash()
    print(f"Last hash: {prev_hash}")

    # Entry 1: Analysis session start
    entry = create_entry(
        "ANALYSIS_SESSION_START",
        {
            "kind": "self_analysis",
            "method": "staged_delta_reading",
            "scope": "comprehensive_system_review",
            "deltas_count": 71,
            "lines_analyzed": 12307
        },
        prev_hash
    )
    prev_hash = append_entry(entry)
    print(f"✓ Analysis session start: {entry['event_id']}")

    # Entry 2: Schema consistency finding
    entry = create_entry(
        "FINDING_CRITICAL",
        {
            "finding_id": "P0-1",
            "category": "schema_chaos",
            "summary": "5 different MIPS header formats detected",
            "impact": "Cannot programmatically validate deltas",
            "evidence": "test_schema_consistency.py detected: MIPS_HEADER, mips_header, mips, meta, no_header",
            "priority": "P0"
        },
        prev_hash
    )
    prev_hash = append_entry(entry)
    print(f"✓ Finding P0-1: {entry['event_id']}")

    # Entry 3: Missing MIPS index
    entry = create_entry(
        "FINDING_CRITICAL",
        {
            "finding_id": "P0-2",
            "category": "missing_index",
            "summary": "MIPS_INDEX_CORE.mips.json not found",
            "impact": "Cannot determine active deltas, load order, or conflicts",
            "evidence": "test_mips_index_exists.py failed to locate index",
            "priority": "P0"
        },
        prev_hash
    )
    prev_hash = append_entry(entry)
    print(f"✓ Finding P0-2: {entry['event_id']}")

    # Entry 4: No governance loading
    entry = create_entry(
        "FINDING_CRITICAL",
        {
            "finding_id": "P0-3",
            "category": "governance_not_enforced",
            "summary": "Runtime doesn't load deltas from manifests/latest.json",
            "impact": "Governance contracts exist but not enforced",
            "evidence": "test_runtime_loads_governance.py found 0 indicators in RUN_METABLOOMS.py",
            "priority": "P0"
        },
        prev_hash
    )
    prev_hash = append_entry(entry)
    print(f"✓ Finding P0-3: {entry['event_id']}")

    # Entry 5: No ledger integration
    entry = create_entry(
        "FINDING_CRITICAL",
        {
            "finding_id": "P0-4",
            "category": "ledger_not_integrated",
            "summary": "Runtime doesn't write to ledger",
            "impact": "No audit trail of boot events",
            "evidence": "test_ledger_integration.py confirmed no ledger writes during boot",
            "priority": "P0"
        },
        prev_hash
    )
    prev_hash = append_entry(entry)
    print(f"✓ Finding P0-4: {entry['event_id']}")

    # Entry 6: Contract violations undetected
    entry = create_entry(
        "FINDING_CRITICAL",
        {
            "finding_id": "P0-5",
            "category": "contracts_not_enforced",
            "summary": "Contract violations not detected",
            "impact": "System can violate its own contracts",
            "evidence": "test_contract_violations.py: 0/4 violations detected (AM append-only, DM authority, RS mutation, doctrine hash)",
            "priority": "P0"
        },
        prev_hash
    )
    prev_hash = append_entry(entry)
    print(f"✓ Finding P0-5: {entry['event_id']}")

    # Entry 7: CSRG not implemented
    entry = create_entry(
        "FINDING_HIGH",
        {
            "finding_id": "P1-1",
            "category": "csrg_missing",
            "summary": "CSRG gate not implemented",
            "impact": "Problematic actions not caught before execution",
            "evidence": "test_csrg_gate.py: 0/3 actions properly gated (perl assumption, test contradiction, unverified boot)",
            "priority": "P1"
        },
        prev_hash
    )
    prev_hash = append_entry(entry)
    print(f"✓ Finding P1-1: {entry['event_id']}")

    # Entry 8: RCA mode not implemented
    entry = create_entry(
        "FINDING_HIGH",
        {
            "finding_id": "P1-2",
            "category": "rca_missing",
            "summary": "RCA mode not implemented",
            "impact": "Root cause analysis requires manual investigation",
            "evidence": "No RCA trigger logic in runtime",
            "priority": "P1"
        },
        prev_hash
    )
    prev_hash = append_entry(entry)
    print(f"✓ Finding P1-2: {entry['event_id']}")

    # Entry 9: Compiler pipeline missing
    entry = create_entry(
        "FINDING_HIGH",
        {
            "finding_id": "P1-3",
            "category": "compiler_missing",
            "summary": "Compiler pipeline not implemented",
            "impact": "Deltas not validated through 7-phase pipeline",
            "evidence": "No pressure tests, no promotion gates",
            "priority": "P1"
        },
        prev_hash
    )
    prev_hash = append_entry(entry)
    print(f"✓ Finding P1-3: {entry['event_id']}")

    # Entry 10: Delta promotion not implemented
    entry = create_entry(
        "FINDING_HIGH",
        {
            "finding_id": "P1-4",
            "category": "promotion_missing",
            "summary": "Delta promotion path not implemented",
            "impact": "No provisional→validated→locked workflow",
            "evidence": "All deltas treated equally regardless of maturity",
            "priority": "P1"
        },
        prev_hash
    )
    prev_hash = append_entry(entry)
    print(f"✓ Finding P1-4: {entry['event_id']}")

    # Entry 11: Learning loop not closed
    entry = create_entry(
        "FINDING_MEDIUM",
        {
            "finding_id": "P2-1",
            "category": "learning_loop_incomplete",
            "summary": "Learning loop not fully operational",
            "impact": "Manual intervention required to close loop",
            "evidence": "User confirms: 'right now the learning loop is not fully operational'",
            "priority": "P2"
        },
        prev_hash
    )
    prev_hash = append_entry(entry)
    print(f"✓ Finding P2-1: {entry['event_id']}")

    # Entry 12: Watcher fragility
    entry = create_entry(
        "FINDING_MEDIUM",
        {
            "finding_id": "P2-2",
            "category": "watcher_fragile",
            "summary": "Watcher scripts fragile across environments",
            "impact": "Auto-upload breaks when assumptions violated",
            "evidence": "Termux perl assumption failure documented in analysis",
            "priority": "P2"
        },
        prev_hash
    )
    prev_hash = append_entry(entry)
    print(f"✓ Finding P2-2: {entry['event_id']}")

    # Entry 13: Documentation gaps
    entry = create_entry(
        "FINDING_MEDIUM",
        {
            "finding_id": "P2-3",
            "category": "documentation_gaps",
            "summary": "Specification-implementation gap",
            "impact": "85% spec complete, 20% implementation complete",
            "evidence": "Comprehensive specifications exist but minimal runtime enforcement",
            "priority": "P2"
        },
        prev_hash
    )
    prev_hash = append_entry(entry)
    print(f"✓ Finding P2-3: {entry['event_id']}")

    # Entry 14: Test suite execution
    entry = create_entry(
        "TEST_EXECUTION",
        {
            "test_suite": "metablooms_self_test",
            "tests_run": 6,
            "tests_passed": 0,
            "tests_failed": 6,
            "total_time_seconds": 0.70,
            "test_files": [
                "test_schema_consistency.py",
                "test_mips_index_exists.py",
                "test_runtime_loads_governance.py",
                "test_ledger_integration.py",
                "test_contract_violations.py",
                "test_csrg_gate.py"
            ]
        },
        prev_hash
    )
    prev_hash = append_entry(entry)
    print(f"✓ Test execution: {entry['event_id']}")

    # Entry 15: Analysis completion
    entry = create_entry(
        "ANALYSIS_SESSION_COMPLETE",
        {
            "kind": "self_analysis",
            "findings_total": 12,
            "findings_p0": 5,
            "findings_p1": 4,
            "findings_p2": 3,
            "tests_created": 6,
            "tests_failed": 6,
            "outcome": "comprehensive_gap_analysis_complete",
            "artifacts": [
                "METABLOOMS_SELF_ANALYSIS_2026-01-06.md",
                "tests/test_schema_consistency.py",
                "tests/test_mips_index_exists.py",
                "tests/test_runtime_loads_governance.py",
                "tests/test_ledger_integration.py",
                "tests/test_contract_violations.py",
                "tests/test_csrg_gate.py",
                "tests/run_all_tests.py"
            ]
        },
        prev_hash
    )
    prev_hash = append_entry(entry)
    print(f"✓ Analysis completion: {entry['event_id']}")

    print(f"\n✅ Generated {15} ledger entries")
    print(f"Final hash: {prev_hash}")


if __name__ == "__main__":
    main()
