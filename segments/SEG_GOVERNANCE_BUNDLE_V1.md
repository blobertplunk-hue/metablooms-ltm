# SEG_GOVERNANCE_BUNDLE_V1

**Segment ID**: SEG_GOV_BUNDLE_V1
**Type**: GOVERNANCE_INFRASTRUCTURE
**Authority**: VALIDATED
**Proof Class**: INTEGRATION_EXECUTION

## Purpose
Assemble complete audit artifacts for governed debugging or development sessions.

## Governance Bundle Schema

```python
@dataclass
class GovernanceBundle:
    bundle_id: str
    timestamp: str
    protocol: str  # "SEE/MMD/ECL" | "SHIP_WITH_ROLLBACK" | "HEALING"
    purpose: str
    deliverables: Dict[str, List[str]]  # Category -> artifact paths
    results: Dict[str, Any]  # Summary metrics
    ecl_final_status: Dict[str, Any]  # ECL claims and status
    governance_notes: Dict[str, str]
    next_steps: List[Dict]
```

## Bundle Assembly

```python
def assemble_governance_bundle(
    os_root: Path,
    bundle_id: str,
    protocol: str,
    purpose: str,
    artifact_manifest: Dict[str, List[Path]],
    results_summary: Dict[str, Any],
    ecl_status: Dict[str, Any]
) -> Path:
    """
    Assemble governance bundle with all audit artifacts.

    Flow:
    1. Create bundle directory structure
    2. Copy/collect all artifacts to bundle directory
    3. Generate bundle manifest
    4. Validate artifact completeness
    5. Compute bundle hash
    6. Write bundle to governance/bundles/

    Returns:
        Path to bundle manifest
    """
    bundle_dir = os_root / "governance" / "bundles" / bundle_id
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # Copy artifacts to bundle directory
    deliverables = {}

    for category, artifact_paths in artifact_manifest.items():
        category_artifacts = []

        for artifact_path in artifact_paths:
            if artifact_path.exists():
                # Copy artifact to bundle
                relative_path = artifact_path.relative_to(os_root)
                bundle_artifact_path = bundle_dir / relative_path

                bundle_artifact_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(artifact_path, bundle_artifact_path)

                category_artifacts.append(str(relative_path))
            else:
                # Missing artifact - record as missing
                category_artifacts.append(f"MISSING: {artifact_path}")

        deliverables[category] = category_artifacts

    # Generate bundle manifest
    bundle_manifest = {
        "bundle_id": bundle_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "protocol": protocol,
        "purpose": purpose,
        "deliverables": deliverables,
        "results": results_summary,
        "ecl_final_status": ecl_status,
        "governance_notes": {
            "protocol_adherence": _assess_protocol_adherence(protocol, deliverables),
            "artifact_backing": _assess_artifact_completeness(deliverables),
            "execution_proof": _assess_execution_proof(results_summary),
            "next_requirement": _determine_next_requirement(ecl_status)
        },
        "next_steps": []
    }

    # Compute bundle hash
    bundle_hash = sha256_json(bundle_manifest)
    bundle_manifest["bundle_hash"] = bundle_hash

    # Write bundle manifest
    bundle_manifest_path = bundle_dir / f"{bundle_id}.json"
    bundle_manifest_path.write_text(
        json.dumps(bundle_manifest, indent=2),
        encoding="utf-8"
    )

    return bundle_manifest_path


def _assess_protocol_adherence(protocol: str, deliverables: Dict) -> str:
    """
    Assess whether bundle adheres to declared protocol.

    Returns:
        "FULL" | "PARTIAL" | "NONE"
    """
    if protocol == "SEE/MMD/ECL":
        required = ["pre_patch_analysis", "post_patch_analysis", "final_ecl"]
        has_all = all(cat in deliverables for cat in required)
        return "FULL" if has_all else "PARTIAL"

    elif protocol == "SHIP_WITH_ROLLBACK":
        required = ["ship_receipts", "conflict_detection", "rollback_artifacts"]
        has_all = all(cat in deliverables for cat in required)
        return "FULL" if has_all else "PARTIAL"

    elif protocol == "HEALING":
        required = ["healing_receipts", "rollback_snapshots", "validation_artifacts"]
        has_all = all(cat in deliverables for cat in required)
        return "FULL" if has_all else "PARTIAL"

    else:
        return "UNKNOWN_PROTOCOL"


def _assess_artifact_completeness(deliverables: Dict) -> str:
    """
    Assess whether all expected artifacts are present.

    Returns:
        "COMPLETE" | "PARTIAL" | "MISSING"
    """
    total_artifacts = 0
    missing_artifacts = 0

    for category, artifacts in deliverables.items():
        for artifact in artifacts:
            total_artifacts += 1
            if "MISSING:" in artifact:
                missing_artifacts += 1

    if missing_artifacts == 0:
        return "COMPLETE"
    elif missing_artifacts < total_artifacts:
        return "PARTIAL"
    else:
        return "MISSING"


def _assess_execution_proof(results: Dict) -> str:
    """
    Assess level of execution proof provided.

    Returns:
        "RUNTIME_EXECUTION" | "STATIC_ANALYSIS_ONLY" | "NONE"
    """
    verification_method = results.get("verification_method", "").upper()

    if "RUNTIME" in verification_method or "INTEGRATION" in verification_method:
        return "RUNTIME_EXECUTION"
    elif "STATIC" in verification_method:
        return "STATIC_ANALYSIS_ONLY"
    else:
        return "NONE"


def _determine_next_requirement(ecl_status: Dict) -> str:
    """
    Determine next requirement based on ECL status.

    Returns:
        Human-readable next requirement
    """
    if ecl_status.get("runtime_tests_required") and not ecl_status.get("runtime_tests_completed"):
        return "Runtime execution with full OS setup to complete verification"

    conditional_claims = ecl_status.get("conditional_claims", 0)

    if conditional_claims > 0:
        return "Resolve conditional claims to upgrade to ALLOWED status"

    forbidden_claims = ecl_status.get("forbidden_claims", 0)

    if forbidden_claims > 0:
        return "Gather evidence to upgrade FORBIDDEN claims"

    return "All requirements satisfied"
```

