# PIPE_SEE_MMD_ECL_DEBUG

**Pipeline ID**: PIPE_SEE_MMD_ECL_DEBUG
**Type**: DEBUGGING_PROTOCOL
**Authority**: VALIDATED
**Execution Model**: 5-PHASE (DISCOVER, VALIDATE, CONVERGE, DECIDE, ACT)

## Purpose
Execute governed debugging using SEE/MMD/ECL protocol to systematically identify and patch P0 CRITICAL bugs.

## Pipeline Contract

```python
@dataclass
class SeeMMDEclDebugPipeline:
    pipeline_id: str = "PIPE_SEE_MMD_ECL_DEBUG"
    phases: List[str] = field(default_factory=lambda: [
        "DISCOVER",
        "VALIDATE",
        "CONVERGE",
        "DECIDE",
        "ACT"
    ])
    segments_used: List[str] = field(default_factory=lambda: [
        "SEG_P0_DEBUG_PROTOCOL_V1",
        "SEG_EXECUTION_TEST_HARNESS_V1",
        "SEG_GOVERNANCE_BUNDLE_V1"
    ])
    required_inputs: List[str] = field(default_factory=lambda: [
        "os_root",
        "target_codebase",
        "scope_definition"
    ])
    output_artifacts: List[str] = field(default_factory=lambda: [
        "governance_bundle",
        "patch_receipts",
        "ecl_final_status",
        "execution_proof"
    ])
```

## Phase 0: DISCOVER (SEE - Sandcrawler Evidence Engine)

**Purpose**: Enumerate reality without interpretation

**Pipe Segments**:
- INGEST: Load target codebase files
- NORMALIZE: Parse code into analyzable structures
- VALIDATE: Verify files are readable and parseable

**Execution**:
```python
def phase_0_discover(os_root: Path, target_codebase: Path, scope: str) -> SEEBlock:
    """
    PHASE 0: DISCOVER - Enumerate P0 CRITICAL bugs without interpretation.

    Flow:
    1. Load all target files in scope
    2. Run static analysis (grep, AST parsing)
    3. Enumerate findings as raw observations
    4. NO interpretation or gap analysis yet

    Returns:
        SEEBlock with enumerated observations
    """
    see_block = {
        "protocol": "SEE",
        "timestamp": utcnow(),
        "scope": scope,
        "observations": []
    }

    # Example: Enumerate turn_lock.py race condition
    findings = grep_for_patterns(
        target_codebase,
        patterns=[
            r"open\(.*lock.*\"w\"\)",  # Non-atomic file writes
            r"if not.*\.exists\(\):",  # TOCTOU patterns
            r"return 0$",  # Exit code issues
        ]
    )

    for finding in findings:
        see_block["observations"].append({
            "id": generate_observation_id(),
            "file": finding.file,
            "line": finding.line,
            "pattern": finding.pattern,
            "code_snippet": finding.snippet,
            "interpretation": None  # NO INTERPRETATION YET
        })

    # Write SEE block
    see_block_path = os_root / "governance" / "audits" / f"SEE_BLOCK_{scope}.json"
    write_json(see_block_path, see_block)

    return see_block
```

## Phase 1: VALIDATE (MMD - Missing-Middle Detector)

**Purpose**: Compare exists vs must-exist, identify gaps

**Pipe Segments**:
- MAP: Map observations to must-exist requirements
- EXECUTE: Run gap detection algorithm
- VERIFY: Validate gap analysis completeness

**Execution**:
```python
def phase_1_validate(see_block: SEEBlock, os_root: Path) -> MMDReport:
    """
    PHASE 1: VALIDATE - Run MMD gap analysis.

    Flow:
    1. Load SEE block observations
    2. Compare against P0 invariants (must-exist)
    3. Identify gaps (exists but shouldn't, missing but should exist)
    4. Classify gap severity (P0/P1/P2)

    Returns:
        MMDReport with gap analysis
    """
    mmd_report = {
        "protocol": "MMD",
        "timestamp": utcnow(),
        "see_block_ref": see_block["see_block_id"],
        "gaps": []
    }

    # Define P0 invariants
    p0_invariants = {
        "turn_lock_atomic": "Turn lock MUST use atomic primitives (fcntl.flock)",
        "exit_code_reflects_failure": "Exit code MUST be non-zero on P0 failure",
        "genesis_receipt_validated": "Genesis receipt MUST be validated",
        "zip_path_validated": "Zip entries MUST be validated for path traversal",
        "sandbox_workdir_validated": "Sandbox workdir MUST be validated",
        "turn_index_documented": "turn_index.py MUST document boot_receipt dependency"
    }

    # Check each invariant against observations
    for invariant_id, invariant_text in p0_invariants.items():
        exists = check_invariant_satisfied(invariant_id, see_block)

        if not exists:
            mmd_report["gaps"].append({
                "gap_id": invariant_id,
                "severity": "P0_CRITICAL",
                "invariant": invariant_text,
                "status": "MISSING",
                "evidence": find_evidence_for_gap(invariant_id, see_block)
            })

    # Write MMD report
    mmd_report_path = os_root / "governance" / "audits" / f"MMD_REPORT_{see_block['scope']}.json"
    write_json(mmd_report_path, mmd_report)

    return mmd_report
```

