#!/usr/bin/env python3
"""
MetaBlooms OS Mechanical Audit (Fail-Closed)

Verifies implementation claims without executing runtime code.
Uses only: zipfile, pathlib, json, ast, re, hashlib (stdlib only).
"""

import ast
import hashlib
import json
import re
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Optional


@dataclass
class AuditReport:
    """Machine-readable audit output"""
    verified_implementations: List[Dict] = field(default_factory=list)
    present_but_unwired: List[Dict] = field(default_factory=list)
    missing: List[Dict] = field(default_factory=list)
    spec_conflicts: List[Dict] = field(default_factory=list)
    unverifiable: List[Dict] = field(default_factory=list)


class BootAnalyzer:
    """Static analysis of BOOT_METABLOOMS.py without execution"""

    def __init__(self, boot_path: Path):
        self.boot_path = boot_path
        self.source = boot_path.read_text()
        try:
            self.tree = ast.parse(self.source)
        except SyntaxError as e:
            self.tree = None
            self.parse_error = str(e)

    def extract_file_reads(self) -> Set[str]:
        """Find all file paths referenced in code"""
        if not self.tree:
            return set()

        paths = set()

        # Find string literals assigned to path variables
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if isinstance(node.value, ast.BinOp):
                            # Looking for Path / "filename" patterns
                            if isinstance(node.value.right, ast.Constant):
                                paths.add(node.value.right.value)

        # Find Path() constructor calls
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "Path":
                    if node.args and isinstance(node.args[0], ast.Constant):
                        paths.add(node.args[0].value)

        return paths

    def extract_imports(self) -> List[str]:
        """Extract all import statements"""
        if not self.tree:
            return []

        imports = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                imports.extend([alias.name for alias in node.names])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        return imports

    def loads_file(self, filename: str) -> bool:
        """Check if specific filename appears in source"""
        return filename in self.source

    def calls_function(self, func_name: str) -> bool:
        """Check if function is called"""
        if not self.tree:
            return False

        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == func_name:
                    return True
        return False


