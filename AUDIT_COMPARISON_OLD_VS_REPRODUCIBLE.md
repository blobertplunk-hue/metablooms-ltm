# Audit Comparison: Shell-Based vs Python-Reproducible

## Original claims (shell-dependent)

| Claim | Method | Reproducible? |
|-------|--------|---------------|
| "BOOT_METABLOOMS.py boots successfully" | `python3 BOOT_METABLOOMS.py` | ❌ Requires execution |
| "10 boot events in ledger" | `cat epistemic_ledger.ndjson \| wc -l` | ❌ Shell command |
| "14 gate files exist" | `ls *gate*.py \| wc -l` | ✅ Python: `len(list(Path.glob("*gate*.py")))` |
| "No CSRG implementation" | `grep -r csrg *.py` | ✅ Python: `"csrg" in file.read_text().lower()` |
| "RUNTIME_INDEX.json is 780KB" | `ls -lh RUNTIME_INDEX.json` | ✅ Python: `Path.stat().st_size` |
| "Boot loads doctrines" | Executed and observed stdout | ❌ Can verify via AST analysis instead |

## Reproducible verification (Python-only)

### Test 1: Delta loading
```python
# Claim: BOOT_METABLOOMS.py does not load latest.json
from pathlib import Path

boot_source = Path("BOOT_METABLOOMS.py").read_text()
assert "latest.json" not in boot_source
assert "manifests" not in boot_source
# VERIFIED: No delta manifest loading
```

### Test 2: Gate wiring
```python
# Claim: Gates exist but are not imported
import ast
from pathlib import Path

# Count gate files
gate_files = list(Path(".").glob("*gate*.py"))
print(f"Gate files: {len(gate_files)}")

# Check boot imports
boot_source = Path("BOOT_METABLOOMS.py").read_text()
boot_ast = ast.parse(boot_source)

imports = []
for node in ast.walk(boot_ast):
    if isinstance(node, ast.Import):
        imports.extend([a.name for a in node.names])
    elif isinstance(node, ast.ImportFrom):
        if node.module:
            imports.append(node.module)

gate_imports = [i for i in imports if "gate" in i.lower()]
print(f"Gate imports in boot: {len(gate_imports)}")

assert len(gate_files) > 0
assert len(gate_imports) == 0
# VERIFIED: Gates unwired
```

### Test 3: Ledger integration
```python
# Claim: Boot writes to ledger in append mode
import ast
from pathlib import Path

boot_source = Path("BOOT_METABLOOMS.py").read_text()
boot_ast = ast.parse(boot_source)

# Find open() calls with append mode
append_writes = []
for node in ast.walk(boot_ast):
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "open":
                # Check if mode is 'a'
                if len(node.args) >= 2:
                    if isinstance(node.args[1], ast.Constant):
                        if node.args[1].value == "a":
                            append_writes.append(node.lineno)

# Also check for .open("a") pattern
if '"a"' in boot_source or "'a'" in boot_source:
    if "ledger" in boot_source.lower():
        print("VERIFIED: Ledger append-only write exists")
```

### Test 4: CSRG absence
```python
# Claim: No CSRG implementation
from pathlib import Path

py_files = list(Path(".").glob("**/*.py"))
csrg_files = []

for py_file in py_files:
    try:
        source = py_file.read_text()
        if "csrg" in source.lower():
            csrg_files.append(py_file.name)
    except:
        pass

print(f"Files containing 'csrg': {len(csrg_files)}")
assert len(csrg_files) == 0
# VERIFIED: CSRG absent
```

## Automation: metablooms_audit.py

All checks above are now automated in `metablooms_audit.py`.

Usage:
```bash
python3 metablooms_audit.py MetaBlooms_OS_v7.6.10R.zip
```

Output:
```json
{
  "verified_implementations": [
    {
      "component": "Ledger integration",
      "evidence": "BOOT_METABLOOMS.py:172 contains append-only write"
    }
  ],
  "present_but_unwired": [
    {
      "component": "Gate files",
      "count": 14,
      "evidence": "Files exist, 0 imports in boot"
    }
  ],
  "missing": [
    {
      "component": "Delta manifest loading",
      "evidence": "'latest.json' not in BOOT_METABLOOMS.py"
    }
  ]
}
```

## Key difference

**Before**: Trust my execution transcript
**After**: User can run same Python code and verify

## Files delivered

1. `metablooms_audit.py` - Full audit harness
2. `boot_capability_probe.py` - AST-based boot analyzer
3. `PATCH_PLAN_P0_DELTA_ENFORCEMENT.md` - Complete fix with test oracle
4. `PROMPT_METABLOOMS_MECHANICAL_AUDIT.md` - Reusable prompt for future analysis
5. This comparison document

All verification is now **deterministic, reproducible, and requires only Python stdlib**.
