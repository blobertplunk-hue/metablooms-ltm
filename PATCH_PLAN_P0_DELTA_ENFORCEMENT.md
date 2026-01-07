# Patch Plan: P0 Delta Enforcement

## Goal
Wire fail-closed delta loading with SHA256 verification into BOOT_METABLOOMS.py.

## Files Modified

### 1. `BOOT_METABLOOMS.py`

**Line 44** - Add constant:
```python
DELTA_MANIFEST = BASE_DIR / "manifests" / "latest.json"
```

**After line 148** - Add function:
```python
def load_and_validate_deltas() -> Dict[str, Any]:
    """
    Loads deltas from manifests/latest.json with SHA256 verification.
    Fail-closed: missing manifest or hash mismatch => stop.
    """
    if not DELTA_MANIFEST.exists():
        _die(50, f"Missing delta manifest: {DELTA_MANIFEST}")

    manifest = _read_json(DELTA_MANIFEST)

    active_deltas = manifest.get("active_deltas")
    if not isinstance(active_deltas, list):
        _die(51, "Manifest missing 'active_deltas' list")

    loaded: Dict[str, Dict[str, Any]] = {}

    for entry in active_deltas:
        delta_id = entry.get("id")
        rel_path = entry.get("path")
        expected_hash = entry.get("sha256")

        if not all([delta_id, rel_path, expected_hash]):
            _die(52, f"Delta entry incomplete (needs id, path, sha256): {entry}")

        delta_path = BASE_DIR / rel_path
        if not delta_path.exists():
            _die(53, f"Missing required delta {delta_id}: {delta_path}")

        actual_hash = _sha256_file(delta_path)
        if actual_hash != expected_hash:
            _die(54, f"Delta hash mismatch for {delta_id}: expected {expected_hash}, got {actual_hash}")

        loaded[delta_id] = {
            "id": delta_id,
            "path": str(delta_path),
            "sha256": actual_hash,
        }

    return {"manifest": manifest, "loaded": loaded}
```

**Line 216** - Modify `main()`:
```python
def main() -> int:
    try:
        env = env_sanity()
        doctrines = load_and_validate_doctrines()
        deltas = load_and_validate_deltas()  # ADD THIS LINE
        ensure_ledger(env, doctrines)
        smoke_tests()

        print("[BOOT_OK] Governance loaded; handing off to runtime.")
        handoff(env, doctrines)
        return 0
```

**Line 194** - Modify `handoff()` signature:
```python
def handoff(env: Dict[str, Any], doctrines: Dict[str, Any], deltas: Dict[str, Any]) -> None:
```

**Line 200** - Add deltas to context:
```python
context = {
    "env": env,
    "doctrines": doctrines["loaded"],
    "deltas": deltas["loaded"],  # ADD THIS LINE
    "rru": RRU_REFERENCE,
}
```

### 2. `manifests/latest.json` (CREATE)

```json
{
  "schema_version": "1.0",
  "active_deltas": [],
  "notes": "Empty list enforces fail-closed without breaking existing boot. Add deltas incrementally."
}
```

### 3. `tests/test_delta_hash_enforcement.py` (CREATE)

See test oracle below.

---

## Failure Matrix

| Exit Code | Meaning | Trigger |
|-----------|---------|---------|
| 50 | Missing delta manifest | `manifests/latest.json` not found |
| 51 | Malformed manifest | Missing `active_deltas` key or not a list |
| 52 | Incomplete delta entry | Entry missing `id`, `path`, or `sha256` |
| 53 | Missing delta file | Delta file referenced in manifest doesn't exist |
| 54 | Hash mismatch | Actual SHA256 ≠ expected SHA256 |

---

## Test Oracle

User can verify success with:

### Test 1: Boot succeeds with empty manifest
```bash
# Extract bundle
unzip MetaBlooms_OS_*.zip -d test_bundle
cd test_bundle

# Create empty manifest
mkdir -p manifests
echo '{"schema_version":"1.0","active_deltas":[]}' > manifests/latest.json

# Boot should succeed
python3 BOOT_METABLOOMS.py
echo "Exit code: $?"
# Expected: 0
```

### Test 2: Boot fails on missing manifest
```bash
# Remove manifest
rm -rf manifests/

# Boot should fail
python3 BOOT_METABLOOMS.py 2>&1
echo "Exit code: $?"
# Expected: 50
# Stderr should contain: "Missing delta manifest"
```