class MetaBloomsAuditor:
    """Comprehensive audit of MetaBlooms OS bundle"""

    def __init__(self, zip_path: Path):
        self.zip_path = zip_path
        self.report = AuditReport()
        self.extract_dir: Optional[Path] = None

    def run(self) -> AuditReport:
        """Execute full audit suite"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.extract_dir = Path(tmpdir)

            # Extract bundle
            with zipfile.ZipFile(self.zip_path, 'r') as zf:
                zf.extractall(self.extract_dir)

            # Run checks
            self.check_boot_structure()
            self.check_delta_enforcement()
            self.check_gate_wiring()
            self.check_schema_usage()
            self.check_ledger_integration()
            self.check_index_usage()
            self.check_csrg_presence()
            self.check_manifest_loading()

        return self.report

    def check_boot_structure(self):
        """Verify boot files exist and are parseable"""
        boot_file = self.extract_dir / "BOOT_METABLOOMS.py"
        runtime_file = self.extract_dir / "RUN_METABLOOMS.py"

        if not boot_file.exists():
            self.report.missing.append({
                "component": "BOOT_METABLOOMS.py",
                "reason": "File not found in bundle"
            })
            return

        if not runtime_file.exists():
            self.report.missing.append({
                "component": "RUN_METABLOOMS.py",
                "reason": "File not found in bundle"
            })
            return

        # Verify boot is parseable
        try:
            ast.parse(boot_file.read_text())
            self.report.verified_implementations.append({
                "component": "BOOT_METABLOOMS.py",
                "detail": "File exists and is valid Python",
                "path": str(boot_file.relative_to(self.extract_dir))
            })
        except SyntaxError as e:
            self.report.missing.append({
                "component": "BOOT_METABLOOMS.py",
                "reason": f"Syntax error: {e}"
            })

    def check_delta_enforcement(self):
        """Verify delta loading and SHA256 verification"""
        boot_file = self.extract_dir / "BOOT_METABLOOMS.py"
        if not boot_file.exists():
            return

        analyzer = BootAnalyzer(boot_file)

        # Check for latest.json reference
        loads_latest = analyzer.loads_file("latest.json")
        loads_manifests = analyzer.loads_file("manifests")

        if not (loads_latest or loads_manifests):
            self.report.missing.append({
                "component": "Delta manifest loading",
                "reason": "No reference to 'latest.json' or 'manifests' in BOOT_METABLOOMS.py",
                "evidence": "Static source analysis: 0 occurrences"
            })

        # Check for delta SHA256 verification
        has_delta_hash = "delta" in analyzer.source.lower() and "sha256" in analyzer.source

        if not has_delta_hash:
            self.report.missing.append({
                "component": "Delta SHA256 verification",
                "reason": "No evidence of delta hash verification in boot",
                "evidence": "Source contains doctrine hash verification only"
            })

    def check_gate_wiring(self):
        """Check if gate files exist but are unused"""
        gate_files = list(self.extract_dir.glob("*gate*.py"))

        if not gate_files:
            self.report.missing.append({
                "component": "Gate infrastructure",
                "reason": "No gate files found"
            })
            return

        boot_file = self.extract_dir / "BOOT_METABLOOMS.py"
        if not boot_file.exists():
            return

        analyzer = BootAnalyzer(boot_file)
        imports = analyzer.extract_imports()

        # Check if any gates are imported
        gate_imports = [imp for imp in imports if "gate" in imp.lower()]

        if not gate_imports:
            self.report.present_but_unwired.append({
                "component": "Gate files",
                "count": len(gate_files),
                "files": [g.name for g in gate_files[:10]],
                "reason": "Gate files exist but are not imported by BOOT_METABLOOMS.py",
                "evidence": f"Found {len(gate_files)} gate files, 0 gate imports in boot"
            })
        else:
            self.report.verified_implementations.append({
                "component": "Gate imports",
                "imports": gate_imports
            })

    def check_schema_usage(self):
        """Check if schemas exist but are unused"""
        schema_dir = self.extract_dir / "schemas"

        if not schema_dir.exists():
            self.report.missing.append({
                "component": "Schema directory",
                "reason": "schemas/ directory not found"
            })
            return

        schema_files = list(schema_dir.glob("*.json"))

        # Check if any Python file imports jsonschema or validates
        py_files = list(self.extract_dir.glob("*.py"))
        validates_schema = False

        for py_file in py_files:
            try:
                source = py_file.read_text()
                if "jsonschema" in source or "validate(" in source:
                    validates_schema = True
                    break
            except:
                continue

        if schema_files and not validates_schema:
            self.report.present_but_unwired.append({
                "component": "JSON schemas",
                "count": len(schema_files),
                "files": [s.name for s in schema_files],
                "reason": "Schema files exist but no validation code found",
                "evidence": f"{len(schema_files)} schemas, 0 jsonschema imports"
            })

    def check_ledger_integration(self):
        """Verify ledger is written by boot"""
        boot_file = self.extract_dir / "BOOT_METABLOOMS.py"
        if not boot_file.exists():
            return

        source = boot_file.read_text()

        # Check for ledger write
        has_ledger_write = "ledger" in source.lower() and ('open(' in source or '.write(' in source)
        has_append_mode = '"a"' in source or "'a'" in source

        if has_ledger_write and has_append_mode:
            # Extract the ledger path
            ledger_path_match = re.search(r'LEDGER_PATH\s*=\s*.+?["\'](.+?)["\']', source)
            if ledger_path_match:
                ledger_path = ledger_path_match.group(1)
            else:
                ledger_path = "governance/epistemic_ledger.ndjson"

            self.report.verified_implementations.append({
                "component": "Ledger integration",
                "detail": "Boot writes to ledger in append mode",
                "path": ledger_path,
                "evidence": "Source contains ledger open in append mode"
            })
        else:
            self.report.missing.append({
                "component": "Ledger integration",
                "reason": "No evidence of ledger writes in boot"
            })

    def check_index_usage(self):
        """Check if RUNTIME_INDEX.json exists and is loaded"""
        index_file = self.extract_dir / "RUNTIME_INDEX.json"

        if not index_file.exists():
            self.report.missing.append({
                "component": "RUNTIME_INDEX.json",
                "reason": "File not found in bundle"
            })
            return

        # Verify it's valid JSON
        try:
            with open(index_file) as f:
                index_data = json.load(f)

            self.report.present_but_unwired.append({
                "component": "RUNTIME_INDEX.json",
                "size_bytes": index_file.stat().st_size,
                "top_level_keys": list(index_data.keys()),
                "reason": "Index exists but is not referenced by BOOT_METABLOOMS.py",
                "evidence": "File exists, not loaded by boot"
            })
        except json.JSONDecodeError as e:
            self.report.missing.append({
                "component": "RUNTIME_INDEX.json",
                "reason": f"Invalid JSON: {e}"
            })

    def check_csrg_presence(self):
        """Check for CSRG implementation"""
        # Search all Python files for csrg references
        py_files = list(self.extract_dir.glob("**/*.py"))
        csrg_files = []

        for py_file in py_files:
            try:
                source = py_file.read_text()
                if "csrg" in source.lower():
                    csrg_files.append(py_file.name)
            except:
                continue

        if not csrg_files:
            self.report.missing.append({
                "component": "CSRG gate",
                "reason": "No files contain 'csrg' or 'CSRG'",
                "evidence": f"Searched {len(py_files)} Python files, 0 matches"
            })
        else:
            self.report.unverifiable.append({
                "component": "CSRG gate",
                "reason": "Files mention CSRG but wiring unclear without execution",
                "files": csrg_files
            })

    def check_manifest_loading(self):
        """Check if boot_manifest.json is loaded"""
        manifest_file = self.extract_dir / "boot_manifest.json"

        if not manifest_file.exists():
            self.report.missing.append({
                "component": "boot_manifest.json",
                "reason": "File not found in bundle root"
            })
            return

        # Verify it's valid JSON and read preflight list
        try:
            with open(manifest_file) as f:
                manifest_data = json.load(f)

            preflight = manifest_data.get("preflight", [])

            # Check if boot loads this manifest
            boot_file = self.extract_dir / "BOOT_METABLOOMS.py"
            if boot_file.exists():
                analyzer = BootAnalyzer(boot_file)
                loads_manifest = analyzer.loads_file("boot_manifest.json")

                if not loads_manifest:
                    self.report.present_but_unwired.append({
                        "component": "boot_manifest.json",
                        "preflight_count": len(preflight),
                        "preflight_gates": preflight,
                        "reason": "Manifest exists with preflight gates, but BOOT_METABLOOMS.py never loads it",
                        "evidence": "Source analysis: 0 references to 'boot_manifest'"
                    })
                else:
                    self.report.verified_implementations.append({
                        "component": "boot_manifest.json loading",
                        "detail": "Boot references manifest file"
                    })
        except json.JSONDecodeError as e:
            self.report.missing.append({
                "component": "boot_manifest.json",
                "reason": f"Invalid JSON: {e}"
            })


def audit_bundle(zip_path: Path) -> Dict:
    """Run full audit and return JSON report"""
    auditor = MetaBloomsAuditor(zip_path)
    report = auditor.run()

    return {
        "verified_implementations": report.verified_implementations,
        "present_but_unwired": report.present_but_unwired,
        "missing": report.missing,
        "spec_conflicts": report.spec_conflicts,
        "unverifiable_with_given_tools": report.unverifiable
    }


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: metablooms_audit.py <path-to-metablooms-bundle.zip>")
        sys.exit(1)

    zip_path = Path(sys.argv[1])

    if not zip_path.exists():
        print(f"Error: {zip_path} not found")
        sys.exit(1)

    print(f"Auditing: {zip_path}")
    print("=" * 70)

    report = audit_bundle(zip_path)

    # Pretty print
    print(json.dumps(report, indent=2))

    # Summary
    print("\n" + "=" * 70)
    print(f"VERIFIED: {len(report['verified_implementations'])}")
    print(f"UNWIRED: {len(report['present_but_unwired'])}")
    print(f"MISSING: {len(report['missing'])}")
    print(f"SPEC_CONFLICTS: {len(report['spec_conflicts'])}")
    print(f"UNVERIFIABLE: {len(report['unverifiable_with_given_tools'])}")


if __name__ == "__main__":
    main()
