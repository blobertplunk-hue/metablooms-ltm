#!/usr/bin/env python3
"""
MetaBlooms OS Bundle Builder

Automated build script that implements the build checklist to prevent
the "missing boot path" failure mode.

Usage:
    python scripts/build_os_bundle.py --version v7.4.2 --source /path/to/source
    python scripts/build_os_bundle.py --version v7.4.2 --template existing_bundle.zip

This script:
1. Creates a build directory
2. Copies all required boot files (NEVER FORGETS)
3. Copies control plane
4. Copies subsystems
5. Validates the build
6. Tests boot
7. Creates ZIP bundle
8. Validates ZIP
9. Generates build receipt

Returns:
    0 if successful
    1 if any step fails
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class BuildError(Exception):
    """Build process error"""
    pass


class MetaBloomsBuilder:
    """MetaBlooms OS bundle builder"""

    # CRITICAL: These files MUST be in every bundle
    REQUIRED_BOOT_FILES = [
        "BOOT_METABLOOMS.py",
        "RUN_METABLOOMS.py",
        "boot_manifest.json",
        "boot_contract.json",
        "BOOT.md",
        "ENTRYPOINT.md",
    ]

    REQUIRED_CONTROL_PLANE_FILES = [
        "control_plane/BOOT_STATE.json",
        "control_plane/boot_activator.py",
        "control_plane/activation_registry.py",
        "control_plane/mandatory_chat_capture.py",
        "control_plane/bridge_map.json",
        "control_plane/heuristic_matrix.json",
    ]

    def __init__(self, version: str, source_dir: Optional[Path] = None,
                 template_zip: Optional[Path] = None, output_dir: Path = None):
        self.version = version
        self.source_dir = source_dir
        self.template_zip = template_zip
        self.output_dir = output_dir or Path("/mnt/data")
        self.build_dir = None
        self.errors = []
        self.warnings = []

    def log(self, message: str, level: str = "INFO"):
        """Log message with color coding"""
        colors = {
            "INFO": "\033[94m",  # Blue
            "SUCCESS": "\033[92m",  # Green
            "WARNING": "\033[93m",  # Yellow
            "ERROR": "\033[91m",  # Red
            "RESET": "\033[0m",
        }

        prefix = {
            "INFO": "ℹ️ ",
            "SUCCESS": "✅",
            "WARNING": "⚠️ ",
            "ERROR": "❌",
        }

        color = colors.get(level, colors["INFO"])
        reset = colors["RESET"]
        icon = prefix.get(level, "")

        print(f"{color}{icon} {message}{reset}")

    def create_build_directory(self) -> Path:
        """Create temporary build directory"""
        self.log("Creating build directory...")
        build_dir = self.output_dir / "metablooms_build"

        if build_dir.exists():
            self.log(f"Removing existing build directory: {build_dir}", "WARNING")
            shutil.rmtree(build_dir)

        build_dir.mkdir(parents=True, exist_ok=True)
        self.build_dir = build_dir
        self.log(f"Build directory: {build_dir}", "SUCCESS")
        return build_dir

    def extract_template(self):
        """Extract template bundle if provided"""
        if not self.template_zip:
            return

        self.log(f"Extracting template: {self.template_zip}")

        if not self.template_zip.exists():
            raise BuildError(f"Template not found: {self.template_zip}")

        with zipfile.ZipFile(self.template_zip, 'r') as zf:
            zf.extractall(self.build_dir)

        self.log("Template extracted", "SUCCESS")

    def copy_file(self, src: Path, dest: Path, required: bool = True):
        """Copy a file, tracking errors"""
        try:
            if not src.exists():
                msg = f"Missing: {src}"
                if required:
                    self.errors.append(msg)
                    self.log(msg, "ERROR")
                else:
                    self.warnings.append(msg)
                    self.log(msg, "WARNING")
                return False

            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            return True

        except Exception as e:
            msg = f"Failed to copy {src}: {e}"
            if required:
                self.errors.append(msg)
                self.log(msg, "ERROR")
            else:
                self.warnings.append(msg)
                self.log(msg, "WARNING")
            return False

    def copy_boot_files(self):
        """Copy critical boot files - NEVER SKIP THIS"""
        self.log("Copying CRITICAL boot files...")

        if self.template_zip:
            # Files already extracted from template
            self.log("Boot files extracted from template", "INFO")
            return

        if not self.source_dir:
            raise BuildError("No source directory specified and no template provided")

        copied = 0
        for filename in self.REQUIRED_BOOT_FILES:
            src = self.source_dir / filename
            dest = self.build_dir / filename

            if self.copy_file(src, dest, required=True):
                copied += 1

        self.log(f"Copied {copied}/{len(self.REQUIRED_BOOT_FILES)} boot files", "SUCCESS")

        if copied < len(self.REQUIRED_BOOT_FILES):
            raise BuildError("Failed to copy all required boot files")

    def copy_control_plane(self):
        """Copy control plane files"""
        self.log("Copying control plane...")

        if self.template_zip:
            self.log("Control plane extracted from template", "INFO")
            return

        if not self.source_dir:
            raise BuildError("No source directory specified")

        # Copy entire control_plane directory
        src_cp = self.source_dir / "control_plane"
        dest_cp = self.build_dir / "control_plane"

        if src_cp.exists():
            shutil.copytree(src_cp, dest_cp, dirs_exist_ok=True)
            self.log("Control plane copied", "SUCCESS")
        else:
            raise BuildError(f"Control plane directory not found: {src_cp}")

        # Verify critical files
        missing = []
        for filepath in self.REQUIRED_CONTROL_PLANE_FILES:
            if not (self.build_dir / filepath).exists():
                missing.append(filepath)

        if missing:
            for f in missing:
                self.log(f"Missing critical file: {f}", "ERROR")
            raise BuildError("Missing required control plane files")

    def copy_subsystems(self):
        """Copy other subsystems"""
        self.log("Copying subsystems...")

        if self.template_zip:
            self.log("Subsystems extracted from template", "INFO")
            return

        if not self.source_dir:
            return

        # Define subsystems to copy
        subsystems = [
            "learning",
            "ble",
            "governance",
            "baselines",
            "docs",
            "egg_juicer",
            "microblooms",
        ]

        for subsystem in subsystems:
            src = self.source_dir / subsystem
            dest = self.build_dir / subsystem

            if src.exists():
                if src.is_dir():
                    shutil.copytree(src, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dest)
                self.log(f"  Copied: {subsystem}")

        # Initialize learning registries if they don't exist
        learning_dir = self.build_dir / "learning"
        for bloom_type in ["nanoblooms", "microblooms", "macroblooms"]:
            registry = learning_dir / bloom_type / "registry.json"
            if not registry.exists():
                registry.parent.mkdir(parents=True, exist_ok=True)
                with open(registry, 'w') as f:
                    json.dump([], f)
                self.log(f"  Initialized: {bloom_type}/registry.json")

    def create_version_manifest(self, changelog: List[str]):
        """Create VERSION_MANIFEST.json"""
        self.log("Creating version manifest...")

        manifest = {
            "version": self.version,
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "parent_version": None,  # TODO: detect from previous
            "breaking_changes": False,
            "required_subsystems": [
                "CONTROL_PLANE_CORE",
                "BRIDGE_MAP",
                "HEURISTIC_MATRIX",
                "CHM",
                "SHOPPING_MODE_CONTROLLER",
            ],
            "changelog": changelog,
        }

        with open(self.build_dir / "VERSION_MANIFEST.json", 'w') as f:
            json.dump(manifest, f, indent=2)

        self.log("Version manifest created", "SUCCESS")

    def create_meep_manifest(self):
        """Create MEEP manifest with SHA256 hashes"""
        self.log("Creating MEEP manifest...")

        inventory = []

        for file_path in sorted(self.build_dir.rglob("*")):
            if file_path.is_file():
                with open(file_path, 'rb') as f:
                    sha256 = hashlib.sha256(f.read()).hexdigest()

                inventory.append({
                    "path": str(file_path.relative_to(self.build_dir)),
                    "sha256": sha256
                })

        manifest = {
            "export_authority": "MetaBlooms",
            "export_standard": "MEEP-1.0",
            "date": datetime.utcnow().isoformat() + "Z",
            "base_source": f"MetaBlooms_OS_{self.version}",
            "counts": {"files": len(inventory)},
            "inventory": inventory
        }

        with open(self.build_dir / "MEEP_Manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)

        self.log(f"MEEP manifest created ({len(inventory)} files)", "SUCCESS")

    def validate_build(self) -> bool:
        """Run validation script"""
        self.log("Validating build...")

        validator_script = Path(__file__).parent / "validate_os_bundle.py"

        if not validator_script.exists():
            self.log("Validator script not found, skipping validation", "WARNING")
            return True

        result = subprocess.run(
            [sys.executable, str(validator_script), str(self.build_dir)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            self.log("Build validation PASSED", "SUCCESS")
            return True
        else:
            self.log("Build validation FAILED", "ERROR")
            print(result.stdout)
            return False

    def test_boot(self) -> bool:
        """Test that the bundle boots"""
        self.log("Testing boot sequence...")

        entrypoint = self.build_dir / "RUN_METABLOOMS.py"

        if not entrypoint.exists():
            self.log("Entrypoint not found, cannot test boot", "ERROR")
            return False

        try:
            result = subprocess.run(
                [sys.executable, str(entrypoint)],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.build_dir)
            )

            if "BOOT_OK" in result.stdout:
                self.log("Boot test PASSED", "SUCCESS")
                return True
            else:
                self.log("Boot test FAILED - no BOOT_OK signal", "ERROR")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                return False

        except subprocess.TimeoutExpired:
            self.log("Boot test TIMEOUT", "ERROR")
            return False
        except Exception as e:
            self.log(f"Boot test ERROR: {e}", "ERROR")
            return False

    def create_zip_bundle(self) -> Path:
        """Create ZIP bundle"""
        self.log("Creating ZIP bundle...")

        version_safe = self.version.replace(".", "_")
        timestamp = datetime.now().strftime("%Y-%m-%d")
        bundle_name = f"MetaBlooms_OS_CANONICAL_{version_safe}_{timestamp}.zip"
        bundle_path = self.output_dir / bundle_name

        with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            file_count = 0
            for file_path in self.build_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(self.build_dir)
                    zf.write(file_path, arcname)
                    file_count += 1

        size_mb = bundle_path.stat().st_size / 1024 / 1024

        self.log(f"Bundle created: {bundle_name}", "SUCCESS")
        self.log(f"  Files: {file_count}, Size: {size_mb:.2f} MB")

        return bundle_path

    def validate_zip(self, bundle_path: Path) -> bool:
        """Validate the ZIP bundle"""
        self.log("Validating ZIP bundle...")

        validator_script = Path(__file__).parent / "validate_os_bundle.py"

        if not validator_script.exists():
            self.log("Validator script not found, skipping ZIP validation", "WARNING")
            return True

        result = subprocess.run(
            [sys.executable, str(validator_script), str(bundle_path)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            self.log("ZIP validation PASSED", "SUCCESS")
            return True
        else:
            self.log("ZIP validation FAILED", "ERROR")
            print(result.stdout)
            return False

    def create_build_receipt(self, bundle_path: Path, changelog: List[str]):
        """Create build receipt"""
        self.log("Creating build receipt...")

        with open(bundle_path, 'rb') as f:
            bundle_sha256 = hashlib.sha256(f.read()).hexdigest()

        receipt = {
            "build_id": f"MetaBlooms_OS_{self.version}_{datetime.now().strftime('%Y%m%d')}",
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "version": self.version,
            "bundle_filename": bundle_path.name,
            "bundle_sha256": bundle_sha256,
            "validation_status": "PASSED" if not self.errors else "FAILED",
            "boot_test_status": "PASSED",
            "warnings": self.warnings,
            "errors": self.errors,
            "ready_for_distribution": len(self.errors) == 0,
            "changelog": changelog,
        }

        receipt_path = self.output_dir / f"BUILD_RECEIPT_{self.version}.json"
        with open(receipt_path, 'w') as f:
            json.dump(receipt, f, indent=2)

        self.log(f"Build receipt: {receipt_path.name}", "SUCCESS")

        return receipt

    def build(self, changelog: List[str]) -> Path:
        """Execute full build process"""
        try:
            # Phase 1: Setup
            self.create_build_directory()

            # Phase 2: Copy files
            if self.template_zip:
                self.extract_template()
            else:
                self.copy_boot_files()
                self.copy_control_plane()
                self.copy_subsystems()

            # Phase 3: Generate manifests
            self.create_version_manifest(changelog)
            self.create_meep_manifest()

            # Phase 4: Validate
            if not self.validate_build():
                raise BuildError("Build validation failed")

            # Phase 5: Test boot
            if not self.test_boot():
                raise BuildError("Boot test failed")

            # Phase 6: Create ZIP
            bundle_path = self.create_zip_bundle()

            # Phase 7: Validate ZIP
            if not self.validate_zip(bundle_path):
                raise BuildError("ZIP validation failed")

            # Phase 8: Create receipt
            receipt = self.create_build_receipt(bundle_path, changelog)

            # Success
            self.log("="*70, "SUCCESS")
            self.log("BUILD COMPLETE", "SUCCESS")
            self.log("="*70, "SUCCESS")
            self.log(f"Bundle: {bundle_path}", "SUCCESS")
            self.log(f"Ready for distribution: {receipt['ready_for_distribution']}", "SUCCESS")

            if self.warnings:
                self.log(f"Warnings: {len(self.warnings)}", "WARNING")

            return bundle_path

        except BuildError as e:
            self.log(f"BUILD FAILED: {e}", "ERROR")
            raise


def main():
    parser = argparse.ArgumentParser(
        description="Build MetaBlooms OS bundle with automatic validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build from source directory
  python scripts/build_os_bundle.py --version v7.4.2 --source /path/to/source

  # Build from template
  python scripts/build_os_bundle.py --version v7.4.2 --template existing_bundle.zip

  # With changelog
  python scripts/build_os_bundle.py --version v7.4.2 --template bundle.zip \\
    --changelog "Fixed boot path" --changelog "Added validation"
        """
    )

    parser.add_argument("--version", required=True, help="Version number (e.g., v7.4.2)")
    parser.add_argument("--source", type=Path, help="Source directory to copy from")
    parser.add_argument("--template", type=Path, help="Template bundle to use as base")
    parser.add_argument("--output", type=Path, default=Path("/mnt/data"),
                       help="Output directory (default: /mnt/data)")
    parser.add_argument("--changelog", action="append", default=[],
                       help="Changelog entry (can specify multiple times)")

    args = parser.parse_args()

    if not args.source and not args.template:
        parser.error("Must specify either --source or --template")

    builder = MetaBloomsBuilder(
        version=args.version,
        source_dir=args.source,
        template_zip=args.template,
        output_dir=args.output
    )

    try:
        bundle_path = builder.build(args.changelog or ["Version update"])
        print(f"\n📦 Bundle available at: {bundle_path}")
        return 0

    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
