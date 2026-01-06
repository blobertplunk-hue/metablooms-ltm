#!/usr/bin/env python3
"""
Validate MetaBlooms OS Bundle Before Distribution

This script ensures that a MetaBlooms OS bundle contains all required files
for successful boot, preventing the "missing boot path" failure mode.

Usage:
    python scripts/validate_os_bundle.py <bundle.zip>
    python scripts/validate_os_bundle.py <extracted_directory>

Returns:
    0 if bundle is valid and bootable
    1 if bundle has errors
"""

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def load_build_manifest(manifest_path: Path) -> dict:
    """Load the canonical build manifest"""
    if not manifest_path.exists():
        print(f"{Colors.RED}❌ Build manifest not found: {manifest_path}{Colors.RESET}")
        sys.exit(1)

    with open(manifest_path) as f:
        return json.load(f)


def check_zip_contents(zip_path: Path) -> Tuple[bool, List[str]]:
    """Check if zip file contains all required files"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            return True, zf.namelist()
    except Exception as e:
        return False, [f"Failed to read zip: {e}"]


def check_directory_contents(dir_path: Path) -> Tuple[bool, List[str]]:
    """Check if directory contains all required files"""
    if not dir_path.is_dir():
        return False, [f"Not a directory: {dir_path}"]

    files = []
    for item in dir_path.rglob("*"):
        if item.is_file():
            files.append(str(item.relative_to(dir_path)))

    return True, files


def validate_boot_files(file_list: List[str], manifest: dict) -> Tuple[bool, List[str]]:
    """Validate that all required boot files are present"""
    errors = []
    warnings = []

    for file_spec in manifest["required_boot_files"]:
        file_path = file_spec["path"]
        required = file_spec["required"]

        if file_path not in file_list:
            if required:
                errors.append(f"CRITICAL: Missing required boot file: {file_path} ({file_spec['purpose']})")
            else:
                warnings.append(f"WARNING: Missing optional file: {file_path}")

    return len(errors) == 0, errors + warnings


def validate_control_plane(file_list: List[str], manifest: dict) -> Tuple[bool, List[str]]:
    """Validate control plane files"""
    errors = []
    warnings = []

    for file_spec in manifest["required_control_plane_files"]:
        file_path = file_spec["path"]
        required = file_spec["required"]

        if file_path not in file_list:
            if required:
                errors.append(f"CRITICAL: Missing control plane file: {file_path} ({file_spec['purpose']})")
            else:
                warnings.append(f"WARNING: Missing optional file: {file_path}")

    return len(errors) == 0, errors + warnings


def validate_directories(file_list: List[str], manifest: dict) -> Tuple[bool, List[str]]:
    """Validate that required directories exist (by checking for files within them)"""
    errors = []

    for required_dir in manifest["required_directories"]:
        # Check if any file starts with this directory path
        has_files_in_dir = any(f.startswith(required_dir + "/") for f in file_list)

        if not has_files_in_dir:
            errors.append(f"CRITICAL: Required directory missing or empty: {required_dir}")

    return len(errors) == 0, errors


def validate_boot_manifest_config(bundle_path: Path, is_zip: bool) -> Tuple[bool, List[str]]:
    """Validate boot_manifest.json configuration"""
    errors = []

    try:
        if is_zip:
            with zipfile.ZipFile(bundle_path, 'r') as zf:
                if 'boot_manifest.json' not in zf.namelist():
                    return False, ["boot_manifest.json not found in bundle"]

                with zf.open('boot_manifest.json') as f:
                    boot_manifest = json.load(f)
        else:
            boot_manifest_path = bundle_path / "boot_manifest.json"
            if not boot_manifest_path.exists():
                return False, ["boot_manifest.json not found in bundle"]

            with open(boot_manifest_path) as f:
                boot_manifest = json.load(f)

        # Check entrypoint
        entrypoint = boot_manifest.get("entrypoint")
        if not entrypoint:
            errors.append("boot_manifest.json missing 'entrypoint' field")
        elif entrypoint != "RUN_METABLOOMS.py":
            errors.append(f"boot_manifest.json entrypoint is '{entrypoint}', expected 'RUN_METABLOOMS.py'")

        # Check success signal
        if "success_signal" not in boot_manifest:
            errors.append("boot_manifest.json missing 'success_signal' field")

    except Exception as e:
        errors.append(f"Failed to validate boot_manifest.json: {e}")

    return len(errors) == 0, errors


def print_report(results: Dict[str, Tuple[bool, List[str]]]):
    """Print validation report"""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}MetaBlooms OS Bundle Validation Report{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")

    all_passed = True

    for category, (passed, messages) in results.items():
        if passed:
            print(f"{Colors.GREEN}✅ {category}: PASS{Colors.RESET}")
        else:
            print(f"{Colors.RED}❌ {category}: FAIL{Colors.RESET}")
            all_passed = False

        for msg in messages:
            if msg.startswith("CRITICAL"):
                print(f"  {Colors.RED}{msg}{Colors.RESET}")
            elif msg.startswith("WARNING"):
                print(f"  {Colors.YELLOW}{msg}{Colors.RESET}")
            else:
                print(f"  {msg}")

        print()

    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}")

    if all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}✅ BUNDLE IS VALID AND BOOTABLE{Colors.RESET}")
        print(f"{Colors.GREEN}This bundle can be safely distributed.{Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ BUNDLE VALIDATION FAILED{Colors.RESET}")
        print(f"{Colors.RED}DO NOT DISTRIBUTE this bundle - it will fail to boot.{Colors.RESET}")
        print(f"{Colors.YELLOW}Fix the errors above and re-validate.{Colors.RESET}\n")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Validate MetaBlooms OS bundle for bootability",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a zip bundle
  python scripts/validate_os_bundle.py MetaBlooms_OS_v7_4_2.zip

  # Validate an extracted directory
  python scripts/validate_os_bundle.py /tmp/metablooms_build/

  # Use in build pipeline
  python scripts/validate_os_bundle.py bundle.zip && echo "Safe to upload"
        """
    )
    parser.add_argument("bundle", help="Path to zip bundle or extracted directory")
    parser.add_argument("--manifest", default="scripts/build_manifest.json",
                       help="Path to build manifest (default: scripts/build_manifest.json)")

    args = parser.parse_args()

    bundle_path = Path(args.bundle)
    manifest_path = Path(args.manifest)

    if not bundle_path.exists():
        print(f"{Colors.RED}❌ Bundle not found: {bundle_path}{Colors.RESET}")
        return 1

    # Load canonical build manifest
    manifest = load_build_manifest(manifest_path)

    # Determine if zip or directory
    is_zip = bundle_path.suffix == '.zip'

    # Get file list
    if is_zip:
        success, file_list = check_zip_contents(bundle_path)
        bundle_type = "ZIP"
    else:
        success, file_list = check_directory_contents(bundle_path)
        bundle_type = "DIRECTORY"

    if not success:
        print(f"{Colors.RED}❌ Failed to read bundle: {file_list[0]}{Colors.RESET}")
        return 1

    print(f"{Colors.BLUE}Validating {bundle_type}: {bundle_path}{Colors.RESET}")
    print(f"{Colors.BLUE}Found {len(file_list)} files{Colors.RESET}")

    # Run validations
    results = {}

    results["Boot Files"] = validate_boot_files(file_list, manifest)
    results["Control Plane"] = validate_control_plane(file_list, manifest)
    results["Required Directories"] = validate_directories(file_list, manifest)
    results["Boot Configuration"] = validate_boot_manifest_config(bundle_path, is_zip)

    # Print report and return status
    return print_report(results)


if __name__ == "__main__":
    sys.exit(main())
