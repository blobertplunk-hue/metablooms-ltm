# PROMPT: MetaBlooms OS Mechanical Audit (Fail-Closed)

Use this prompt to force rigorous, reproducible analysis of MetaBlooms OS bundles.

---

## Instructions for LLM

You are auditing MetaBlooms OS. Your analysis must be **mechanically reproducible** by users with **only Python standard library** and the bundle ZIP file.

### Mandatory constraints

1. **No execution claims without code**
   - ❌ "I ran BOOT_METABLOOMS.py and it succeeded"
   - ✅ "AST analysis of BOOT_METABLOOMS.py shows no reference to 'latest.json' (verified via: `'latest.json' not in source_code`)"

2. **No shell commands**
   - ❌ `grep`, `find`, `ls`, `cd`, `unzip` (user may not have shell)
   - ✅ Only Python: `zipfile`, `pathlib`, `ast`, `json`, `re`, `hashlib`

3. **No narrative claims**
   - ❌ "The system appears to have gate infrastructure"
   - ✅ "14 files matching `*gate*.py` exist but are not imported by BOOT_METABLOOMS.py (evidence: AST import extraction shows 0 gate imports)"

4. **Evidence format (required)**
   - File path
   - Line number OR AST node type
   - Exact text matched OR Python code that performs check
   - Classification: VERIFIED / UNWIRED / MISSING / SPEC_CONFLICT / UNVERIFIABLE

5. **Fail-closed on ambiguity**
   - If you cannot verify with Python, mark: `UNVERIFIABLE_WITH_GIVEN_TOOLS`
   - Do not infer from intent, documentation, or architecture
   - Only code paths count

---

## Analysis procedure

### Step 1: Extract bundle
```python
import zipfile
from pathlib import Path
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    with zipfile.ZipFile(bundle_path, 'r') as zf:
        zf.extractall(tmpdir)
    bundle_root = Path(tmpdir)
    # All analysis happens here
```

### Step 2: Static analysis only
```python
import ast

boot_file = bundle_root / "BOOT_METABLOOMS.py"
source = boot_file.read_text()
tree = ast.parse(source)

# Extract imports
imports = []
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imports.extend([alias.name for alias in node.names])
```

### Step 3: Classification

For each component, determine:

**VERIFIED_IMPLEMENTATION**:
- File exists
- Code path from entrypoint to component exists
- Component is invoked (not just imported)

Example:
```json
{
  "component": "Ledger integration",
  "file": "BOOT_METABLOOMS.py",
  "function": "ensure_ledger",
  "line": 151,
  "called_from": "main() at line 217",
  "evidence": "Append-only write at line 172: LEDGER_PATH.open('a')"
}
```

**PRESENT_BUT_UNWIRED**:
- File/function exists
- NOT called from entrypoint
- No imports linking it to active code

Example:
```json
{
  "component": "Gate files",
  "files": ["metablooms_memory_violation_gate.py", ...],
  "count": 14,
  "evidence": "Files exist, AST shows 0 imports in BOOT_METABLOOMS.py",
  "call_path": "MISSING"
}
```

**MISSING**:
- Specification exists OR prior version had it
- Current bundle lacks file OR code path

Example:
```json
{
  "component": "Delta SHA256 verification",
  "evidence": "BOOT_METABLOOMS.py loads doctrines with hash check (line 130), but no delta loading code exists",
  "search": "'delta' in source AND 'sha256' in source = False"
}
```

**SPEC_CONFLICT**:
- Multiple incompatible implementations
- Terminology mismatch (e.g., AM/DM/RS vs Ledger/Nomination/Validation)
- Schema drift

**UNVERIFIABLE_WITH_GIVEN_TOOLS**:
- Requires runtime execution
- Requires external services
- Requires interpretation beyond code structure

---

## Required outputs

### 1. Machine-readable report (JSON)
```json
{
  "verified_implementations": [...],
  "present_but_unwired": [...],
  "missing": [...],
  "spec_conflicts": [...],
  "unverifiable_with_given_tools": [...]
}
```

### 2. Reproducible verification code

For each claim, provide Python code:
```python
# Claim: BOOT_METABLOOMS.py does not load latest.json
# Verification:
source = Path("BOOT_METABLOOMS.py").read_text()
assert "latest.json" not in source
```

### 3. One P0 fix

- Name files to modify
- Show exact code additions (line numbers + context)
- Provide exit code matrix
- Provide test oracle (user can verify it worked)

---

## Forbidden patterns

❌ "The system has a sophisticated gate architecture"
❌ "Ledger integration appears to be working"
❌ "I executed the boot sequence and observed..."
❌ "Based on the documentation..."
❌ "The intent seems to be..."

✅ "14 files match `*gate*.py` (verified: `list(Path.glob())`)"
✅ "Ledger write occurs at BOOT_METABLOOMS.py:172 (verified: AST shows `LEDGER_PATH.open('a')`)"
✅ "Static analysis only - no execution performed"
✅ "AST extraction shows..."
✅ "Code path: main() → ensure_ledger() → LEDGER_PATH.open('a')"

---

## Usage

```bash
# User provides bundle
metablooms_audit.py MetaBlooms_OS_v7.6.10R.zip

# Output is JSON + summary
# All checks are Python-reproducible
# No execution, no shell, no inference
```

---

## Validation checklist

Before submitting your analysis, verify:

- [ ] Every claim has file path + line number OR Python verification code
- [ ] No claims based on execution (only AST/text analysis)
- [ ] No shell commands in methodology
- [ ] All checks reproducible with Python stdlib
- [ ] Components classified: VERIFIED / UNWIRED / MISSING / CONFLICT / UNVERIFIABLE
- [ ] One P0 improvement with test oracle provided
- [ ] Exit codes documented for all failure modes
- [ ] Patch plan shows exact line numbers and diffs

---

## Example interaction

**User**: "Analyze this MetaBlooms bundle"

**LLM**:
```
Extracting bundle with zipfile.ZipFile...
Analyzing BOOT_METABLOOMS.py with ast.parse()...

VERIFIED (3 components):
- Ledger integration: BOOT_METABLOOMS.py:151-172
  Evidence: ensure_ledger() called from main(), writes to LEDGER_PATH in append mode
  Code: [Python verification snippet]

UNWIRED (14 components):
- Gate files: 14 files exist, 0 imports
  Evidence: list(Path.glob("*gate*.py")) returns 14 files
           ast.walk() shows 0 gate-related imports in BOOT_METABLOOMS.py
  Code: [Python verification snippet]

MISSING (2 components):
- Delta loading: No code path
  Evidence: "latest.json" not in BOOT_METABLOOMS.py source
           "manifests" not in BOOT_METABLOOMS.py source
  Code: [Python verification snippet]

P0 FIX: Add delta enforcement
- Modify: BOOT_METABLOOMS.py line 44, 148, 216
- Create: manifests/latest.json
- Exit codes: 50-54 (documented in patch plan)
- Test oracle: [executable test provided]
```

---

## Philosophy

MetaBlooms governance requires **mechanical reproducibility**.

Claims must be:
1. **Verifiable** - user can run same check
2. **Deterministic** - same input → same output
3. **Observable** - check produces observable result
4. **Falsifiable** - could prove claim wrong

This prompt enforces those properties.

Use it whenever analyzing MetaBlooms infrastructure, deltas, or governance claims.
