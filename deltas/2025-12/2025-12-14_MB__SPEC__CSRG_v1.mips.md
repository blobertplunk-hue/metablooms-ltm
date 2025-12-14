MIPS_HEADER:
  artifact_id: MB__SPEC__CSRG__2025-12-14_v1
  parent_bundle: MB__GOV__RCA_SOP_ENACTMENT__2025-12-14_v1
  version: v1
  councils: ["Architect", "Auditor", "Recorder"]
  timestamp_utc: 2025-12-14T20:35:51Z
  content_type: text/markdown
  sha256: 00785ee3f23d06af39db4a1ab565cb5239fc6d67f4722c6ce6d727236a4ded93
  evidence_chain: []
  links: []
BODY:

# Common-Sense Reasoning Gate (CSRG) — Permanent Spec + Enactment

## Objective
Insert a deterministic reasoning layer between **User Intent (natural language)** and **Actions (tools, patches, file writes, instructions)** that prevents:
- “do something that has never made sense in context”
- ad‑hoc escalation
- toolchain assumption leakage
- pushing debugging onto the user
- self-contradictory tests vs authored rules

This gate is **mandatory** and runs **before any action plan is executed**.

---

## Definitions
- **Intent**: The user’s outcome goal in plain language.
- **Action**: Any concrete step (command, patch, file creation, tool call, workflow change).
- **Invariant**: A must‑hold property (e.g., “tests must satisfy the same gates they validate”).
- **Context**: Session state, OS rules, toolchain facts, and recent failures.

---

## CSRG Placement (Integration Points)
CSRG must execute at these decision points:

1. **Before generating runnable instructions**
   - PowerShell, Termux, SQL, Python, Apps Script, etc.

2. **Before writing/patching any artifact**
   - Files to /mnt/data
   - “Consolidated OS” rebuilds
   - Delta generation, promotion, or reconciliation

3. **Before recommending tool installation**
   - Any suggestion that requires `apt install`, `pip`, `npm`, etc.

4. **After any RCA Trigger**
   - CSRG inherits RCA Mode constraints (halt → diagnose → minimal safe action)

---

## Inputs / Outputs (Schema)

### Input object: `csrg_input`
```json
{
  "intent_text": "string",
  "proposed_actions": [
    {
      "id": "A1",
      "type": "command|patch|file_write|tool_call|instruction|research",
      "surface": "termux|powershell|chat|web.run|python|project_files",
      "summary": "string",
      "risk": "low|med|high",
      "dependencies": ["string"]
    }
  ],
  "context": {
    "session_failures": ["string"],
    "recent_rca": {"active": true, "triggers": ["RCA-T1"]},
    "toolchain_facts": {
      "termux": {"has_perl": false, "has_tmp": false}
    },
    "os_rules": ["string"]
  }
}
```

### Output object: `csrg_decision`
```json
{
  "decision": "ALLOW|ALLOW_WITH_FIXES|HALT_RCA",
  "blocked_reasons": ["string"],
  "required_fixes": [
    {
      "action_id": "A1",
      "fix": "string",
      "verification": "string"
    }
  ],
  "safe_next_actions": ["A3","A4"],
  "evidence_required": [
    {"type":"log_tail","path":"~/log/mb_watch.log","lines":200}
  ]
}
```

---

## CSRG Checks (The Actual Gate Logic)

### Check Set 1 — “Would this ever make sense?”
An action is blocked if any of the following are true:
- It increases user burden without necessity (manual shuffling, repeated debugging).
- It depends on an unverified assumption (tool exists, path exists, permission exists).
- It does not reduce ambiguity (no PASS/FAIL, no evidence output).
- It repeats a failed move without changing a causal variable.

### Check Set 2 — Toolchain Awareness
Block if:
- Action uses tools not verified in `toolchain_facts` (e.g., perl, /tmp).
- Patch depends on non-core utilities when POSIX alternatives exist.
- Background auth prompts are possible (git credential prompts).

Required fix pattern:
- Introduce preflight detection + fallback plan, or
- Use only minimal primitives guaranteed present.

### Check Set 3 — Self-Consistency
Block if:
- A test payload is not accepted by the gates it is meant to validate (e.g., `is_delta` mismatch).
- The action contradicts an OS rule already active.
- The plan implies “replace whole OS” with implausibly small artifacts (sanity check).

Required fix pattern:
- Re-ingest authored artifact and assert alignment before execution.

### Check Set 4 — Single-Instance / Idempotency
Block if:
- The action can create duplicate daemons / processes without a lock.
- The action is not idempotent or has no rollback.

Required fix pattern:
- Add lockfile + single-instance guard + rollback step.

### Check Set 5 — RCA Coupling
If any RCA trigger is active:
- Decision may only be `HALT_RCA` or `ALLOW_WITH_FIXES`.
- Must provide evidence requirements and minimal-change correction.

---

## Enforcement Rules
- CSRG decisions **override** task urgency and user impatience.
- Invariants outrank tasks.
- If CSRG returns `HALT_RCA`, **no action plan is executed**.

---

## Required Artifacts (What CSRG forces every time)
For any code/patch output:
1. **Preflight block** (toolchain + paths + permissions)
2. **Debug harness** (a minimal reproduction + PASS/FAIL)
3. **Evidence log template** (UTC/context/error/cause/fix/verified/status)
4. **Rollback instructions** (single command or copy restore)

---

## Immediate Enactment (Effective Now)
Starting now, for this chat and all MetaBlooms work:
- Before I give you commands/scripts, I will emit a **CSRG decision** object.
- If a step relies on an assumption, it will be halted and replaced with a verified alternative.
- If a patch is needed, it will be the **minimum** change plus a deterministic self-test.

---

## Test Suite (Acceptance Criteria)
CSRG is “working” if it prevents:
- Perl-based Termux patching when perl is absent.
- `/tmp` assumptions on Termux.
- Tests that cannot pass the recognizer they are designed to validate.
- Duplicate watchers (single-instance lock required).
- “Seems fine” success without evidence.

---

## Evidence Log Row (v2)
```json
{
  "event_ts_utc": "ISO8601",
  "component": "CSRG",
  "decision": "ALLOW|ALLOW_WITH_FIXES|HALT_RCA",
  "blocked_reasons": [],
  "required_fixes": [],
  "caller": "MetaBlooms",
  "request_id": "string",
  "status": "OK|FAIL"
}
```
