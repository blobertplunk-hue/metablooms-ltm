# MetaBlooms Build Tools

## Problem This Solves

**The system keeps leaving the boot path out of the OS.**

When creating new OS bundles in ChatGPT, critical boot files were being forgotten, causing:
- ❌ `BOOT_FAILED: NO_ENTRYPOINT`
- ❌ Next session can't start
- ❌ Learning loop broken
- ❌ Manual recovery required

This tooling **makes it impossible to forget the boot path**.

---

## Quick Start

### For ChatGPT: Automated Build

```python
# Build from existing template (recommended)
!python scripts/build_os_bundle.py \
  --version v7.4.3 \
  --template 2025-12-30_MetaBlooms_OS_CANONICAL_v7_4_1.zip \
  --changelog "Fixed Termux compatibility" \
  --changelog "Added new governance rules"
```

**This will:**
1. ✅ Extract template
2. ✅ Apply your modifications
3. ✅ Validate all boot files present
4. ✅ Test boot sequence
5. ✅ Create ZIP bundle
6. ✅ Validate ZIP
7. ✅ Generate build receipt with SHA256

**If it succeeds:** Download and distribute safely
**If it fails:** Errors show exactly what's missing

---

### For Manual Builds: Validation

If you built manually, validate before distribution:

```bash
# Validate before creating ZIP
python scripts/validate_os_bundle.py /mnt/data/metablooms_build

# Validate ZIP before distribution
python scripts/validate_os_bundle.py /mnt/data/MetaBlooms_OS_v7_4_3.zip
```

**Expected output:**
```
✅ Boot Files: PASS
✅ Control Plane: PASS
✅ Required Directories: PASS
✅ Boot Configuration: PASS

✅ BUNDLE IS VALID AND BOOTABLE
This bundle can be safely distributed.
```

**If validation fails:**
- Read error messages
- Fix missing files
- Re-validate
- **DO NOT distribute** until validation passes

---

## The Tools

### 1. `build_manifest.json`
**Purpose:** Authoritative list of required files

**Contains:**
- Required boot files (BOOT_METABLOOMS.py, RUN_METABLOOMS.py, etc.)
- Required control plane files (BOOT_STATE.json, boot_activator.py, etc.)
- Required directories (learning/, governance/, etc.)
- Boot validation rules

**You don't run this** - the validator reads it.

---

### 2. `validate_os_bundle.py`
**Purpose:** Check if bundle is bootable

**Usage:**
```bash
python scripts/validate_os_bundle.py <bundle.zip>
python scripts/validate_os_bundle.py <build_directory>
```

**Checks:**
- ✅ All boot files present
- ✅ Control plane complete
- ✅ Required directories exist
- ✅ boot_manifest.json configured correctly

**Returns:**
- Exit 0 = Valid and bootable
- Exit 1 = Invalid, shows errors

**Use this:**
- Before creating ZIP
- After creating ZIP
- Before distributing to users
- In automated watcher (prevent bad uploads)

---

### 3. `BUILD_CHECKLIST.md`
**Purpose:** Step-by-step manual build process

**Use when:**
- Building manually
- Learning the build process
- Debugging build failures
- Understanding what the automation does

**Key sections:**
- Boot files (CRITICAL - NEVER SKIP)
- Control plane
- Subsystems
- Validation checkpoints
- Failure recovery

---

### 4. `build_os_bundle.py`
**Purpose:** Automated build script

**Usage:**
```python
# From template (recommended)
!python scripts/build_os_bundle.py \
  --version v7.4.3 \
  --template existing_bundle.zip \
  --changelog "What changed"

# From source directory
!python scripts/build_os_bundle.py \
  --version v7.4.3 \
  --source /path/to/source \
  --changelog "What changed"
```

**What it does:**
1. Creates build directory
2. Copies ALL required files (uses build_manifest.json)
3. Generates VERSION_MANIFEST.json
4. Generates MEEP_Manifest.json (SHA256 for all files)
5. Validates build
6. Tests boot (actually runs RUN_METABLOOMS.py)
7. Creates ZIP
8. Validates ZIP
9. Generates build receipt

**Output:**
- ZIP bundle in `/mnt/data/`
- Build receipt with SHA256
- Validation report

**If any step fails:** Build stops, shows errors

---

## Integration with Watcher

Update your Termux/PowerShell watcher to validate before upload:

```bash
#!/bin/bash
# In your watcher script

DOWNLOADS="/storage/emulated/0/Download"
REPO="/path/to/metablooms-ltm"

inotifywait -m "$DOWNLOADS" -e create |
while read dir action file; do
  if [[ "$file" =~ MetaBlooms.*\.zip$ ]]; then
    echo "📥 Detected: $file"

    # VALIDATE BEFORE UPLOAD
    if python3 "$REPO/scripts/validate_os_bundle.py" "$DOWNLOADS/$file"; then
      echo "✅ Validation passed, uploading..."
      cp "$DOWNLOADS/$file" "$REPO/"
      cd "$REPO"
      git add "$file"
      git commit -m "Auto-upload: $file (validated)"
      git push origin main
    else
      echo "❌ Validation FAILED - not uploading"
      # Notify user
      termux-notification --title "Upload Blocked" \
        --content "$file failed validation"
    fi
  fi
done
```

**This prevents broken bundles from reaching GitHub.**

---

## Typical Workflow

### In ChatGPT Session 1:

```python
# Make improvements to MetaBlooms
# ... edit control_plane files, add features, etc. ...

# Build new bundle using automation
!python scripts/build_os_bundle.py \
  --version v7.4.3 \
  --template 2025-12-30_MetaBlooms_OS_CANONICAL_v7_4_1.zip \
  --changelog "Added MIPS index support" \
  --changelog "Fixed Termux path issues"

# Output shows:
# ✅ Build validation PASSED
# ✅ Boot test PASSED
# ✅ ZIP validation PASSED
# 📦 Bundle available at: /mnt/data/MetaBlooms_OS_CANONICAL_v7_4_3_2026-01-06.zip

# Download the bundle
# Watcher auto-uploads to GitHub (after validation)
```

### In ChatGPT Session 2:

```python
# Boot with new version (from Project Files or GitHub)
# All improvements from Session 1 are present
# Learning loop continues
```

---

## Failure Scenarios

### Scenario 1: Missing Boot Files

**Symptom:**
```
❌ Boot Files: FAIL
  CRITICAL: Missing required boot file: RUN_METABLOOMS.py (Primary runtime entrypoint)
```

**Fix:**
```python
# If using automation, check template source
# If manual, copy missing file:
cp RUN_METABLOOMS.py /mnt/data/metablooms_build/
```

### Scenario 2: Boot Test Failed

**Symptom:**
```
❌ Boot test FAILED - no BOOT_OK signal
```

**Fix:**
1. Check `control_plane/BOOT_STATE.json` exists
2. Check `boot_manifest.json` has correct entrypoint
3. Review error output from boot test
4. Fix issues
5. Re-run validator

### Scenario 3: Watcher Uploaded Broken Bundle

**Recovery:**
```bash
# In your repo
git log --oneline -10
# Find the bad commit

git revert <commit-hash>
git push origin main

# Next session will use previous working version
```

---

## Testing the Tools

### Test the validator on existing bundle:

```bash
python scripts/validate_os_bundle.py 2025-12-30_MetaBlooms_OS_CANONICAL_v7_4_1.zip
```

**Should show:** ✅ BUNDLE IS VALID AND BOOTABLE

### Test the automated builder:

```python
# Create a test build
!python scripts/build_os_bundle.py \
  --version v7.4.2-test \
  --template 2025-12-30_MetaBlooms_OS_CANONICAL_v7_4_1.zip \
  --changelog "Test build"

# Check output
# Should complete all steps successfully
```

---

## Maintenance

### Updating build_manifest.json

If you add new required files to MetaBlooms:

1. Edit `scripts/build_manifest.json`
2. Add file spec:
```json
{
  "path": "new_subsystem/critical_file.py",
  "required": true,
  "category": "new_subsystem",
  "purpose": "Description of what this does"
}
```
3. Commit changes
4. Future builds will require this file

### Updating the validator

If you change boot requirements:

1. Update `scripts/build_manifest.json` (required files)
2. Update `scripts/validate_os_bundle.py` (validation logic if needed)
3. Test on existing bundle
4. Commit changes

---

## Quick Reference

```bash
# Validate directory before zipping
python scripts/validate_os_bundle.py /mnt/data/metablooms_build

# Validate ZIP before distribution
python scripts/validate_os_bundle.py bundle.zip

# Automated build from template
python scripts/build_os_bundle.py --version v7.4.3 --template bundle.zip --changelog "Changes"

# Automated build from source
python scripts/build_os_bundle.py --version v7.4.3 --source /path/to/source --changelog "Changes"

# Read the manual checklist
cat scripts/BUILD_CHECKLIST.md
```

---

## Success Criteria

**You know the tools are working when:**

1. ✅ New bundles **always** boot successfully
2. ✅ Validation catches missing files **before** distribution
3. ✅ Watcher **never** uploads broken bundles
4. ✅ "Missing boot path" failure **never** happens again
5. ✅ Build receipts provide audit trail (SHA256 hashes)
6. ✅ Rollback is possible (previous versions preserved)

**If you see `BOOT_FAILED` again:**
- Check if validation was skipped
- Check if watcher validation is enabled
- Review build logs

The tools only work if you **use them** - make validation mandatory.