## Phase 2: CONVERGE (ECL - Extraordinary Claims Law)

**Purpose**: Police what may be said based on evidence

**Pipe Segments**:
- NORMALIZE: Normalize claims to standard form
- VALIDATE: Validate claims against evidence
- LEDGER: Record ECL claim matrix

**Execution**:
```python
def phase_2_converge(mmd_report: MMDReport, os_root: Path) -> ECLClaimMatrix:
    """
    PHASE 2: CONVERGE - Generate ECL claim matrix.

    Flow:
    1. Load MMD gap analysis
    2. For each potential claim, classify as ALLOWED/CONDITIONAL/FORBIDDEN
    3. Require evidence references for all claims
    4. Generate ECL claim matrix

    Returns:
        ECLClaimMatrix with claim classifications
    """
    ecl_matrix = {
        "protocol": "ECL",
        "timestamp": utcnow(),
        "mmd_report_ref": mmd_report["report_id"],
        "claims": []
    }

    # Example claims
    potential_claims = [
        "MetaBlooms OS implements crash-safe turn locking",
        "Boot failures are reported via exit codes",
        "Receipt chain is cryptographically tamper-evident",
        "OS rehydration prevents malicious zip extraction",
        "Sandbox execution provides security isolation",
        "MetaBlooms OS is production-ready"
    ]

    for claim_text in potential_claims:
        # Check if evidence exists
        evidence = find_evidence_for_claim(claim_text, mmd_report)

        if not evidence:
            status = "FORBIDDEN"
            reason = "No evidence present"
        elif evidence["partial"]:
            status = "CONDITIONAL"
            reason = evidence["reason"]
        else:
            status = "ALLOWED"
            reason = "Full evidence present"

        ecl_matrix["claims"].append({
            "claim": claim_text,
            "status": status,
            "reason": reason,
            "evidence": evidence.get("references", []),
            "qualification": evidence.get("qualification")
        })

    # Write ECL matrix
    ecl_matrix_path = os_root / "governance" / "audits" / f"ECL_CLAIM_MATRIX_{mmd_report['scope']}.json"
    write_json(ecl_matrix_path, ecl_matrix)

    return ecl_matrix
```

## Phase 3: DECIDE (Patch Selection)

**Purpose**: Prioritize and select patches to apply

**Pipe Segments**:
- MAP: Map gaps to potential patches
- EXECUTE: Prioritize patches by P0/P1/P2
- VERIFY: Validate patch completeness

**Execution**:
```python
def phase_3_decide(mmd_report: MMDReport, os_root: Path) -> PatchPlan:
    """
    PHASE 3: DECIDE - Select patches in priority order.

    Flow:
    1. Load MMD gaps
    2. For each P0 gap, design patch
    3. Prioritize patches (P0 first)
    4. Generate patch plan

    Returns:
        PatchPlan with ordered patches
    """
    patch_plan = {
        "timestamp": utcnow(),
        "mmd_report_ref": mmd_report["report_id"],
        "patches": []
    }

    # Sort gaps by priority
    p0_gaps = [g for g in mmd_report["gaps"] if g["severity"] == "P0_CRITICAL"]

    for gap in p0_gaps:
        patch = design_patch_for_gap(gap)

        patch_plan["patches"].append({
            "patch_id": f"PATCH_{gap['gap_id']}",
            "gap_id": gap["gap_id"],
            "priority": 0,  # P0
            "target_file": patch["target_file"],
            "patch_type": patch["patch_type"],  # "CODE_CHANGE" | "DOCUMENTATION"
            "description": patch["description"]
        })

    # Write patch plan
    patch_plan_path = os_root / "governance" / "audits" / f"PATCH_PLAN_{mmd_report['scope']}.json"
    write_json(patch_plan_path, patch_plan)

    return patch_plan
```

## Phase 4: ACT (Patch Application + Re-Audit)

