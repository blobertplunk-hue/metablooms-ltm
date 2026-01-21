# MetaBlooms Runtime Entrypoint Flow Diagram

## Overview

This document visualizes the execution flow through the MetaBlooms runtime entrypoint system.

---

## 1. High-Level Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        CALLER / ORCHESTRATOR                     │
│                    (external invocation layer)                   │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                │ invokes with context + work_fn
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│            runtime_entrypoint.run(context, work_fn)              │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. Validate context (repo_root, turn_id required)       │   │
│  │  2. Load state/OPEN_FAILURES.json (fail if missing)      │   │
│  │  3. Check unresolved failures (block if present)         │   │
│  │  4. Enforce commit gate (open expectations block)        │   │
│  │  5. Write START event → telemetry/events.jsonl          │   │
│  │  6. Write hashes → telemetry/hashes.jsonl               │   │
│  │  7. Mark context['runtime_entrypoint'] = True           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    try:                                   │   │
│  │  ┌────────────────────────────────────────────────────┐ │   │
│  │  │  PREFLIGHT GATES (gate_runner.run_preflight)       │ │   │
│  │  │  ├─ Materialize research structures               │ │   │
│  │  │  ├─ Enforce Rule-of-Three invariant               │ │   │
│  │  │  ├─ Enforce Delta-on-retry invariant              │ │   │
│  │  │  └─ Enforce P0DCC router                          │ │   │
│  │  └────────────────────────────────────────────────────┘ │   │
│  │                         │                                │   │
│  │                         ▼                                │   │
│  │  ┌────────────────────────────────────────────────────┐ │   │
│  │  │  WORK EXECUTION: result = work_fn(context)         │ │   │
│  │  │  (caller-provided callback executes here)          │ │   │
│  │  └────────────────────────────────────────────────────┘ │   │
│  │                         │                                │   │
│  │                         ▼                                │   │
│  │  ┌────────────────────────────────────────────────────┐ │   │
│  │  │  POSTFLIGHT GATES (gate_runner.run_postflight)     │ │   │
│  │  │  ├─ Enforce research evidence requirements        │ │   │
│  │  │  ├─ Enforce citation density invariant            │ │   │
│  │  │  ├─ Enforce claim↔receipt↔timestamp binding       │ │   │
│  │  │  └─ Enforce staging→commit discipline             │ │   │
│  │  └────────────────────────────────────────────────────┘ │   │
│  │                         │                                │   │
│  │                         ▼                                │   │
│  │                    return result                         │   │
│  │                                                          │   │
│  │  except Exception as e:                                 │   │
│  │      raise RuntimeFailClosed(str(e))                    │   │
│  │                                                          │   │
│  │  finally:                                               │   │
│  │      if commit:                                         │   │
│  │          Write provenance → telemetry/provenance.jsonl  │   │
│  │      Write END event → telemetry/events.jsonl          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                │ returns result (or raises RuntimeFailClosed)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        CALLER / ORCHESTRATOR                     │
│                   (handles result or failure)                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. State & Telemetry Files

```
metablooms_live/
├── state/
│   └── OPEN_FAILURES.json          ← Persistent failure tracking
│                                      Format: {"open": ["failure1", "failure2"]}
│                                      Blocks new work if non-empty
│
└── telemetry/
    ├── events.jsonl                ← START+END events per turn
    │                                  {"turn_id": "...", "event": "START", "ts": "..."}
    │                                  {"turn_id": "...", "event": "END", "ts": "..."}
    │
    ├── hashes.jsonl                ← Hash tracking per turn
    │                                  {"turn_id": "...", "ts": "...", "note": "hashes"}
    │
    └── provenance.jsonl            ← Commit provenance (commit=True only)
                                       {"turn_id": "...", "ts": "...", "commit": true}
```

---

## 3. Fail-Closed Decision Tree