## Artifact Manifest Builder

```python
def build_artifact_manifest_for_see_mmd_ecl(
    os_root: Path,
    audit_dir: Path
) -> Dict[str, List[Path]]:
    """
    Build artifact manifest for SEE/MMD/ECL debugging session.

    Returns:
        Dictionary mapping categories to artifact paths
    """
    return {
        "pre_patch_analysis": [
            audit_dir / "SEE_BLOCK_P0_CRITICAL.json",
            audit_dir / "MMD_REPORT_P0_CRITICAL.json",
            audit_dir / "ECL_CLAIM_MATRIX_P0.json"
        ],
        "post_patch_analysis": [
            audit_dir / "SEE_BLOCK_P0_CRITICAL_POST_PATCH.json",
            audit_dir / "MMD_REPORT_P0_CRITICAL_POST_PATCH.json",
            audit_dir / "ECL_CLAIM_MATRIX_P0_POST_PATCH.json"
        ],
        "execution_proof": [
            audit_dir / "execution" / "EXECUTION_TRANSCRIPT.json",
            audit_dir / "execution" / "EXECUTION_RECEIPT.json"
        ],
        "final_ecl": [
            audit_dir / "ECL_CLAIM_MATRIX_FINAL.json"
        ],
        "documentation": [
            audit_dir / "DEBUG_SESSION_SUMMARY.md",
            audit_dir / "AUDIT_MANIFEST.json"
        ],
        "specifications": [
            os_root / "governance" / "specs" / "TURN_LOCAL_REHYDRATE_SPEC_V1.md"
        ],
        "test_harness": [
            os_root / "POST_PATCH_EXECUTION_TEST.py"
        ]
    }


def build_artifact_manifest_for_healing(
    os_root: Path,
    healing_id: str
) -> Dict[str, List[Path]]:
    """
    Build artifact manifest for healing session.

    Returns:
        Dictionary mapping categories to artifact paths
    """
    healing_dir = os_root / "ledgers" / "healing"
    rollback_dir = os_root / "ledgers" / "healing_rollbacks" / healing_id

    return {
        "healing_receipts": [
            healing_dir / f"{healing_id}.json"
        ],
        "rollback_snapshots": [
            rollback_dir / "rollback_manifest.json"
        ],
        "validation_artifacts": [
            healing_dir / f"{healing_id}_preconditions.json",
            healing_dir / f"{healing_id}_postconditions.json"
        ]
    }


def build_artifact_manifest_for_shipping(
    os_root: Path,
    ship_id: str
) -> Dict[str, List[Path]]:
    """
    Build artifact manifest for shipping session.

    Returns:
        Dictionary mapping categories to artifact paths
    """
    ship_ledger_dir = os_root / "ledgers" / "ships"
    staging_dir = os_root / "staging" / ship_id

    return {
        "ship_receipts": [
            ship_ledger_dir / f"{ship_id}.json"
        ],
        "conflict_detection": [
            staging_dir / "conflict_report.json"
        ],
        "validation_artifacts": [
            staging_dir / "validation_results.json"
        ],
        "rollback_artifacts": [
            staging_dir / "rollback_snapshot.json"
        ]
    }
```