**Purpose**: Apply patches and re-audit with governed recursion

**Pipe Segments**:
- EXECUTE: Apply each patch in priority order
- VERIFY: Verify patch applied correctly
- LEDGER: Emit patch receipts
- EMIT: Trigger re-audit (SEE/MMD/ECL POST-PATCH)

**Execution**:
```python
def phase_4_act(patch_plan: PatchPlan, os_root: Path, target_codebase: Path) -> ActResult:
    """
    PHASE 4: ACT - Apply patches and re-audit.

    Flow:
    1. For each patch in priority order:
       a. Apply patch to target file
       b. Emit patch receipt
       c. Run verification tests
    2. After all patches applied:
       a. Re-run SEE (POST-PATCH enumeration)
       b. Re-run MMD (POST-PATCH gap analysis)
       c. Re-run ECL (POST-PATCH claim matrix)
    3. Generate governance bundle

    Returns:
        ActResult with patch results and governance bundle
    """
    patch_results = []

    # Apply each patch
    for patch in patch_plan["patches"]:
        result = apply_patch(target_codebase, patch)

        patch_results.append({
            "patch_id": patch["patch_id"],
            "status": result.status,
            "files_modified": result.files_modified
        })

        # Emit patch receipt
        emit_patch_receipt(os_root, patch, result)

    # Re-audit POST-PATCH
    see_block_post = phase_0_discover(os_root, target_codebase, f"{patch_plan['scope']}_POST_PATCH")
    mmd_report_post = phase_1_validate(see_block_post, os_root)
    ecl_matrix_post = phase_2_converge(mmd_report_post, os_root)

    # Generate execution proof
    execution_transcript = generate_execution_transcript(os_root, patch_results)
    execution_receipt = generate_execution_receipt(execution_transcript)

    # Update ECL with execution proof
    ecl_matrix_final = update_ecl_with_execution_proof(ecl_matrix_post, execution_receipt)

    # Assemble governance bundle
    bundle_path = assemble_governance_bundle(
        os_root=os_root,
        bundle_id=f"BUNDLE_{patch_plan['scope']}_{utcnow()}",
        protocol="SEE/MMD/ECL",
        purpose=f"Systematic P0 debugging: {patch_plan['scope']}",
        artifact_manifest=build_artifact_manifest_for_see_mmd_ecl(os_root, ...),
        results_summary={
            "bugs_found": len(mmd_report["gaps"]),
            "bugs_resolved": len([r for r in patch_results if r["status"] == "APPLIED"]),
            "patches_applied": len(patch_results)
        },
        ecl_status=ecl_matrix_final
    )

    return ActResult(
        patch_results=patch_results,
        governance_bundle_path=bundle_path,
        ecl_final_status=ecl_matrix_final
    )
```

## Pipeline Execution

```python
def execute_pipeline(os_root: Path, target_codebase: Path, scope: str) -> PipelineResult:
    """
    Execute complete SEE/MMD/ECL debugging pipeline.

    Returns:
        PipelineResult with governance bundle and ECL status
    """
    # Phase 0: DISCOVER (SEE)
    see_block = phase_0_discover(os_root, target_codebase, scope)

    # Phase 1: VALIDATE (MMD)
    mmd_report = phase_1_validate(see_block, os_root)

    # Phase 2: CONVERGE (ECL)
    ecl_matrix = phase_2_converge(mmd_report, os_root)

    # Phase 3: DECIDE
    patch_plan = phase_3_decide(mmd_report, os_root)

    # Phase 4: ACT (with governed recursion)
    act_result = phase_4_act(patch_plan, os_root, target_codebase)

    return PipelineResult(
        status="COMPLETED",
        governance_bundle_path=act_result.governance_bundle_path,
        ecl_final_status=act_result.ecl_final_status,
        bugs_found=len(mmd_report["gaps"]),
        bugs_resolved=len([r for r in act_result.patch_results if r["status"] == "APPLIED"])
    )
```

## Governance Rules
- P0: Pipeline MUST execute all 5 phases in order
- P0: Pipeline MUST re-audit after patch application
- P0: Pipeline MUST generate governance bundle
- P0: Pipeline MUST emit ECL final status
- P1: Pipeline SHOULD use governed recursion (patch → re-audit → terminate when P0 satisfied)

## Anti-Patterns (FORBIDDEN)
- ❌ Skipping re-audit after patching
- ❌ Claiming bugs fixed without MMD verification
- ❌ Shipping without governance bundle
- ❌ Conflating proof classes in ECL
- ❌ Overclaiming without evidence
