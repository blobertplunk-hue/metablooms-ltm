# MetaBlooms SEE Loop System

## Overview

The **SEE (Sandcrawler Evidence Engine) Loop System** is a self-governing, evidence-based recursive validation framework for AI-generated code.

## Core Paradigm

**Standard AI coding:**
```
LLM → Code → Hope it works → Manual debugging
```

**SEE Loop paradigm:**
```
LLM → Code → Sandbox → Evidence → Recursive correction → Proof of correctness
          ↑______________|
```

## Architecture

### Components

1. **Loop Controller** (`loop/see_recursive_controller_v1.py`)
   - Orchestrates bounded recursive validation
   - Enforces stop conditions
   - Manages evidence progression (E1 → E4)

2. **Sandbox Executor** (`runtime/sandbox_exec_v1.py`)
   - Runs code in isolated environment
   - Captures stdout, stderr, exit codes
   - Generates hash-verified receipts

3. **Evidence Store** (`evidence/store_v1.py`)
   - Manages evidence artifacts
   - Computes SHA256 hashes
   - Ensures immutable receipts

4. **Receipt Validator** (`evidence/receipt_validate_v1.py`)
   - Enforces receipt schema
   - Verifies hash integrity
   - Fail-closed validation

5. **Regression Tracker** (`evidence/regression_signature_v1.py`)
   - Prevents silent regressions
   - Tracks execution stability

6. **Failure Diagnoser** (`diagnostics/failure_diagnoser_v1.py`)
   - Evidence-based error classification
   - Structured failure analysis

7. **Patch Provider** (`patching/patch_provider_v1.py`)
   - Pluggable patch generation interface
   - Minimal, evidence-driven fixes

8. **Missing Middle Detector** (`validators/missing_middle_detector_v1.py`)
   - **Meta-validator** that ensures plan ↔ code ↔ evidence alignment
   - Detects systemic gaps in capability claims
   - Self-enforcing architecture

9. **SEE Loop Gate** (`preflight/gates/mb_gate_evidence_see_loop_v1.py`)
   - Preflight enforcement mechanism
   - Blocks advancement on missing middles
   - Integrates with MetaBlooms governance

## Evidence Classification

| Level | Meaning | Execution Allowed |
|-------|---------|------------------|
| **E0** | Contradicted | ❌ Forbidden |
| **E1** | No evidence yet | ⚠️ Sandbox only |
| **E2** | Partial evidence | ⚠️ With warnings |
| **E3** | Strong evidence | ✅ Normal execution |
| **E4** | Validated in system | ✅ Preferred for export |

## Loop Flow

```
1. AUTHOR CODE
   ↓ (E1 - no evidence yet)

2. EXECUTE IN SANDBOX
   ↓ (capture evidence)

3. GENERATE RECEIPT
   ↓ (hash verification)

4. VALIDATE
   ├─ SUCCESS → E3/E4 (PASS)
   └─ FAILURE → DIAGNOSE
      ↓
5. DIAGNOSE FAILURE
   ↓ (evidence-based)

6. GENERATE PATCH
   ↓ (minimal, bounded)

7. RE-EXECUTE
   ↓
   └─ LOOP (max 3 iterations)

8. STOP CONDITIONS:
   - Success + stable
   - Max iterations exceeded
   - No patch available
   - Sandbox violation
```

## Receipt Schema

Every execution produces:

```json
{
  "receipt_version": "v1",
  "task_id": "string",
  "iteration": 1,
  "command": ["python", "script.py"],
  "workdir": "/path/to/work",
  "exec": {
    "exit_code": 0,
    "duration_ms": 1234
  },
  "artifacts": [
    {
      "path": "stdout.txt",
      "sha256": "abc123..."
    }
  ],
  "environment": {
    "python": "3.11.0",
    "platform": "Linux-..."
  },
  "evidence_level_claimed": "E3"
}
```

## Missing Middle Detection

The MMD enforces four critical alignments:

1. **PLAN_CODE**: Design exists → Implementation exists
2. **CODE_EVIDENCE**: Code exists → Receipts exist
3. **EVIDENCE_GATE**: Evidence exists → Gates enforce it
4. **LOOP**: One-shot execution → Bounded retry loop

### Meta-Validation

The system can **detect its own absence**:

