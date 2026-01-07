#!/usr/bin/env python3
"""
Boot Capability Surface Extractor

Analyzes BOOT_METABLOOMS.py WITHOUT executing it.
Extracts: file reads, imports, path references, function calls.
"""

import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Set


class BootCapabilityExtractor:
    """AST-based static analysis of boot file"""

    def __init__(self, boot_source: str):
        self.source = boot_source
        try:
            self.tree = ast.parse(boot_source)
        except SyntaxError as e:
            self.tree = None
            self.error = str(e)

    def extract_all(self) -> Dict:
        """Extract complete capability surface"""
        if not self.tree:
            return {"error": getattr(self, 'error', 'Unknown parse error')}

        return {
            "file_reads": self.extract_file_reads(),
            "imports": self.extract_imports(),
            "path_constants": self.extract_path_constants(),
            "function_definitions": self.extract_function_defs(),
            "external_calls": self.extract_external_calls(),
            "string_literals": self.extract_string_literals(),
            "fail_exit_codes": self.extract_exit_codes()
        }

    def extract_file_reads(self) -> List[Dict]:
        """Find all file read operations"""
        reads = []

        for node in ast.walk(self.tree):
            # Pattern: Path.read_text()
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ('read_text', 'read_bytes', 'open'):
                        # Try to get the path
                        if isinstance(node.func.value, ast.Name):
                            reads.append({
                                "operation": node.func.attr,
                                "variable": node.func.value.id,
                                "line": node.lineno
                            })

            # Pattern: open(path)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'open':
                    if node.args:
                        reads.append({
                            "operation": "open",
                            "argument": ast.unparse(node.args[0]) if hasattr(ast, 'unparse') else "unparseable",
                            "line": node.lineno
                        })

        return reads

    def extract_imports(self) -> List[str]:
        """Extract all imports"""
        imports = []

        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                imports.extend([alias.name for alias in node.names])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        return sorted(set(imports))

    def extract_path_constants(self) -> Dict[str, str]:
        """Find all path variable assignments"""
        paths = {}

        # Look for uppercase variables assigned to paths
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id.isupper() and 'PATH' in target.id or 'DIR' in target.id:
                            try:
                                value = ast.unparse(node.value) if hasattr(ast, 'unparse') else repr(node.value)
                                paths[target.id] = value
                            except:
                                paths[target.id] = "<unparseable>"

        return paths

    def extract_function_defs(self) -> List[Dict]:
        """Extract all function definitions"""
        functions = []

        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                # Extract parameters
                params = [arg.arg for arg in node.args.args]

                # Check for _die calls (fail-closed exits)
                has_die = False
                for subnode in ast.walk(node):
                    if isinstance(subnode, ast.Call):
                        if isinstance(subnode.func, ast.Name) and subnode.func.id == '_die':
                            has_die = True
                            break

                functions.append({
                    "name": node.name,
                    "params": params,
                    "line": node.lineno,
                    "has_fail_closed": has_die
                })

        return functions

    def extract_external_calls(self) -> List[Dict]:
        """Find calls to functions not defined in this file"""
        defined = {f['name'] for f in self.extract_function_defs()}
        stdlib = {'print', 'open', 'len', 'sorted', 'list', 'dict', 'set', 'str', 'int', 'float', 'isinstance', 'hasattr', 'getattr'}

        external = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name not in defined and func_name not in stdlib:
                        external.append({
                            "function": func_name,
                            "line": node.lineno
                        })

        # Deduplicate
        seen = set()
        unique = []
        for call in external:
            key = (call['function'], call['line'])
            if key not in seen:
                seen.add(key)
                unique.append(call)

        return unique

    def extract_string_literals(self) -> Set[str]:
        """Extract all string constants (to find filename references)"""
        strings = set()

        for node in ast.walk(self.tree):
            if isinstance(node, ast.Constant):
                if isinstance(node.value, str):
                    strings.add(node.value)

        return sorted(strings)

    def extract_exit_codes(self) -> Dict[int, str]:
        """Find all _die() calls and their exit codes"""
        exits = {}

        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == '_die':
                    if len(node.args) >= 2:
                        # First arg is exit code
                        if isinstance(node.args[0], ast.Constant):
                            code = node.args[0].value
                            # Second arg is message
                            if isinstance(node.args[1], ast.Constant):
                                msg = node.args[1].value
                            elif isinstance(node.args[1], ast.JoinedStr):
                                # f-string
                                msg = "<f-string>"
                            else:
                                msg = "<dynamic>"
                            exits[code] = msg

        return exits


def analyze_boot_file(boot_path: Path) -> Dict:
    """Main entry point"""
    source = boot_path.read_text()
    extractor = BootCapabilityExtractor(source)
    return extractor.extract_all()


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: boot_capability_probe.py <BOOT_METABLOOMS.py>")
        sys.exit(1)

    boot_path = Path(sys.argv[1])

    if not boot_path.exists():
        print(f"Error: {boot_path} not found")
        sys.exit(1)

    capabilities = analyze_boot_file(boot_path)

    print(json.dumps(capabilities, indent=2, default=str))


if __name__ == "__main__":
    main()