### Test 3: Boot fails on hash mismatch
```bash
# Create manifest with bogus hash
mkdir -p manifests
cat > manifests/latest.json <<'EOF'
{
  "schema_version": "1.0",
  "active_deltas": [
    {
      "id": "TEST-001",
      "path": "governance/doctrines/D-001_boot_as_axiom.md",
      "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
    }
  ]
}
EOF

# Boot should fail
python3 BOOT_METABLOOMS.py 2>&1
echo "Exit code: $?"
# Expected: 54
# Stderr should contain: "Delta hash mismatch"
```

### Test 4: Boot succeeds with valid delta
```bash
# Get real hash
sha256sum governance/doctrines/D-001_boot_as_axiom.md
# Copy hash output

# Create manifest with correct hash
cat > manifests/latest.json <<'EOF'
{
  "schema_version": "1.0",
  "active_deltas": [
    {
      "id": "D-001",
      "path": "governance/doctrines/D-001_boot_as_axiom.md",
      "sha256": "83b90d3d9fb4f92894f2ac7ff4850d41fca87c0b0cff5a8d7cd31c54f7d0da81"
    }
  ]
}
EOF

# Boot should succeed
python3 BOOT_METABLOOMS.py
echo "Exit code: $?"
# Expected: 0
```

---

## Automated Test

```python
#!/usr/bin/env python3
"""Test: Delta hash enforcement"""
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def test_enforcement(bundle_path):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Extract
        with zipfile.ZipFile(bundle_path, 'r') as zf:
            zf.extractall(tmppath)

        tests = []

        # Test 1: Empty manifest (should pass)
        manifest_path = tmppath / "manifests" / "latest.json"
        manifest_path.parent.mkdir(exist_ok=True)
        manifest_path.write_text('{"schema_version":"1.0","active_deltas":[]}')

        result = subprocess.run(
            [sys.executable, str(tmppath / "BOOT_METABLOOMS.py")],
            capture_output=True, timeout=5
        )
        tests.append(("Empty manifest", result.returncode == 0))

        # Test 2: Hash mismatch (should fail with 54)
        manifest_path.write_text(json.dumps({
            "schema_version": "1.0",
            "active_deltas": [{
                "id": "TEST",
                "path": "governance/doctrines/D-001_boot_as_axiom.md",
                "sha256": "0" * 64
            }]
        }))

        result = subprocess.run(
            [sys.executable, str(tmppath / "BOOT_METABLOOMS.py")],
            capture_output=True, timeout=5
        )
        tests.append(("Hash mismatch exits 54", result.returncode == 54))

        # Test 3: Valid hash (should pass)
        doctrine = tmppath / "governance/doctrines/D-001_boot_as_axiom.md"
        real_hash = sha256_file(doctrine)

        manifest_path.write_text(json.dumps({
            "schema_version": "1.0",
            "active_deltas": [{
                "id": "D-001",
                "path": "governance/doctrines/D-001_boot_as_axiom.md",
                "sha256": real_hash
            }]
        }))

        result = subprocess.run(
            [sys.executable, str(tmppath / "BOOT_METABLOOMS.py")],
            capture_output=True, timeout=5
        )
        tests.append(("Valid hash passes", result.returncode == 0))

        # Results
        for name, passed in tests:
            status = "✅" if passed else "❌"
            print(f"{status} {name}")

        return all(passed for _, passed in tests)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: test_delta_hash_enforcement.py <bundle.zip>")
        sys.exit(1)

    success = test_enforcement(Path(sys.argv[1]))
    sys.exit(0 if success else 1)
```

---

## Migration Path

1. **Phase 1**: Add code, create empty manifest
   - No deltas enforced yet
   - Boot still succeeds
   - Enforcement infrastructure active

2. **Phase 2**: Populate manifest with existing doctrines
   - Compute SHA256 of existing doctrine files
   - Add to `active_deltas`
   - Verify boot still succeeds

3. **Phase 3**: Add governance deltas
   - Incrementally add deltas from `deltas/` directory
   - Each addition is SHA256-verified
   - Any corruption caught immediately

---

## Guarantees

- **Fail-closed**: Missing or corrupted deltas halt boot
- **No silent fallbacks**: Every error is explicit exit code
- **Deterministic**: Same manifest + same files = same hash = same boot result
- **Append-only safe**: Doesn't modify existing files, only adds checks
- **Observable**: Exit codes distinguish all failure modes