## Bundle Validation

```python
def validate_governance_bundle(bundle_manifest_path: Path) -> BundleValidationResult:
    """
    Validate governance bundle for completeness and integrity.

    Validates:
    1. Bundle manifest exists and is valid JSON
    2. All declared artifacts exist
    3. Bundle hash is valid
    4. Protocol adherence is at least PARTIAL
    5. Artifact backing is at least PARTIAL

    Returns:
        BundleValidationResult with status and any errors
    """
    if not bundle_manifest_path.exists():
        return BundleValidationResult(
            valid=False,
            reason="Bundle manifest does not exist"
        )

    try:
        bundle = json.loads(bundle_manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        return BundleValidationResult(
            valid=False,
            reason=f"Failed to parse bundle manifest: {e}"
        )

    # Validate required fields
    required_fields = [
        "bundle_id", "timestamp", "protocol", "purpose",
        "deliverables", "results", "ecl_final_status",
        "governance_notes", "bundle_hash"
    ]

    for field in required_fields:
        if field not in bundle:
            return BundleValidationResult(
                valid=False,
                reason=f"Bundle missing required field: {field}"
            )

    # Validate bundle hash
    bundle_without_hash = {k: v for k, v in bundle.items() if k != "bundle_hash"}
    computed_hash = sha256_json(bundle_without_hash)

    if bundle["bundle_hash"] != computed_hash:
        return BundleValidationResult(
            valid=False,
            reason=f"Bundle hash mismatch: expected {bundle['bundle_hash']}, got {computed_hash}"
        )

    # Validate artifacts exist
    bundle_dir = bundle_manifest_path.parent
    missing_artifacts = []

    for category, artifacts in bundle["deliverables"].items():
        for artifact_path_str in artifacts:
            if "MISSING:" in artifact_path_str:
                missing_artifacts.append(artifact_path_str)
                continue

            artifact_path = bundle_dir / artifact_path_str
            if not artifact_path.exists():
                missing_artifacts.append(artifact_path_str)

    if missing_artifacts:
        return BundleValidationResult(
            valid=False,
            reason=f"Missing artifacts: {', '.join(missing_artifacts)}"
        )

    # Validate protocol adherence
    protocol_adherence = bundle["governance_notes"].get("protocol_adherence", "NONE")

    if protocol_adherence == "NONE":
        return BundleValidationResult(
            valid=False,
            reason="Bundle does not adhere to declared protocol"
        )

    # Validate artifact backing
    artifact_backing = bundle["governance_notes"].get("artifact_backing", "MISSING")

    if artifact_backing == "MISSING":
        return BundleValidationResult(
            valid=False,
            reason="Bundle has no artifact backing"
        )

    return BundleValidationResult(
        valid=True,
        bundle_id=bundle["bundle_id"],
        protocol=bundle["protocol"],
        artifact_count=sum(len(arts) for arts in bundle["deliverables"].values()),
        protocol_adherence=protocol_adherence,
        artifact_backing=artifact_backing
    )
```

## Bundle Querying

