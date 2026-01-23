# SEG_P0_DEBUG_PROTOCOL_V1

**Segment ID**: SEG_P0_DEBUG_V1
**Type**: METHODOLOGICAL
**Authority**: VALIDATED
**Proof Class**: INTEGRATION_EXECUTION

## Purpose
Systematic P0 CRITICAL bug identification and patching using governed SEE/MMD/ECL protocol.

## Canonical Order

### Phase 0: Input Contract
- Scope boundary (what is being evaluated)
- Artifacts (files, logs, receipts)
- Demand (specific request)
- Question (what needs proving)

### Phase 1: SEE (Sandcrawler Evidence Engine)
- Enumerate reality without interpretation
- Record: paths, filenames, hashes, counts, literals
- Output: `SEE_BLOCK_<ID>.json`
- Forbidden: explanations, conclusions, opinions

### Phase 2: MMD (Missing-Middle Detector)
- Compare exists vs must-exist
- For each required invariant: MISSING | BROKEN | SATISFIED
- Output: `MMD_REPORT_<ID>.json`
- Forbidden: proposing fixes

### Phase 3: ECL (Extraordinary Claims Law)
- Classify claims: ALLOWED | CONDITIONAL | FORBIDDEN | FALSE
- Require evidence for each claim
- Output: `ECL_CLAIM_MATRIX_<ID>.json`

### Phase 4: Governed Recursion Decision
```
IF MMD has missing P0 items:
    → RECURSE WITH PATCH
ELSE IF MMD only has P1/P2:
    → OPTIONAL RECURSE
ELSE:
    → STOP
```

### Phase 5: Patch Generation
- Explicit, diff-able, atomic, reversible
- Output: code patches + delta manifest

### Phase 6: RE-AUDIT
- Restart at SEE with new artifacts
- Verify gaps closed
- Update MMD and ECL

### Phase 7: Termination
Stop when:
- All P0 invariants satisfied, OR
- No further recursion can add evidence, OR
- Operator intervenes

## Invariants
- P0: No execution claim without artifacts
- P0: No inference of state
- P0: No continuity without receipts
- P0: Failure → halt or recurse, never gloss
- P0: Recursion must be artifact-producing or stop

## Evidence Class Requirements
All proofs must declare class:
- `STATIC_CODE_ANALYSIS`: Code inspection only
- `RUNTIME_EXECUTION`: Actual execution with receipts
- `INTEGRATION_EXECUTION`: Multi-turn proof with chain
- `SIMULATED`: Synthetic/mock environment

ECL may only ALLOW "enabled" claims when proof_class ≥ RUNTIME_EXECUTION.

## Proof Schema
```json
{
  "see_block": "SEE_BLOCK_<ID>.json",
  "mmd_report": "MMD_REPORT_<ID>.json",
  "ecl_matrix": "ECL_CLAIM_MATRIX_<ID>.json",
  "patches": ["list of file paths"],
  "receipts": ["list of receipt paths"],
  "proof_class": "RUNTIME_EXECUTION|STATIC_CODE_ANALYSIS|...",
  "status": "P0_INVARIANTS_SATISFIED|PENDING|FAILED"
}
```

## Terminal Conditions
- ✅ All P0 gaps RESOLVED (not "documented")
- ✅ Integration tests executed and passed
- ✅ Evidence artifacts complete and hash-chained
- ❌ "0 P0 gaps remaining" FORBIDDEN if any items are SUBSTANTIALLY_RESOLVED or tests SKIPPED

## MMD Gap Taxonomy
- `SPEC_EXISTS_IMPLEMENTATION_MISSING`: Design complete, code absent
- `IMPLEMENTATION_EXISTS_NOT_WIRED`: Code exists, entrypoint doesn't call it
- `WIRED_NOT_EXECUTED`: Called in code, no runtime receipts
- `EXECUTED_NOT_RECEIPTED`: Ran but didn't emit proof artifacts

## ECL Claim Binding
Claims must bind to proof class:
```json
{
  "claim": "Auto-rehydration is enabled",
  "allowed_if": {
    "proof_class": "RUNTIME_EXECUTION",
    "required_artifacts": [
      "rehydrate_receipt.json",
      "gate_results.json"
    ]
  }
}
```

## Anti-Patterns (FORBIDDEN)
- ❌ Mixing static + runtime language without labels
- ❌ "PASSED" for static checks (use "static check indicates...")
- ❌ "Execution proof" for grep-based validation
- ❌ Claiming "enabled" without live receipts
- ❌ Spec-only completion (spec ≠ implementation)

## Success Criteria
Recursion terminates in artifacts, not documentation.
- Spec ≠ Enablement
- Markdown ≠ Behavior
- Audit ≠ Execution
- No closure without live receipts for claimed invariant
