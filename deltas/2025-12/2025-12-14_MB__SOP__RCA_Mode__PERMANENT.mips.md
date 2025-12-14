MIPS_HEADER:
  artifact_id: MB__SOP__RCA_Mode__PERMANENT__2025-12-14
  parent_bundle: MB__GOVERNANCE__FOUNDATION
  version: v1
  timestamp_utc: 2025-12-14T20:38:29Z
  content_type: text/markdown
  councils: ["Auditor", "Architect", "Recorder"]
  sha256: eea7652df28abb07d97e20957bafb0c7943e9280dc81587536be252a13da7380
  evidence_chain: []
  links: []
BODY:

# MetaBlooms RCA Mode — Permanent Standard Operating Procedure (SOP)

## Status
**PERMANENT • MANDATORY • AUTO‑ENFORCED**

This SOP defines Root Cause Analysis (RCA) as an execution **mode**, not advice.
When RCA Mode is active, all non‑diagnostic work is halted until exit criteria are met.

---

## 1. Purpose
Prevent ad‑hoc fixes, assumption stacking, and user‑burdened debugging by enforcing a deterministic,
evidence‑driven recovery loop whenever system behavior deviates from intent.

---

## 2. RCA Triggers (Any ONE activates RCA Mode)
RCA Mode **must** activate immediately when any trigger fires:

- **R1 Repetition**: Same component patched ≥2 times in a session.
- **R2 Contradiction**: A test or script contradicts an authored rule or gate.
- **R3 Toolchain Drift**: Missing tool, path, permission, or interactive prompt appears.
- **R4 Implausibility**: Output violates sanity checks (e.g., “replace OS” with tiny artifacts).
- **R5 User Escalation**: User reports confusion, wasted effort, or misalignment.
- **R6 Evidence Gap**: Success claimed without logs, diffs, or PASS/FAIL criteria.
- **R7 Gate Failure**: CSRG returns HALT_RCA or ALLOW_WITH_FIXES and fixes aren’t applied.

Activation is automatic; urgency does not override RCA.

---

## 3. RCA Mode Lock (What is NOT allowed)
While RCA Mode is active, the following are **forbidden**:

- New features, refactors, or optimizations
- Additional patches to the failing component
- Tool installation without preflight proof
- “Try this” or “one more change” behavior
- Shifting manual work to the user

Only diagnostic actions listed below are allowed.

---

## 4. Allowed Actions During RCA (In Order)
Actions must be executed sequentially. Skipping steps is not permitted.

### Step A — Scope Freeze
- Identify failing surface(s): governance, toolchain, test, execution.
- Declare the smallest reproducible scope.
- No file writes beyond logs/templates.

### Step B — Inventory & Facts
- Enumerate relevant files, sizes, timestamps.
- Enumerate environment facts (tools present, paths, permissions).
- Record assumptions explicitly (then verify or discard).

### Step C — Hypotheses (≤3)
- Form up to three falsifiable hypotheses.
- Each hypothesis must specify:
  - Cause
  - Observable evidence
  - One change that would falsify it

### Step D — Evidence Collection
- Collect logs, diffs, and command outputs required to falsify hypotheses.
- No changes to production artifacts.

### Step E — Single‑Variable Fix
- Apply **one** minimal fix addressing the confirmed cause.
- Include:
  - Preflight
  - Deterministic self‑test
  - Rollback

### Step F — Verification
- Run the self‑test.
- Record PASS/FAIL with evidence.
- If FAIL, return to Step C (max 2 loops).

---

## 5. Exit Criteria (ALL required)
RCA Mode may exit only when:

1. Root cause is named and evidenced.
2. Minimal fix passes its self‑test.
3. A **preventative control** is defined (gate, invariant, preflight).
4. Evidence is logged.
5. CSRG returns **ALLOW**.

If any condition is unmet, RCA continues.

---

## 6. Preventative Controls (One Required)
At least one must be added before exit:

- New invariant + enforcement location
- New CSRG check
- New toolchain preflight
- New size/implausibility sanity gate
- New assumption registry entry

---

## 7. Evidence Log (v2)
Every RCA cycle must emit an evidence row:

```json
{
  "event_ts_utc": "ISO8601",
  "component": "RCA_MODE",
  "trigger": "R1|R2|R3|R4|R5|R6|R7",
  "hypothesis": "string",
  "evidence": ["string"],
  "fix": "string",
  "verification": "PASS|FAIL",
  "preventative_control": "string",
  "status": "OPEN|VERIFIED"
}
```

---

## 8. Enforcement Hooks
- **CSRG**: If RCA trigger active → decision limited to HALT_RCA or ALLOW_WITH_FIXES.
- **Audit**: Any audit finding can retroactively trigger RCA.
- **Size Plausibility Gate**: Blocks implausible rebuilds.
- **Single‑Instance Guard**: Prevents duplicate daemons/processes.

---

## 9. Immediate Enactment
Effective immediately:
- This SOP governs this chat and all MetaBlooms work.
- Any further failure triggers RCA automatically.
- No forward progress without satisfying exit criteria.

---

## 10. Acceptance Tests
RCA SOP is considered working if it prevents:
- Repeated patch loops
- Toolchain assumption errors
- Tests that cannot pass authored gates
- “Success” without evidence
- User‑burdened debugging
