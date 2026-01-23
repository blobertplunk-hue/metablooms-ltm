# SEG_METABLOOMS_PROMOTION_GATE_V1

**Segment ID**: SEG_MB_PROMOTION_V1
**Type**: GOVERNANCE_INFRASTRUCTURE
**Authority**: PRODUCTION_IMPLEMENTATION
**Proof Class**: RUNTIME_EXECUTION
**Source**: MetaBlooms OS `/home/user/metablooms-os-debug/metablooms/gates/enforced_promotion_gate/`

## Purpose
Document the comprehensive enforced promotion gate that validates internal SEE, external items, MMD anomaly detection, and evidence packing before allowing promotion.

## Core Module: runner.py

### Main Promotion Flow

```python
def run(
    candidate_path: Path,
    mode: str,  # "CANONICAL" | "TRUSTED" | "EXPERIMENTAL"
    evidence_pack_path: Path
) -> PromotionResult:
    """
    Execute enforced promotion gate with full workflow.

    Contract: Always writes evidence pack; raises PromotionBlocked on BLOCK

    Flow:
    1. Resolve promotion mode
    2. Run internal SEE verification
    3. Validate external items minimum
    4. Run MMD anomaly detection
    5. Generate evidence pack
    6. Enforce decision (BLOCK/ALLOW)
    7. Return result

    Returns:
        PromotionResult with decision and evidence

    Raises:
        PromotionBlocked: If promotion rejected
    """
    # 1. Resolve mode
    resolved_mode = mode.resolver.resolve_mode(mode)

    # 2. Internal SEE verification
    see_internal_result = see.internal.see_internal(
        candidate_path=candidate_path,
        policy_bundle=resolved_mode.policy_bundle
    )

    if not see_internal_result.passed:
        raise PromotionBlocked(
            f"SEE internal verification failed: {see_internal_result.reason}"
        )

    # 3. External items validation
    try:
        see.external.validate_external_items_minimum(
            candidate_path=candidate_path,
            min_items=resolved_mode.min_external_items
        )
    except ExternalItemsInsufficientError as e:
        raise PromotionBlocked(f"External items insufficient: {e}")

    # 4. MMD anomaly detection
    mmd_result = mmd.detectors.mmd_detect(
        candidate_path=candidate_path,
        prior_baseline=load_prior_baseline()
    )

    if mmd_result.anomalies_found:
        # Decision point: block or warn?
        if resolved_mode.mmd_blocking:
            raise PromotionBlocked(
                f"MMD anomalies detected: {mmd_result.anomalies}"
            )
        else:
            # Log warning but proceed
            log_warning(f"MMD anomalies (non-blocking): {mmd_result.anomalies}")

    # 5. Generate evidence pack
    evidence_pack = evidence.writer.EvidencePack(
        see_internal=see_internal_result,
        external_items=load_external_items(candidate_path),
        mmd_result=mmd_result,
        mode=resolved_mode.name
    )

    evidence_pack.write(evidence_pack_path)

    # 6. Enforce decision
    decision = enforcement.consequence_handler.enforce_decision(
        evidence_pack=evidence_pack,
        mode=resolved_mode
    )

    if decision == "BLOCK":
        raise PromotionBlocked("Promotion blocked by consequence handler")

    # 7. Success
    return PromotionResult(
        decision="ALLOW",
        evidence_pack_path=evidence_pack_path,
        mode=resolved_mode.name
    )
```

## Submodules

### see/internal.py

**Purpose**: Internal SEE verification of candidate against policy

```python
@dataclass
class SEEInternalResult:
    passed: bool
    reason: Optional[str]
    violations: List[Dict]

def see_internal(
    candidate_path: Path,
    policy_bundle: Dict
) -> SEEInternalResult:
    """
    Verify candidate against internal policy bundle.

    Checks:
    1. Required files present
    2. Forbidden patterns absent
    3. Code quality gates passed
    4. Schema validation passed

    Returns:
        SEEInternalResult with pass/fail status
    """
    violations = []

    # Check required files
    for required_file in policy_bundle.get("required_files", []):
        file_path = candidate_path / required_file
        if not file_path.exists():
            violations.append({
                "type": "MISSING_REQUIRED_FILE",
                "file": required_file
            })

    # Check forbidden patterns
    for pattern in policy_bundle.get("forbidden_patterns", []):
        matches = grep_pattern(candidate_path, pattern)
        if matches:
            violations.append({
                "type": "FORBIDDEN_PATTERN",
                "pattern": pattern,
                "matches": matches
            })

    # Check code quality
    for gate_name in policy_bundle.get("quality_gates", []):
        gate_result = run_quality_gate(candidate_path, gate_name)
        if not gate_result.passed:
            violations.append({
                "type": "QUALITY_GATE_FAILED",
                "gate": gate_name,
                "reason": gate_result.reason
            })

    if violations:
        return SEEInternalResult(
            passed=False,
            reason=f"{len(violations)} violations found",
            violations=violations
        )

    return SEEInternalResult(passed=True, reason=None, violations=[])
```