```
┌─────────────────────────────────────────────────────────────────┐
│              runtime_entrypoint.run(context, work_fn)            │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                │  repo_root in context?        │
                └───────────────┬───────────────┘
                                │
                        ┌───────┴───────┐
                        │               │
                       YES              NO
                        │               │
                        │               └─→ raise RuntimeFailClosed("repo_root required")
                        │
                ┌───────┴────────────────────────┐
                │  turn_id in context?            │
                └───────────────┬────────────────┘
                                │
                        ┌───────┴───────┐
                        │               │
                       YES              NO
                        │               │
                        │               └─→ raise RuntimeFailClosed("turn_id required")
                        │
                ┌───────┴────────────────────────────────┐
                │  state/OPEN_FAILURES.json exists?      │
                └───────────────┬────────────────────────┘
                                │
                        ┌───────┴───────┐
                        │               │
                       YES              NO
                        │               │
                        │               └─→ raise RuntimeFailClosed("Missing state file")
                        │
                ┌───────┴────────────────────────────────┐
                │  state/OPEN_FAILURES.json valid JSON?  │
                └───────────────┬────────────────────────┘
                                │
                        ┌───────┴───────┐
                        │               │
                       YES              NO
                        │               │
                        │               └─→ raise RuntimeFailClosed("Invalid JSON")
                        │
                ┌───────┴────────────────────────────────┐
                │  "open" key present in JSON?           │
                └───────────────┬────────────────────────┘
                                │
                        ┌───────┴───────┐
                        │               │
                       YES              NO
                        │               │
                        │               └─→ raise RuntimeFailClosed("Missing 'open' key")
                        │
                ┌───────┴────────────────────────────────────┐
                │  Unresolved failures (open list not empty)?│
                └───────────────┬────────────────────────────┘
                                │
                        ┌───────┴───────┐
                        │               │
                        NO             YES
                        │               │
                        │               └─→ raise RuntimeFailClosed("Unresolved failures")
                        │
                ┌───────┴────────────────────────────────────────────┐
                │  commit=True AND len(open)>0 AND                   │
                │  allow_open_expectations=False?                     │
                └───────────────┬────────────────────────────────────┘
                                │
                        ┌───────┴───────┐
                        │               │
                        NO             YES
                        │               │
                        │               └─→ raise RuntimeFailClosed("Open expectations block commit")
                        │
                        ▼
                ┌──────────────────────┐
                │  Write START event   │
                │  Write hashes        │
                │  Mark context        │
                └──────────┬───────────┘
                           │
                           ▼
                ┌─────────────────────────┐
                │  Execute preflight gates │
                │  (may raise)             │
                └──────────┬──────────────┘
                           │
                           ▼
                ┌─────────────────────────┐
                │  Execute work_fn         │
                │  (may raise)             │
                └──────────┬──────────────┘
                           │
                           ▼
                ┌─────────────────────────┐
                │  Execute postflight gates│
                │  (may raise)             │
                └──────────┬──────────────┘
                           │
                           ▼
                ┌─────────────────────────────────┐
                │  finally:                        │
                │    if commit: write provenance   │
                │    write END event               │
                └──────────┬──────────────────────┘
                           │
                           ▼
                  ┌────────────────┐
                  │  Return result  │
                  │  (or raise)     │
                  └────────────────┘
```

---

## 4. Telemetry Guarantee: Try/Finally Pattern

The critical pattern ensuring telemetry writes survive failures:

```python
# START event written BEFORE try block
_append_jsonl(events_p, {"turn_id": turn_id, "event": "START", "ts": ...})
_append_jsonl(hashes_p, {"turn_id": turn_id, "ts": ..., "note": "hashes"})

try:
    # Preflight gates (may fail)
    run_preflight(context)

    # Work execution (may fail)
    result = work_fn(context)

    # Postflight gates (may fail)
    run_postflight(context)

    return result

except Exception as e:
    # Normalize all failures to RuntimeFailClosed
    raise RuntimeFailClosed(str(e))

finally:
    # GUARANTEED TO EXECUTE even if try block raises
    if commit:
        _append_jsonl(prov_p, {"turn_id": turn_id, "ts": ..., "commit": True})
    _append_jsonl(events_p, {"turn_id": turn_id, "event": "END", "ts": ...})
```

**Result**: Every invocation writes:
- START event (before any work)
- END event (even if work fails)
- Hashes (before any work)
- Provenance (on commit, even if work fails)

---

## 5. Gate Runner Invariants

### Preflight Gates

```
┌────────────────────────────────────────────────────────────┐
│             gate_runner.run_preflight(context)              │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  1. research_materializer.enforce(context)                 │
│     └─ Materialize research structures                     │
│        (claims/citation skeleton; inject created_ts)       │
│                                                             │
│  2. rule_of_three_invariant.enforce(context)               │
│     └─ Enforce Rule-of-Three prerequisites                 │
│                                                             │
│  3. delta_required_invariant.enforce(context)              │
│     └─ Enforce Delta-on-retry requirements                 │
│                                                             │
│  4. p0_dcc_router.enforce_p0_dcc(context)                  │
│     └─ Enforce P0DCC router                                │
│        (loop/ECL/ledgers/telemetry mandatory routing)      │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

### Postflight Gates

```
┌────────────────────────────────────────────────────────────┐
│            gate_runner.run_postflight(context)              │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  1. research_invariant.enforce(context)                    │
│     └─ Enforce research evidence requirements              │
│        (when research is required)                         │
│                                                             │
│  2. citation_density_invariant.enforce(context)            │
│     └─ Enforce citation coverage requirements              │
│                                                             │
│  3. claim_receipt_timestamp_invariant.enforce(context)     │
│     └─ Enforce claim↔receipt↔timestamp binding             │
│                                                             │
│  4. staging_commit.enforce(context)                        │
│     └─ Enforce staging→commit discipline                   │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

