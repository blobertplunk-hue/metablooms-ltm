#!/usr/bin/env python3
"""
MetaBlooms Bundle Extractor with Validation

Safely extract MetaBlooms bundle and verify all critical files are present
BEFORE attempting to boot. Prevents "missing entrypoint" failures.

Usage in ChatGPT:
    python scripts/extract_and_validate.py --bundle <bundle.zip> --dest /mnt/data/mb_runtime

Returns:
    0 if extraction successful and validated
    1 if extraction or validation failed
"""

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import List, Tuple


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


# CRITICAL: These files MUST exist after extraction
REQUIRED_FILES = [
    "RUN_METABLOOMS.py",  # PRIMARY ENTRYPOINT
    "BOOT_METABLOOMS.py",
    "boot_manifest.json",
    "control_plane/BOOT_STATE.json",
    "control_plane/boot_activator.py",
]


def log(message: str, level: str = "INFO"):
    """Log with colors"""
    colors = {
        "INFO": Colors.BLUE,
        "SUCCESS": Colors.GREEN,
        "WARNING": Colors.YELLOW,
        "ERROR": Colors.RED,
    }
    icons = {
        "INFO": "ℹ️ ",
        "SUCCESS": "✅",
        "WARNING": "⚠️ ",
        "ERROR": "❌",
    }

    color = colors.get(level, Colors.BLUE)
    icon = icons.get(level, "")
    print(f"{color}{icon} {message}{Colors.RESET}")


def extract_bundle(bundle_path: Path, dest_path: Path) -> Tuple[bool, str]:
    """Extract bundle with error handling"""
    try:
        log(f"Extracting: {bundle_path}")
        log(f"Destination: {dest_path}")

        if not bundle_path.exists():
            return False, f"Bundle not found: {bundle_path}"

        # Create destination
        dest_path.mkdir(parents=True, exist_ok=True)

        # Extract
        with zipfile.ZipFile(bundle_path, 'r') as zf:
            file_list = zf.namelist()
            log(f"Bundle contains {len(file_list)} files")

            zf.extractall(dest_path)

        log(f"Extracted {len(file_list)} files", "SUCCESS")
        return True, f"Extracted {len(file_list)} files"

    except Exception as e:
        return False, f"Extraction failed: {e}"


def verify_critical_files(dest_path: Path) -> Tuple[bool, List[str]]:
    """Verify all critical files exist after extraction"""
    log("Verifying critical files...")

    missing = []

    for required_file in REQUIRED_FILES:
        file_path = dest_path / required_file

        if not file_path.exists():
            missing.append(required_file)
            log(f"MISSING: {required_file}", "ERROR")
        else:
            log(f"Found: {required_file}")

    if missing:
        return False, missing
    else:
        log("All critical files present", "SUCCESS")
        return True, []


def verify_boot_manifest(dest_path: Path) -> Tuple[bool, str]:
    """Verify boot_manifest.json is correct"""
    log("Verifying boot manifest...")

    manifest_path = dest_path / "boot_manifest.json"

    if not manifest_path.exists():
        return False, "boot_manifest.json not found"

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)

        # Check entrypoint
        entrypoint = manifest.get("entrypoint")

        if not entrypoint:
            return False, "boot_manifest.json missing 'entrypoint' field"

        # Verify entrypoint file exists
        entrypoint_path = dest_path / entrypoint

        if not entrypoint_path.exists():
            return False, f"Entrypoint specified but not found: {entrypoint}"

        log(f"Entrypoint: {entrypoint}", "SUCCESS")
        return True, entrypoint

    except Exception as e:
        return False, f"Failed to read boot_manifest.json: {e}"


def print_boot_instructions(dest_path: Path, entrypoint: str):
    """Print how to boot"""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
    print(f"{Colors.GREEN}{Colors.BOLD}✅ EXTRACTION VALIDATED - READY TO BOOT{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")

    print(f"{Colors.BOLD}To boot MetaBlooms:{Colors.RESET}")
    print(f"  cd {dest_path}")
    print(f"  python {entrypoint}")
    print()
    print(f"{Colors.BOLD}Expected output:{Colors.RESET}")
    print(f"  BOOT_OK")
    print(f"  MetaBlooms OS READY")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Safely extract and validate MetaBlooms bundle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage in ChatGPT:

  # Extract bundle from Project Files
  !python scripts/extract_and_validate.py \\
    --bundle MetaBlooms_OS_v7_4_1.zip \\
    --dest /mnt/data/mb_runtime

  # If validation passes, boot:
  !cd /mnt/data/mb_runtime && python RUN_METABLOOMS.py

This prevents "missing entrypoint" failures by validating BEFORE boot.
        """
    )

    parser.add_argument("--bundle", required=True, help="Path to MetaBlooms bundle ZIP")
    parser.add_argument("--dest", required=True, help="Destination directory for extraction")

    args = parser.parse_args()

    bundle_path = Path(args.bundle)
    dest_path = Path(args.dest)

    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}MetaBlooms Bundle Extraction & Validation{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")

    # Step 1: Extract
    success, message = extract_bundle(bundle_path, dest_path)

    if not success:
        log(message, "ERROR")
        print(f"\n{Colors.RED}{Colors.BOLD}❌ EXTRACTION FAILED{Colors.RESET}")
        return 1

    # Step 2: Verify critical files
    success, missing = verify_critical_files(dest_path)

    if not success:
        log(f"Missing {len(missing)} critical files:", "ERROR")
        for file in missing:
            print(f"  - {file}")

        print(f"\n{Colors.RED}{Colors.BOLD}❌ VALIDATION FAILED{Colors.RESET}")
        print(f"{Colors.RED}DO NOT BOOT - critical files missing{Colors.RESET}")
        print(f"{Colors.YELLOW}The bundle may be corrupted or incomplete.{Colors.RESET}")
        return 1

    # Step 3: Verify boot manifest
    success, result = verify_boot_manifest(dest_path)

    if not success:
        log(result, "ERROR")
        print(f"\n{Colors.RED}{Colors.BOLD}❌ BOOT MANIFEST INVALID{Colors.RESET}")
        return 1

    entrypoint = result

    # Success!
    print_boot_instructions(dest_path, entrypoint)

    return 0


if __name__ == "__main__":
    sys.exit(main())
