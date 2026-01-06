# MetaBlooms OS Build Checklist

**CRITICAL:** Follow this checklist IN ORDER when creating a new OS bundle.
**NEVER skip steps.** Each step prevents specific failure modes.

---

## Pre-Build Phase

### ☐ 1. Version Planning
- [ ] Determine version number (e.g., v7.4.2)
- [ ] Document what changed from previous version
- [ ] Identify if this is a breaking change

### ☐ 2. Environment Check
- [ ] Confirm current working directory
- [ ] Verify you have access to all source files
- [ ] Check if previous bundle exists to use as template

---

## Build Phase

### ☐ 3. Create Build Directory
```bash
mkdir -p /mnt/data/metablooms_build
cd /mnt/data/metablooms_build
```

### ☐ 4. Copy BOOT FILES (CRITICAL - NEVER SKIP)

**This step prevents the "missing boot path" failure.**

Copy these files IN THIS ORDER:

```bash
# 1. Boot launcher (stable entrypoint)
cp BOOT_METABLOOMS.py /mnt/data/metablooms_build/

# 2. Runtime entrypoint (primary executable)
cp RUN_METABLOOMS.py /mnt/data/metablooms_build/

# 3. Boot configuration
cp boot_manifest.json /mnt/data/metablooms_build/
cp boot_contract.json /mnt/data/metablooms_build/

# 4. Boot documentation
cp BOOT.md /mnt/data/metablooms_build/
cp ENTRYPOINT.md /mnt/data/metablooms_build/
cp README_BOOT_RULES.md /mnt/data/metablooms_build/
```

**VERIFICATION CHECKPOINT:**
```bash
ls -la /mnt/data/metablooms_build/*.py
# Must show: BOOT_METABLOOMS.py, RUN_METABLOOMS.py

ls -la /mnt/data/metablooms_build/*.json
# Must show: boot_manifest.json, boot_contract.json
```

If ANY file is missing, STOP and copy it before proceeding.

### ☐ 5. Copy Control Plane (CRITICAL)

```bash
mkdir -p /mnt/data/metablooms_build/control_plane
cp -r control_plane/* /mnt/data/metablooms_build/control_plane/
```

**VERIFICATION CHECKPOINT:**
```bash
# These files MUST exist:
ls /mnt/data/metablooms_build/control_plane/BOOT_STATE.json
ls /mnt/data/metablooms_build/control_plane/boot_activator.py
ls /mnt/data/metablooms_build/control_plane/activation_registry.py
ls /mnt/data/metablooms_build/control_plane/bridge_map.json
ls /mnt/data/metablooms_build/control_plane/heuristic_matrix.json
```

### ☐ 6. Copy Learning Infrastructure

```bash
mkdir -p /mnt/data/metablooms_build/learning/{nanoblooms,microblooms,macroblooms,cle,traces}

# Initialize empty registries if they don't exist
echo '[]' > /mnt/data/metablooms_build/learning/nanoblooms/registry.json
echo '[]' > /mnt/data/metablooms_build/learning/microblooms/registry.json
echo '[]' > /mnt/data/metablooms_build/learning/macroblooms/registry.json

# Copy CLE wiring
cp learning/CLE_WIRING.json /mnt/data/metablooms_build/learning/
```

### ☐ 7. Copy Other Subsystems

```bash
# BLE (Bloom Learning Engine)
mkdir -p /mnt/data/metablooms_build/ble
cp -r ble/* /mnt/data/metablooms_build/ble/

# Governance
mkdir -p /mnt/data/metablooms_build/governance
cp -r governance/* /mnt/data/metablooms_build/governance/

# Other directories as needed
# (baselines, docs, egg_juicer, etc.)
```

### ☐ 8. Create Version Manifest

```bash
cat > /mnt/data/metablooms_build/VERSION_MANIFEST.json <<EOF
{
  "version": "v7.4.2",
  "date": "$(date -u +%Y-%m-%d)",
  "parent_version": "v7.4.1",
  "breaking_changes": false,
  "required_subsystems": [
    "CONTROL_PLANE_CORE",
    "BRIDGE_MAP",
    "HEURISTIC_MATRIX",
    "CHM",
    "SHOPPING_MODE_CONTROLLER"
  ],
  "changelog": [
    "Add your changes here"
  ]
}
EOF
```

### ☐ 9. Create MEEP Manifest (Integrity Verification)

```python
# Generate SHA256 hashes for all files
import json
import hashlib
from pathlib import Path
from datetime import datetime

build_dir = Path("/mnt/data/metablooms_build")
inventory = []

for file_path in sorted(build_dir.rglob("*")):
    if file_path.is_file():
        with open(file_path, 'rb') as f:
            sha256 = hashlib.sha256(f.read()).hexdigest()

        inventory.append({
            "path": str(file_path.relative_to(build_dir)),
            "sha256": sha256
        })

manifest = {
    "export_authority": "MetaBlooms",
    "export_standard": "MEEP-1.0",
    "date": datetime.utcnow().isoformat() + "Z",
    "base_source": "MetaBlooms_OS_v7_4_2",
    "counts": {"files": len(inventory)},
    "inventory": inventory
}

with open(build_dir / "MEEP_Manifest.json", 'w') as f:
    json.dump(manifest, f, indent=2)

print(f"✅ MEEP Manifest created with {len(inventory)} files")
```