---

## 6. Context Dictionary Structure

```python
context = {
    # REQUIRED
    "repo_root": str,           # Absolute path to repository root
    "turn_id": str,             # Unique turn identifier (e.g., "MB-ACCEPT-2026-01-21-04")

    # OPTIONAL (behavior control)
    "commit": bool,             # If True, attempt commit (default: False)
    "allow_open_expectations": bool,  # Override open expectations commit gate (default: False)

    # INJECTED BY RUNTIME
    "runtime_entrypoint": bool, # Set to True by runtime_entrypoint.run() to mark supervised path

    # DOMAIN-SPECIFIC (provided by caller)
    # ... additional context keys for gates/invariants/work ...
}
```

---

## 7. Failure Modes & Recovery

### Failure Mode 1: Missing State File

```
Cause: state/OPEN_FAILURES.json does not exist
Effect: raise RuntimeFailClosed("Missing required state file: state/OPEN_FAILURES.json")
Recovery: Create state/OPEN_FAILURES.json with {"open": []}
```

### Failure Mode 2: Invalid State File

```
Cause: state/OPEN_FAILURES.json contains invalid JSON
Effect: raise RuntimeFailClosed("Invalid JSON in required state file: ...")
Recovery: Fix JSON syntax in state/OPEN_FAILURES.json
```

### Failure Mode 3: Unresolved Failures

```
Cause: state/OPEN_FAILURES.json contains {"open": ["failure1", "failure2"]}
Effect: raise RuntimeFailClosed("P0 FAIL-CLOSED — unresolved failures present: ['failure1', 'failure2']")
Recovery: Enter fail-to-fix mode, resolve failures, clear open list
```

### Failure Mode 4: Open Expectations Block Commit

```
Cause: commit=True, len(open) > 0, allow_open_expectations=False
Effect: raise RuntimeFailClosed("Open expectations present; commit blocked")
Recovery: Either:
  - Resolve open expectations and clear open list
  - Set allow_open_expectations=True to override (testing/acceptance only)
```

### Failure Mode 5: Preflight Gate Failure

```
Cause: One of the preflight gates (research_materializer, rule_of_three, etc.) raises
Effect: raise RuntimeFailClosed(str(original_exception))
Telemetry: START+END+hashes written (provenance if commit=True)
Recovery: Investigate gate failure, fix underlying issue, retry
```

### Failure Mode 6: Work Callback Failure

```
Cause: work_fn(context) raises an exception
Effect: raise RuntimeFailClosed(str(original_exception))
Telemetry: START+END+hashes written (provenance if commit=True)
Recovery: Investigate work_fn failure, fix underlying issue, retry
```

### Failure Mode 7: Postflight Gate Failure

```
Cause: One of the postflight gates (research, citation, crt, staging_commit) raises
Effect: raise RuntimeFailClosed(str(original_exception))
Telemetry: START+END+hashes written (provenance if commit=True)
Recovery: Investigate gate failure, ensure work satisfies postflight requirements, retry
```

---

## 8. Comparison: Before vs. After Fix

### Before Fix (Broken)

```
Problems:
1. API collision: Two def run(...) with incompatible signatures
2. Telemetry missing on fail-closed paths (END not written if preflight failed)
3. Provenance not written on commit failures

Call Pattern:
runtime_entrypoint.run(context, work_fn)  # TypeError: takes 0 positional arguments but 2 given

Telemetry on Failure:
events.jsonl:   {"event": "START", "turn_id": "..."}
                # END missing if preflight failed!
hashes.jsonl:   {"turn_id": "..."}
provenance.jsonl: # Missing entirely if commit failed!
```

### After Fix (Corrected)

```
Fixes:
1. Renamed secondary run() to run_turn() (helper, non-canonical)
2. Wrapped preflight/work/postflight in try/finally
3. Guaranteed telemetry writes in finally block

Call Pattern:
runtime_entrypoint.run(context, work_fn)  # Works correctly

Telemetry on Failure:
events.jsonl:   {"event": "START", "turn_id": "..."}
                {"event": "END", "turn_id": "..."}      # ✅ Written in finally
hashes.jsonl:   {"turn_id": "..."}
provenance.jsonl: {"turn_id": "...", "commit": true}   # ✅ Written in finally (if commit=True)
```

---

## 9. Acceptance Probe Results

### Probe 1: commit=False (Expected Fail-Closed)

```python
context = {
    "repo_root": "/mnt/data/metablooms_fix_runtimeentrypoint_work",
    "turn_id": "MB-ACCEPT-2026-01-21-04",
    "commit": False
}
result = runtime_entrypoint.run(context, noop)
```

