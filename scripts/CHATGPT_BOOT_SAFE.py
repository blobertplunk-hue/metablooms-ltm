#!/usr/bin/env python3
"""
Safe MetaBlooms Boot for ChatGPT

This script GUARANTEES the entrypoint exists before attempting to boot.
Use this instead of manual extraction + boot to prevent "missing entrypoint" failures.

Usage in ChatGPT:
    !python scripts/CHATGPT_BOOT_SAFE.py

This will:
1. Find MetaBlooms bundle in current directory or Project Files
2. Extract to /mnt/data/mb_runtime (safe location)
3. VERIFY entrypoint exists
4. Boot MetaBlooms
5. Display activation status

If entrypoint is missing, it FAILS EARLY with clear error message.
"""

import glob
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path


def log(msg, level="INFO"):
    """Colored logging"""
    colors = {"INFO": "\033[94m", "OK": "\033[92m", "ERR": "\033[91m", "WARN": "\033[93m", "": "\033[0m"}
    icons = {"INFO": "ℹ️ ", "OK": "✅", "ERR": "❌", "WARN": "⚠️ "}
    print(f"{colors.get(level, '')}{icons.get(level, '')}{msg}{colors['']}", flush=True)


def find_bundle():
    """Find MetaBlooms bundle"""
    log("Searching for MetaBlooms bundle...")

    # Search patterns
    patterns = [
        "MetaBlooms_OS*.zip",
        "metablooms*.zip",
        "*.zip"
    ]

    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            # Sort by modification time, newest first
            matches.sort(key=os.path.getmtime, reverse=True)
            bundle = matches[0]
            log(f"Found: {bundle}", "OK")
            return Path(bundle)

    log("No bundle found in current directory", "ERR")
    return None


def extract_bundle(bundle_path, dest):
    """Extract bundle safely"""
    log(f"Extracting to: {dest}")

    dest.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(bundle_path, 'r') as zf:
            zf.extractall(dest)

        file_count = len(list(dest.rglob("*")))
        log(f"Extracted {file_count} files", "OK")
        return True

    except Exception as e:
        log(f"Extraction failed: {e}", "ERR")
        return False


def verify_entrypoint(dest):
    """Verify entrypoint exists - CRITICAL CHECK"""
    log("Verifying entrypoint...")

    # Check boot_manifest.json first
    manifest_path = dest / "boot_manifest.json"

    if not manifest_path.exists():
        log("boot_manifest.json NOT FOUND", "ERR")
        return None

    with open(manifest_path) as f:
        manifest = json.load(f)

    entrypoint_name = manifest.get("entrypoint", "RUN_METABLOOMS.py")
    entrypoint_path = dest / entrypoint_name

    if not entrypoint_path.exists():
        log(f"ENTRYPOINT MISSING: {entrypoint_name}", "ERR")
        log(f"Expected at: {entrypoint_path}", "ERR")

        # List what files ARE present
        log("Files that ARE present:", "WARN")
        for f in sorted(dest.rglob("*.py"))[:10]:
            print(f"  - {f.relative_to(dest)}")

        return None

    log(f"Entrypoint found: {entrypoint_name}", "OK")
    return entrypoint_path


def verify_critical_files(dest):
    """Verify other critical files"""
    log("Verifying critical files...")

    required = [
        "control_plane/BOOT_STATE.json",
        "control_plane/boot_activator.py",
    ]

    missing = []
    for req in required:
        if not (dest / req).exists():
            missing.append(req)

    if missing:
        log(f"Missing {len(missing)} critical files:", "WARN")
        for m in missing:
            print(f"  - {m}")
        return False

    log("All critical files present", "OK")
    return True


def boot_metablooms(entrypoint_path, dest):
    """Boot MetaBlooms"""
    log(f"Booting MetaBlooms from: {entrypoint_path}")

    try:
        result = subprocess.run(
            [sys.executable, str(entrypoint_path)],
            cwd=str(dest),
            capture_output=True,
            text=True,
            timeout=15
        )

        print("\n" + "="*70)
        print(result.stdout)
        print("="*70 + "\n")

        if "BOOT_OK" in result.stdout:
            log("Boot successful!", "OK")

            # Show activation status if available
            status_files = list(dest.glob("control_plane/state_hub/activation_status_*.json"))
            if status_files:
                with open(status_files[-1]) as f:
                    status = json.load(f)

                active_count = sum(1 for v in status.values() if v.get("status") == "ACTIVE")
                log(f"Active subsystems: {active_count}/{len(status)}", "OK")

            return True

        else:
            log("Boot failed - no BOOT_OK signal", "ERR")
            if result.stderr:
                print("STDERR:", result.stderr)
            return False

    except subprocess.TimeoutExpired:
        log("Boot timed out", "ERR")
        return False
    except Exception as e:
        log(f"Boot error: {e}", "ERR")
        return False


def main():
    print("\n" + "="*70)
    print("MetaBlooms Safe Boot for ChatGPT")
    print("="*70 + "\n")

    # Step 1: Find bundle
    bundle = find_bundle()
    if not bundle:
        log("ERROR: No MetaBlooms bundle found", "ERR")
        log("Upload a MetaBlooms_OS_*.zip file first", "WARN")
        return 1

    # Step 2: Extract
    dest = Path("/mnt/data/mb_runtime")
    if not extract_bundle(bundle, dest):
        return 1

    # Step 3: Verify entrypoint (CRITICAL)
    entrypoint = verify_entrypoint(dest)
    if not entrypoint:
        log("FATAL: Entrypoint not found after extraction", "ERR")
        log("The bundle may be corrupted or incomplete", "ERR")
        log("DO NOT ATTEMPT TO BOOT", "ERR")
        return 1

    # Step 4: Verify other files
    if not verify_critical_files(dest):
        log("Some critical files missing, boot may fail", "WARN")

    # Step 5: Boot
    if not boot_metablooms(entrypoint, dest):
        return 1

    # Success
    print("\n" + "="*70)
    log("MetaBlooms is ready!", "OK")
    print("="*70 + "\n")

    log(f"Runtime location: {dest}", "INFO")
    log("You can now interact with MetaBlooms", "INFO")

    return 0


if __name__ == "__main__":
    sys.exit(main())