### see/external.py

**Purpose**: Validate external items meet minimum requirements

```python
def validate_external_items_minimum(
    candidate_path: Path,
    min_items: int = 3
) -> None:
    """
    Validate candidate has minimum external evidence items.

    External items:
    - Test results from external CI
    - Security scan reports
    - Peer review receipts
    - Integration test receipts

    Raises:
        ExternalItemsInsufficientError: If < min_items found
    """
    external_items_path = candidate_path / "external_evidence"

    if not external_items_path.exists():
        raise ExternalItemsInsufficientError(
            "No external evidence directory found"
        )

    items = list(external_items_path.glob("*.json"))

    if len(items) < min_items:
        raise ExternalItemsInsufficientError(
            f"External items insufficient: {len(items)} < {min_items}"
        )

    # Validate each item has SHA256 and source
    for item_path in items:
        item = json.loads(item_path.read_text())

        if "sha256" not in item:
            raise ExternalItemsInsufficientError(
                f"External item missing sha256: {item_path}"
            )

        if "source" not in item:
            raise ExternalItemsInsufficientError(
                f"External item missing source: {item_path}"
            )
```

### mmd/detectors.py

**Purpose**: Multi-modal drift detection for anomaly identification

```python
@dataclass
class MMDResult:
    anomalies_found: bool
    anomalies: List[Dict]

def mmd_detect(
    candidate_path: Path,
    prior_baseline: Dict
) -> MMDResult:
    """
    Detect anomalies via multi-modal drift analysis.

    Detection modes:
    1. Content hash drift (files changed unexpectedly)
    2. API surface drift (public APIs changed)
    3. Dependency drift (dependencies changed)
    4. Behavior drift (tests behave differently)

    Returns:
        MMDResult with anomalies list
    """
    anomalies = []

    # 1. Content hash drift
    current_hashes = compute_file_hashes(candidate_path)
    baseline_hashes = prior_baseline.get("file_hashes", {})

    for file_path, current_hash in current_hashes.items():
        if file_path in baseline_hashes:
            if baseline_hashes[file_path] != current_hash:
                anomalies.append({
                    "type": "CONTENT_HASH_DRIFT",
                    "file": file_path,
                    "baseline_hash": baseline_hashes[file_path],
                    "current_hash": current_hash
                })

    # 2. API surface drift
    current_api_surface = extract_api_surface(candidate_path)
    baseline_api_surface = prior_baseline.get("api_surface", [])

    removed_apis = set(baseline_api_surface) - set(current_api_surface)
    if removed_apis:
        anomalies.append({
            "type": "API_SURFACE_DRIFT",
            "removed_apis": list(removed_apis)
        })

    # 3. Dependency drift
    current_deps = extract_dependencies(candidate_path)
    baseline_deps = prior_baseline.get("dependencies", {})

    for dep_name, current_version in current_deps.items():
        if dep_name in baseline_deps:
            if baseline_deps[dep_name] != current_version:
                anomalies.append({
                    "type": "DEPENDENCY_DRIFT",
                    "dependency": dep_name,
                    "baseline_version": baseline_deps[dep_name],
                    "current_version": current_version
                })

    return MMDResult(
        anomalies_found=len(anomalies) > 0,
        anomalies=anomalies
    )
```

### evidence/writer.py

**Purpose**: Generate and write evidence packs for promotion decisions

```python
class EvidencePack:
    """Evidence pack for promotion decision."""

    def __init__(
        self,
        see_internal: SEEInternalResult,
        external_items: List[Dict],
        mmd_result: MMDResult,
        mode: str
    ):
        self.see_internal = see_internal
        self.external_items = external_items
        self.mmd_result = mmd_result
        self.mode = mode
        self.timestamp = utcnow()

    def write(self, evidence_pack_path: Path) -> None:
        """
        Write evidence pack to disk.

        Evidence Pack Structure:
        {
          "timestamp_utc": "2026-01-23T12:00:00Z",
          "mode": "CANONICAL",
          "see_internal": {
            "passed": true,
            "violations": []
          },
          "external_items": [
            {"source": "CI", "sha256": "abc123..."},
            {"source": "SECURITY_SCAN", "sha256": "def456..."}
          ],
          "mmd_result": {
            "anomalies_found": false,
            "anomalies": []
          },
          "evidence_pack_hash": "ghi789..."
        }
        """
        pack = {
            "timestamp_utc": self.timestamp,
            "mode": self.mode,
            "see_internal": {
                "passed": self.see_internal.passed,
                "violations": self.see_internal.violations
            },
            "external_items": self.external_items,
            "mmd_result": {
                "anomalies_found": self.mmd_result.anomalies_found,
                "anomalies": self.mmd_result.anomalies
            }
        }

        pack_hash = sha256_json(pack)
        pack["evidence_pack_hash"] = pack_hash

        evidence_pack_path.write_text(
            json.dumps(pack, indent=2),
            encoding="utf-8"
        )
```