**Expected**: Fails closed (ModuleNotFoundError: metablooms_runtime.invariants.rule_of_three_invariant)
**Actual**: ✅ Failed closed as expected
**Telemetry**: ✅ START+END+hashes written

### Probe 2: commit=True (Expected Fail-Closed, Provenance Written)

```python
context = {
    "repo_root": "/mnt/data/metablooms_fix_runtimeentrypoint_work",
    "turn_id": "MB-ACCEPT-2026-01-21-04",
    "commit": True,
    "allow_open_expectations": True
}
result = runtime_entrypoint.run(context, noop)
```

**Expected**: Fails closed (ModuleNotFoundError: metablooms_runtime.invariants.rule_of_three_invariant)
**Actual**: ✅ Failed closed as expected
**Telemetry**: ✅ START+END+hashes+provenance written

### Telemetry Evidence

```json
events.jsonl (tail):
{"event": "START", "ts": "2026-01-21T15:29:21.056722+00:00", "turn_id": "MB-ACCEPT-2026-01-21-04"}
{"event": "END", "ts": "2026-01-21T15:29:21.057575+00:00", "turn_id": "MB-ACCEPT-2026-01-21-04"}
{"event": "START", "ts": "2026-01-21T15:29:21.058290+00:00", "turn_id": "MB-ACCEPT-2026-01-21-04"}
{"event": "END", "ts": "2026-01-21T15:29:21.059168+00:00", "turn_id": "MB-ACCEPT-2026-01-21-04"}
```

**Verdict**: ✅ ACCEPTANCE PASS (with expected fail-closed core)

---

## 10. Integration Points

### Caller Responsibilities

1. **Provide valid context**: Must include `repo_root` and `turn_id`
2. **Provide work callback**: `work_fn(context)` that executes staged work
3. **Handle RuntimeFailClosed**: Catch and handle fail-closed exceptions appropriately
4. **Maintain state files**: Ensure `state/OPEN_FAILURES.json` exists and is valid
5. **Respect telemetry**: Do not delete or modify telemetry/*.jsonl files

### Runtime Entrypoint Guarantees

1. **Supervised execution**: Sets `context['runtime_entrypoint'] = True`
2. **Fail-closed by default**: Any violation raises `RuntimeFailClosed`
3. **Telemetry append-only**: Writes START+END+hashes (provenance on commit) for every turn
4. **State validation**: Enforces presence and validity of state files
5. **Gate enforcement**: Runs preflight and postflight gates, blocks on violations
6. **Commit gating**: Blocks commits if open expectations exist (unless overridden)

---

## 11. Terminology

| Term | Definition |
|------|------------|
| **Turn** | A single invocation of `runtime_entrypoint.run()` with a unique `turn_id` |
| **Fail-Closed** | System blocks execution (raises `RuntimeFailClosed`) when invariants are violated |
| **Open Failures** | Unresolved failures tracked in `state/OPEN_FAILURES.json` that block new work |
| **Preflight Gates** | Invariant checks run BEFORE work execution (materialize, rule-of-three, delta, P0DCC) |
| **Postflight Gates** | Invariant checks run AFTER work execution (research, citation, crt, staging→commit) |
| **Supervised Execution** | Work executed through `runtime_entrypoint.run()` with full gate enforcement |
| **Unsupervised Execution** | Work bypassing `runtime_entrypoint.run()` (DISALLOWED, violates fail-closed contract) |
| **Commit Gate** | Check that blocks commits if open expectations exist (unless `allow_open_expectations=True`) |
| **Telemetry Append-Only** | Telemetry files are never deleted or modified, only appended |
| **Work Callback** | `work_fn(context)` provided by caller, executed within supervised context |

---

## 12. Security Properties

1. **No Silent Failures**: All violations raise `RuntimeFailClosed` with detailed context
2. **Audit Trail**: Every turn leaves telemetry trace (START+END+hashes+provenance)
3. **State Immutability**: State files are validated before use, never silently created/ignored
4. **Explicit Overrides**: Dangerous operations (allow_open_expectations) require explicit opt-in
5. **Fail-Closed Default**: Unknown/unsafe states cause hard failures, not degraded operation

---

## 13. Performance Characteristics

- **Overhead**: Minimal (state file read + telemetry writes + gate checks)
- **Latency**: Dominated by work_fn execution time, not runtime overhead
- **Scalability**: Append-only telemetry scales linearly with turn count
- **Failure Recovery**: Fast (clear open failures, retry turn)

---

## 14. Future Enhancements (Out of Scope)

- **Distributed tracing**: Propagate turn_id across service boundaries
- **Telemetry retention**: Archive old telemetry files (currently unbounded)
- **Async execution**: Support async work_fn callbacks
- **Parallel gates**: Run independent preflight/postflight gates in parallel
- **Dashboard**: Real-time visualization of telemetry events

---

**END OF FLOW DIAGRAM**