---

## Validation Phase (NEVER SKIP)

### ☐ 10. Run Bundle Validator

```bash
python scripts/validate_os_bundle.py /mnt/data/metablooms_build
```

**Expected output:**
```
✅ Boot Files: PASS
✅ Control Plane: PASS
✅ Required Directories: PASS
✅ Boot Configuration: PASS

✅ BUNDLE IS VALID AND BOOTABLE
```

**If validation fails:**
- Read the error messages carefully
- Fix the missing/incorrect files
- Re-run validation
- DO NOT proceed to packaging until validation passes

### ☐ 11. Test Boot (Smoke Test)

```python
import subprocess
import sys

result = subprocess.run(
    ["python3", "/mnt/data/metablooms_build/RUN_METABLOOMS.py"],
    capture_output=True,
    text=True,
    timeout=10
)

print(result.stdout)

if "BOOT_OK" in result.stdout:
    print("✅ Boot test PASSED")
else:
    print("❌ Boot test FAILED")
    print(result.stderr)
    sys.exit(1)
```

**If boot test fails:**
- Check control_plane/BOOT_STATE.json exists
- Check all required subsystems are present
- Review error output
- Fix issues and re-test

---

## Packaging Phase

### ☐ 12. Create ZIP Bundle

```python
import zipfile
from pathlib import Path
from datetime import datetime

build_dir = Path("/mnt/data/metablooms_build")
version = "v7_4_2"
timestamp = datetime.now().strftime("%Y-%m-%d")
bundle_name = f"MetaBlooms_OS_CANONICAL_{version}_{timestamp}.zip"
bundle_path = Path(f"/mnt/data/{bundle_name}")

with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for file_path in build_dir.rglob("*"):
        if file_path.is_file():
            arcname = file_path.relative_to(build_dir)
            zf.write(file_path, arcname)
            print(f"  Added: {arcname}")

print(f"\n✅ Bundle created: {bundle_path}")
print(f"   Size: {bundle_path.stat().st_size / 1024 / 1024:.2f} MB")
```

### ☐ 13. Validate ZIP Bundle

```bash
python scripts/validate_os_bundle.py /mnt/data/MetaBlooms_OS_CANONICAL_v7_4_2_2026-01-06.zip
```

Must show: `✅ BUNDLE IS VALID AND BOOTABLE`

### ☐ 14. Generate Download Link

```python
bundle_path = "/mnt/data/MetaBlooms_OS_CANONICAL_v7_4_2_2026-01-06.zip"
print(f"Download link will be available in ChatGPT UI for:")
print(f"  {bundle_path}")
```

---

## Post-Build Verification

### ☐ 15. Create Build Receipt

```json
{
  "build_id": "MetaBlooms_OS_v7_4_2_20260106",
  "timestamp_utc": "2026-01-06T21:30:00Z",
  "version": "v7.4.2",
  "bundle_filename": "MetaBlooms_OS_CANONICAL_v7_4_2_2026-01-06.zip",
  "validation_status": "PASSED",
  "boot_test_status": "PASSED",
  "file_count": 94,
  "bundle_size_mb": 0.25,
  "sha256": "<calculate from bundle>",
  "ready_for_distribution": true,
  "upload_instructions": "Download bundle, watcher will auto-upload to GitHub"
}
```

### ☐ 16. User Instructions

Provide to user:
```
✅ BUILD COMPLETE

Bundle: MetaBlooms_OS_CANONICAL_v7_4_2_2026-01-06.zip
Status: VALIDATED AND BOOTABLE

Instructions:
1. Download the bundle from the link below
2. Termux/PowerShell watcher will detect and upload to GitHub
3. Next session: Boot with this bundle from Project Files

Changes in this version:
- [List changes here]
```

---

## Failure Recovery

### If you realize boot path was forgotten:

**DO NOT create new bundle from scratch.** Instead:

1. Extract the incomplete bundle
2. Add missing boot files
3. Re-run validation
4. Re-package
5. Re-validate

### If boot test fails:

1. Check `BOOT_STATE.json` exists
2. Check `boot_manifest.json` has correct entrypoint
3. Check all required `.py` files are present
4. Check control_plane/ structure
5. Review error output from boot test
6. Fix issues
7. Re-run from step 10 (Validation Phase)

---

## Checklist Summary

Before saying "Build Complete":

- [ ] All boot files present (BOOT_METABLOOMS.py, RUN_METABLOOMS.py, boot_manifest.json)
- [ ] Control plane complete (BOOT_STATE.json, boot_activator.py, etc.)
- [ ] Bundle validation PASSED
- [ ] Boot test PASSED
- [ ] ZIP created
- [ ] ZIP validation PASSED
- [ ] Build receipt generated
- [ ] Download link available

**If ANY checkbox is unchecked, the build is NOT complete.**