### enforcement/consequence_handler.py

**Purpose**: Enforce promotion decisions based on evidence

```python
class PromotionBlocked(Exception):
    """Raised when promotion is blocked."""
    pass

def enforce_decision(
    evidence_pack: EvidencePack,
    mode: PromotionMode
) -> str:
    """
    Enforce promotion decision based on evidence.

    Decision Logic:
    - CANONICAL mode: Zero tolerance (block on any violation)
    - TRUSTED mode: Low tolerance (block on P0 violations only)
    - EXPERIMENTAL mode: High tolerance (warn only)

    Returns:
        "ALLOW" | "BLOCK"
    """
    if mode.name == "CANONICAL":
        # Zero tolerance
        if not evidence_pack.see_internal.passed:
            return "BLOCK"

        if len(evidence_pack.external_items) < 3:
            return "BLOCK"

        if evidence_pack.mmd_result.anomalies_found:
            return "BLOCK"

        return "ALLOW"

    elif mode.name == "TRUSTED":
        # Low tolerance (P0 only)
        p0_violations = [
            v for v in evidence_pack.see_internal.violations
            if v.get("severity") == "P0"
        ]

        if p0_violations:
            return "BLOCK"

        return "ALLOW"

    elif mode.name == "EXPERIMENTAL":
        # High tolerance (warn only)
        return "ALLOW"

    else:
        # Unknown mode - fail closed
        return "BLOCK"
```

### mode/resolver.py

**Purpose**: Resolve promotion mode configuration

```python
@dataclass
class PromotionMode:
    name: str
    policy_bundle: Dict
    min_external_items: int
    mmd_blocking: bool

def resolve_mode(mode: str) -> PromotionMode:
    """
    Resolve promotion mode to configuration.

    Modes:
    - CANONICAL: Highest standards (production)
    - TRUSTED: Medium standards (staging)
    - EXPERIMENTAL: Low standards (dev/test)

    Returns:
        PromotionMode with configuration
    """
    if mode == "CANONICAL":
        return PromotionMode(
            name="CANONICAL",
            policy_bundle=load_canonical_policy(),
            min_external_items=3,
            mmd_blocking=True
        )

    elif mode == "TRUSTED":
        return PromotionMode(
            name="TRUSTED",
            policy_bundle=load_trusted_policy(),
            min_external_items=2,
            mmd_blocking=False
        )

    elif mode == "EXPERIMENTAL":
        return PromotionMode(
            name="EXPERIMENTAL",
            policy_bundle=load_experimental_policy(),
            min_external_items=0,
            mmd_blocking=False
        )

    else:
        raise ValueError(f"Unknown promotion mode: {mode}")
```

## CLI Interface: cli.py

```python
def main():
    """Command-line interface for promotion gate."""
    parser = argparse.ArgumentParser(description="Run enforced promotion gate")
    parser.add_argument("candidate_path", type=Path)
    parser.add_argument("--mode", choices=["CANONICAL", "TRUSTED", "EXPERIMENTAL"], required=True)
    parser.add_argument("--evidence-pack", type=Path, required=True)

    args = parser.parse_args()

    try:
        result = runner.run(
            candidate_path=args.candidate_path,
            mode=args.mode,
            evidence_pack_path=args.evidence_pack
        )

        print(f"Promotion ALLOWED: {result.mode}")
        print(f"Evidence pack: {result.evidence_pack_path}")
        sys.exit(0)

    except PromotionBlocked as e:
        print(f"Promotion BLOCKED: {e}", file=sys.stderr)
        sys.exit(1)
```

## Integration with Core

```python
# From core/promotion.py
def promote(candidate_path: Path, mode: str = "CANONICAL") -> Path:
    """
    Promote candidate to registry.

    Delegates to enforced_promotion_gate.run()

    Returns:
        Path to promoted artifact in registry

    Raises:
        PromotionBlocked: If gate rejects
    """
    evidence_pack_path = candidate_path / "promotion_evidence_pack.json"

    # Run enforced gate
    gates.enforced_promotion_gate.run(
        candidate_path=candidate_path,
        mode=mode,
        evidence_pack_path=evidence_pack_path
    )

    # If we reach here, promotion allowed
    return _copy_to_registry(candidate_path)
```

## Governance Rules
- P0: Promotion gate MUST always write evidence pack
- P0: Promotion gate MUST be fail-closed (block on uncertainty)
- P0: Promotion MUST run internal SEE verification
- P0: Promotion MUST validate external items minimum
- P1: Promotion SHOULD run MMD anomaly detection
- P1: Promotion decisions SHOULD be mode-dependent

## Anti-Patterns (FORBIDDEN)
- ❌ Bypassing promotion gate
- ❌ Skipping evidence pack generation
- ❌ Promoting without external items
- ❌ Ignoring MMD anomalies in CANONICAL mode
- ❌ Modifying evidence pack after generation
- ❌ Silently allowing promotions on violations