```python
def list_governance_bundles(os_root: Path) -> List[Dict]:
    """
    List all governance bundles with summary info.

    Returns:
        List of bundle summaries (id, timestamp, protocol, status)
    """
    bundles_dir = os_root / "governance" / "bundles"

    if not bundles_dir.exists():
        return []

    bundle_summaries = []

    for bundle_dir in bundles_dir.iterdir():
        if not bundle_dir.is_dir():
            continue

        manifest_path = bundle_dir / f"{bundle_dir.name}.json"

        if not manifest_path.exists():
            continue

        try:
            bundle = json.loads(manifest_path.read_text(encoding="utf-8"))

            bundle_summaries.append({
                "bundle_id": bundle["bundle_id"],
                "timestamp": bundle["timestamp"],
                "protocol": bundle["protocol"],
                "purpose": bundle["purpose"],
                "ecl_status": bundle["ecl_final_status"].get("production_ready_status", "UNKNOWN")
            })
        except Exception:
            continue

    # Sort by timestamp (newest first)
    bundle_summaries.sort(key=lambda b: b["timestamp"], reverse=True)

    return bundle_summaries


def get_bundle_by_id(os_root: Path, bundle_id: str) -> Optional[Dict]:
    """
    Retrieve specific governance bundle by ID.

    Returns:
        Bundle manifest dict, or None if not found
    """
    bundle_path = os_root / "governance" / "bundles" / bundle_id / f"{bundle_id}.json"

    if not bundle_path.exists():
        return None

    return json.loads(bundle_path.read_text(encoding="utf-8"))
```

## Bundle Export

```python
def export_bundle_to_archive(
    bundle_manifest_path: Path,
    output_path: Path
) -> Path:
    """
    Export governance bundle to portable archive (zip).

    Includes:
    - Bundle manifest
    - All artifacts referenced in deliverables
    - README with bundle overview

    Returns:
        Path to created archive
    """
    bundle_dir = bundle_manifest_path.parent
    bundle = json.loads(bundle_manifest_path.read_text(encoding="utf-8"))

    # Create zip archive
    import zipfile

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add bundle manifest
        zipf.write(
            bundle_manifest_path,
            arcname=f"{bundle['bundle_id']}.json"
        )

        # Add all artifacts
        for category, artifacts in bundle["deliverables"].items():
            for artifact_path_str in artifacts:
                if "MISSING:" in artifact_path_str:
                    continue

                artifact_path = bundle_dir / artifact_path_str
                if artifact_path.exists():
                    zipf.write(
                        artifact_path,
                        arcname=artifact_path_str
                    )

        # Add README
        readme_content = _generate_bundle_readme(bundle)
        zipf.writestr("README.md", readme_content)

    return output_path


def _generate_bundle_readme(bundle: Dict) -> str:
    """Generate README for governance bundle export."""
    return f"""# Governance Bundle: {bundle['bundle_id']}

**Protocol**: {bundle['protocol']}
**Timestamp**: {bundle['timestamp']}
**Purpose**: {bundle['purpose']}

## Deliverables

{_format_deliverables(bundle['deliverables'])}

## Results Summary

{json.dumps(bundle['results'], indent=2)}

## ECL Final Status

{json.dumps(bundle['ecl_final_status'], indent=2)}

## Governance Notes

- **Protocol Adherence**: {bundle['governance_notes']['protocol_adherence']}
- **Artifact Backing**: {bundle['governance_notes']['artifact_backing']}
- **Execution Proof**: {bundle['governance_notes']['execution_proof']}
- **Next Requirement**: {bundle['governance_notes']['next_requirement']}

## Next Steps

{_format_next_steps(bundle.get('next_steps', []))}
"""


def _format_deliverables(deliverables: Dict) -> str:
    """Format deliverables for README."""
    lines = []
    for category, artifacts in deliverables.items():
        lines.append(f"### {category}")
        for artifact in artifacts:
            lines.append(f"- {artifact}")
        lines.append("")
    return "\n".join(lines)


def _format_next_steps(next_steps: List[Dict]) -> str:
    """Format next steps for README."""
    if not next_steps:
        return "No next steps defined."

    lines = []
    for step in next_steps:
        lines.append(f"{step['step']}. {step['action']} (Owner: {step['owner']}, Status: {step['status']})")
    return "\n".join(lines)
```

## Governance Rules
- P0: All governed debugging sessions MUST produce bundle
- P0: Bundle MUST include manifest with hash
- P0: Bundle MUST reference all audit artifacts
- P1: Bundle MUST be validated before distribution
- P1: Bundle MUST include ECL final status
- P2: Bundle SHOULD be exportable to portable archive

## Anti-Patterns (FORBIDDEN)
- ❌ Distributing bundles without manifest
- ❌ Claiming bundle is complete when artifacts are missing
- ❌ Modifying bundle after hash is computed
- ❌ Deleting bundle before retention period ends
- ❌ Bundle without ECL status
