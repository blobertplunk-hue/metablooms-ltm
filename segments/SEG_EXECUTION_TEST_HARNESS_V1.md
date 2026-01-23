# SEG_EXECUTION_TEST_HARNESS_V1

**Segment ID**: SEG_EXEC_TEST_V1
**Type**: VALIDATION_INFRASTRUCTURE
**Authority**: VALIDATED
**Proof Class**: RUNTIME_EXECUTION

## Purpose
Generate execution proof via static code verification or runtime tests.

## Structure

### Test Class Pattern
```python
class ExecutionTest:
    def __init__(self, os_root: Path):
        self.os_root = os_root
        self.results = []
        self.start_time = _timestamp()

    def record_result(self, test_id: str, description: str,
                     passed: bool, evidence: dict):
        """Record test result with evidence."""
        self.results.append({
            "test_id": test_id,
            "description": description,
            "passed": passed,
            "timestamp": _timestamp(),
            "evidence": evidence,
            "proof_class": "STATIC_CODE_ANALYSIS"  # or RUNTIME_EXECUTION
        })
```

### Proof Class Declaration
Every test MUST declare its proof class:
- `STATIC_CODE_ANALYSIS`: Grep, file existence, string matching
- `RUNTIME_EXECUTION`: Actual process execution with receipts
- `INTEGRATION_EXECUTION`: Multi-component interaction

### Test Execution
```python
def test_feature_implementation(self):
    """Test that feature code exists and is wired."""
    # Check implementation exists (STATIC)
    impl_path = self.os_root / "module/feature.py"
    has_impl = impl_path.exists()

    # Check code contains key functions (STATIC)
    if has_impl:
        content = impl_path.read_text()
        has_function = "def feature_impl(" in content

    self.record_result(
        "FEATURE_IMPLEMENTATION",
        "Feature implementation exists with required functions",
        has_impl and has_function,
        {
            "file": str(impl_path),
            "implementation_present": has_impl,
            "function_present": has_function,
            "proof_class": "STATIC_CODE_ANALYSIS",
            "note": "Runtime execution required for full verification"
        }
    )
```

### Transcript Generation
```python
def generate_transcript(self):
    """Generate execution transcript with proof class labels."""
    passed_tests = [r for r in self.results if r["passed"] is True]
    failed_tests = [r for r in self.results if r["passed"] is False]
    skipped_tests = [r for r in self.results if r["passed"] is None]

    # Aggregate proof classes
    proof_classes = set(r["evidence"].get("proof_class", "UNKNOWN")
                       for r in self.results)

    transcript = {
        "execution_id": f"EXEC_{_timestamp()}",
        "timestamp_start": self.start_time,
        "timestamp_end": _timestamp(),
        "verification_method": list(proof_classes),
        "results": self.results,
        "summary": {
            "total_tests": len(self.results),
            "passed": len(passed_tests),
            "failed": len(failed_tests),
            "skipped": len(skipped_tests)
        },
        "ecl_status": self._compute_ecl_status()
    }
    return transcript

def _compute_ecl_status(self):
    """Compute ECL status based on proof classes used."""
    has_runtime = any(
        "RUNTIME_EXECUTION" in r["evidence"].get("proof_class", "")
        for r in self.results
    )

    if has_runtime and all(r["passed"] for r in self.results):
        return "ALLOWED"
    elif not has_runtime:
        return "CONDITIONAL_STATIC_ONLY"
    else:
        return "FORBIDDEN_TESTS_FAILED"
```

### Receipt Generation
```python
def generate_receipt(self, transcript: dict):
    """Generate cryptographic receipt of execution."""
    receipt = {
        "receipt_type": "EXECUTION_RECEIPT",
        "execution_id": transcript["execution_id"],
        "timestamp": _timestamp(),
        "transcript_hash": _sha256(json.dumps(transcript, sort_keys=True)),
        "verification_methods": transcript["verification_method"],
        "tests_passed": transcript["summary"]["passed"],
        "tests_failed": transcript["summary"]["failed"],
        "runtime_tests_completed": "RUNTIME_EXECUTION" in transcript["verification_method"]
    }

    receipt["receipt_hash"] = _sha256(
        json.dumps({k: v for k, v in receipt.items()
                   if k != "receipt_hash"}, sort_keys=True)
    )

    return receipt
```

## Output Artifacts
1. `EXECUTION_TRANSCRIPT.json` - Complete test results with proof classes
2. `EXECUTION_RECEIPT.json` - Cryptographic proof of execution
3. Individual test evidence files as needed

## ECL Integration
- Static-only tests → claims must be qualified ("static check indicates...")
- Runtime tests → claims can be unqualified if all pass
- Mixed tests → use most conservative proof class for overall status

## Governance Rules
- P0: Transcript MUST declare verification_method (proof class)
- P0: Receipt MUST hash transcript for integrity
- P0: No "PASSED" language for STATIC_CODE_ANALYSIS (use "validated statically")
- P1: Runtime tests should produce actual receipts from system under test