```python
from metablooms.validators.missing_middle_detector_v1 import detect_missing_middle

findings = detect_missing_middle("/path/to/repo")
# Returns [] if complete, or list of missing components
```

**This closes the meta-loop**: The detector enforces the existence of the loop system itself.

## Usage Example

```python
from metablooms.loop.see_recursive_controller_v1 import run_see_loop
from metablooms.runtime.sandbox_exec_v1 import sandbox_execute
from metablooms.diagnostics.failure_diagnoser_v1 import diagnose
from metablooms.patching.patch_provider_v1 import provide_patch

task_spec = {
    "task_id": "test_function_v1",
    "command": ["python", "-m", "pytest", "test_function.py"],
    "workdir": "/workspace",
    "evidence_root": "/evidence",
    "timeout": 30
}

result = run_see_loop(
    task_spec=task_spec,
    executor=sandbox_execute,
    diagnoser=diagnose,
    patch_provider=provide_patch,
    max_iterations=3
)

if result["status"] == "PASS":
    print(f"✅ Validation passed in {result['iterations']} iterations")
    print(f"Receipt: {result['final_receipt']}")
else:
    print(f"❌ Validation failed: {result['reason']}")
```

## Governance Integration

### Preflight Gate

Add to `preflight_gate_chain_v1.json`:

```json
{
  "gate_id": "GATE.EVIDENCE.SEE.LOOP.V1",
  "priority": "P1",
  "mode": "WARN",
  "module": "metablooms.preflight.gates.mb_gate_evidence_see_loop_v1",
  "callable": "run_gate",
  "description": "Blocks missing-middle gaps"
}
```

### P0 Invariant

```
INVARIANT: CODE.AUTHORSHIP.REQUIRES.SEE.LOOP

MetaBlooms MUST NOT:
- Claim code correctness
- Export code
- Promote evidence level
- Ship an OS bundle

UNLESS:
- A bounded SEE loop was attempted
- Evidence receipts exist
- Receipts validate
- GATE.EVIDENCE.SEE.LOOP.V1 passes
```

## Why This Matters

### Convergent vs. Random Walk

**Standard LLM debugging:**
- ~60% success per attempt
- Might introduce new bugs
- No guarantee of convergence
- Random walk in solution space

**SEE Loop:**
- Evidence-driven correction
- Hash-verified non-regression
- Monotonic progress toward E4
- Directed search toward correctness

### Effective "Online Learning"

```
Attempt 1: Code + Execution → Evidence
Attempt 2: Code + Evidence from 1 → Better Evidence
Attempt 3: Code + Evidence from 1+2 → Even Better Evidence
...
Attempt N: VALIDATED (E4 status)
```

### Self-Improving System

SEE reports become a **learned corpus**:

```
metablooms/see_reports/
├── BUG_001_race_condition/
│   ├── see_contradictions.json  ← "Don't do this again"
│   └── see_sources.md           ← "How we fixed it"
└── BUG_043_type_coercion/
    └── ...
```

## Testing

Run the meta-validation test:

```bash
python metablooms/validators/test_missing_middle_meta_validation.py
```

Expected output:
```
✅ PASS: All required components present
✅ Meta-loop CLOSED: MMD enforces its own requirements
```

## Implementation Status

- ✅ Loop Controller
- ✅ Sandbox Executor
- ✅ Evidence Store
- ✅ Receipt Validation
- ✅ Regression Tracker
- ✅ Failure Diagnoser
- ✅ Patch Provider Interface
- ✅ Missing Middle Detector
- ✅ SEE Loop Gate
- ✅ Meta-validation Test
- ⚠️ LLM-backed Patch Provider (pluggable, to be implemented)

## Next Steps

1. Implement LLM-backed patch provider
2. Wire gate into production preflight chain
3. Promote GATE.EVIDENCE.SEE.LOOP.V1 from WARN to BLOCK
4. Create end-to-end integration test
5. Document deployment procedures

## Key Innovation

**This system doesn't just validate code—it validates its own ability to validate code.**

The Missing Middle Detector ensures that:
- Claims require implementation
- Implementation requires evidence
- Evidence requires enforcement
- Enforcement requires gates

**The meta-loop is closed. The system is self-enforcing.**

## License

Part of MetaBlooms OS - Evidence-first AI governance system.
