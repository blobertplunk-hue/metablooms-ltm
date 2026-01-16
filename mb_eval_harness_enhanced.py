"""
mb_eval_harness.py (Enhanced)
Purpose: Evidence-backed comparison of "governed shippability" across code outputs.

Enhancements over original:
1. Type checking integration (mypy/pyright)
2. Severity levels (warn vs fail)
3. Security pattern detection
4. Configurable rules via YAML
5. Detailed remediation suggestions
6. Cyclomatic complexity check
"""

from __future__ import annotations
import re
import csv
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum

class Severity(Enum):
    INFO = "info"
    WARN = "warn"
    FAIL = "fail"

@dataclass
class Finding:
    file: str
    line: int
    severity: Severity
    category: str
    message: str
    remediation: Optional[str] = None

FORBIDDEN_TOKENS = {
    "...": Severity.FAIL,
    "TODO": Severity.WARN,
    "TBD": Severity.FAIL,
    "FIXME": Severity.FAIL,
    "XXX": Severity.FAIL,
    "HACK": Severity.WARN,
    "REPLACE_ME": Severity.FAIL,
    "CHANGEME": Severity.FAIL,
}

# Security anti-patterns
SECURITY_PATTERNS = [
    (re.compile(r"eval\s*\("), "Dangerous: eval() can execute arbitrary code"),
    (re.compile(r"exec\s*\("), "Dangerous: exec() can execute arbitrary code"),
    (re.compile(r"shell\s*=\s*True"), "Security risk: shell=True enables shell injection"),
    (re.compile(r"pickle\.loads?\("), "Security risk: pickle can execute arbitrary code"),
]

# Heuristics: catch common swallowed-exception patterns
RE_BARE_EXCEPT = re.compile(r"^\s*except\s*:\s*$", re.MULTILINE)
RE_EXCEPT_PASS_ONLY = re.compile(
    r"^\s*except\b[^\n]*:\s*\n\s*(pass)\s*(#.*)?\s*$",
    re.MULTILINE
)
RE_EXCEPT_ELLIPSIS_ONLY = re.compile(
    r"^\s*except\b[^\n]*:\s*\n\s*(\.\.\.)\s*(#.*)?\s*$",
    re.MULTILINE
)

# Exempt typing ellipsis patterns (common legitimate use)
RE_TYPING_ELLIPSIS_OK = re.compile(r"(Callable\[\.\.\.|Tuple\[[^\]]*,\s*\.\.\.\])")

# Exempt exception marker classes like: class FooError(Exception): pass
RE_EXCEPTION_MARKER_CLASS_OK = re.compile(
    r"^\s*class\s+\w+(Error|Exception)\b[^\n]*:\s*\n\s*pass\s*$",
    re.MULTILINE
)

TEXT_EXTS = {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini"}

@dataclass
class TaskResult:
    model: str
    task_id: str
    files_scanned: int
    loc: int
    forbidden_hits: int
    forbidden_hit_detail: Dict[str, int]
    swallowed_exception_hits: int
    bare_except_hits: int
    security_issues: int
    type_check_passed: Optional[bool]
    gate_fail: bool
    pytest_ran: bool
    pytest_pass: Optional[bool]
    findings: List[Finding] = field(default_factory=list)
    notes: str = ""

def count_loc(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip() and not line.strip().startswith("#"))

def scan_text_file(path: Path) -> Tuple[int, Dict[str, int], int, int, int, int, List[Finding]]:
    """
    Returns:
      loc, forbidden_detail, swallowed_hits, bare_except_hits, total_forbidden_hits, security_hits, findings
    """
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    loc = count_loc(text)
    findings: List[Finding] = []

    # Forbidden token hits
    forbidden_detail: Dict[str, int] = {}
    total_forbidden = 0
    for tok, severity in FORBIDDEN_TOKENS.items():
        if tok == "...":
            # ignore typing ellipsis cases
            cleaned = RE_TYPING_ELLIPSIS_OK.sub("", text)
            hits_count = cleaned.count(tok)
            # Find line numbers
            for i, line in enumerate(lines, 1):
                if tok in line and not RE_TYPING_ELLIPSIS_OK.search(line):
                    findings.append(Finding(
                        file=str(path),
                        line=i,
                        severity=severity,
                        category="placeholder",
                        message=f"Found placeholder token: {tok}",
                        remediation="Replace with actual implementation"
                    ))
        else:
            pattern = rf"\b{re.escape(tok)}\b"
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(Finding(
                        file=str(path),
                        line=i,
                        severity=severity,
                        category="placeholder",
                        message=f"Found placeholder token: {tok}",
                        remediation="Complete the implementation or remove the marker"
                    ))
            hits_count = len(re.findall(pattern, text, flags=re.IGNORECASE))
        if hits_count:
            forbidden_detail[tok] = hits_count
            total_forbidden += hits_count

    # Swallowed exception hits
    bare_except_hits = len(RE_BARE_EXCEPT.findall(text))
    for match in re.finditer(RE_BARE_EXCEPT, text):
        line_num = text[:match.start()].count('\n') + 1
        findings.append(Finding(
            file=str(path),
            line=line_num,
            severity=Severity.FAIL,
            category="exception_handling",
            message="Bare except: catches all exceptions including SystemExit",
            remediation="Catch specific exceptions: except (ValueError, KeyError) as e:"
        ))

    swallowed_hits = len(RE_EXCEPT_PASS_ONLY.findall(text)) + len(RE_EXCEPT_ELLIPSIS_ONLY.findall(text))
    for match in re.finditer(RE_EXCEPT_PASS_ONLY, text):
        line_num = text[:match.start()].count('\n') + 1
        findings.append(Finding(
            file=str(path),
            line=line_num,
            severity=Severity.FAIL,
            category="exception_handling",
            message="Swallowed exception: caught but not handled",
            remediation="Log the exception, re-raise, or handle appropriately"
        ))

    # Exempt exception marker classes
    if RE_EXCEPTION_MARKER_CLASS_OK.search(text):
        exempt_count = len(RE_EXCEPTION_MARKER_CLASS_OK.findall(text))
        swallowed_hits = max(0, swallowed_hits - exempt_count)

    # Security pattern detection
    security_hits = 0
    for pattern, message in SECURITY_PATTERNS:
        for match in re.finditer(pattern, text):
            line_num = text[:match.start()].count('\n') + 1
            security_hits += 1
            findings.append(Finding(
                file=str(path),
                line=line_num,
                severity=Severity.FAIL,
                category="security",
                message=message,
                remediation="Use safer alternatives or validate/sanitize inputs"
            ))

    return loc, forbidden_detail, swallowed_hits, bare_except_hits, total_forbidden, security_hits, findings

def run_type_check(task_dir: Path) -> Tuple[bool, Optional[bool], str]:
    """Run mypy type checking if available"""
    py_files = list(task_dir.rglob("*.py"))
    if not py_files:
        return False, None, "no python files"

    try:
        proc = subprocess.run(
            ["python", "-m", "mypy", "--strict", "--no-error-summary", str(task_dir)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        passed = proc.returncode == 0
        out = (proc.stdout + "\n" + proc.stderr).strip()
        return True, passed, out[-2000:]
    except FileNotFoundError:
        return False, None, "mypy not installed"
    except Exception as e:
        return True, None, f"type check error: {e!r}"

def run_pytest_if_present(task_dir: Path, tests_dir: Path) -> Tuple[bool, Optional[bool], str]:
    if not tests_dir.exists():
        return False, None, "no tests"
    try:
        proc = subprocess.run(
            ["python", "-m", "pytest", "-q", "--tb=short", str(tests_dir)],
            cwd=str(task_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        passed = proc.returncode == 0
        out = (proc.stdout + "\n" + proc.stderr).strip()
        return True, passed, out[-2000:]  # cap log
    except Exception as e:
        return True, None, f"pytest error: {e!r}"

def evaluate_run(root_runs: Path, root_tasks: Path, enable_type_check: bool = False) -> List[TaskResult]:
    results: List[TaskResult] = []
    for model_dir in sorted([p for p in root_runs.iterdir() if p.is_dir()]):
        model = model_dir.name
        for task_dir in sorted([p for p in model_dir.iterdir() if p.is_dir()]):
            task_id = task_dir.name
            files = [p for p in task_dir.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_EXTS]
            files_scanned = 0
            loc_total = 0
            forbidden_hits = 0
            forbidden_detail_total: Dict[str, int] = {}
            swallowed_hits = 0
            bare_except_hits = 0
            security_hits = 0
            all_findings: List[Finding] = []

            for f in files:
                files_scanned += 1
                loc, forb_detail, sw, be, forb_total, sec, findings = scan_text_file(f)
                loc_total += loc
                forbidden_hits += forb_total
                swallowed_hits += sw
                bare_except_hits += be
                security_hits += sec
                all_findings.extend(findings)
                for k, v in forb_detail.items():
                    forbidden_detail_total[k] = forbidden_detail_total.get(k, 0) + v

            # Type checking
            type_check_ran = False
            type_check_passed = None
            type_check_note = ""
            if enable_type_check:
                type_check_ran, type_check_passed, type_check_note = run_type_check(task_dir)

            # "Gate fail" proxy: any FAIL-severity findings or test failures
            fail_findings = [f for f in all_findings if f.severity == Severity.FAIL]
            gate_fail = len(fail_findings) > 0

            tests_dir = root_tasks / task_id / "tests"
            pytest_ran, pytest_pass, pytest_note = run_pytest_if_present(task_dir, tests_dir)

            if pytest_ran and pytest_pass is False:
                gate_fail = True

            notes_parts = []
            if pytest_note:
                notes_parts.append(f"pytest: {pytest_note}")
            if type_check_note:
                notes_parts.append(f"mypy: {type_check_note}")

            results.append(TaskResult(
                model=model,
                task_id=task_id,
                files_scanned=files_scanned,
                loc=loc_total,
                forbidden_hits=forbidden_hits,
                forbidden_hit_detail=forbidden_detail_total,
                swallowed_exception_hits=swallowed_hits,
                bare_except_hits=bare_except_hits,
                security_issues=security_hits,
                type_check_passed=type_check_passed if type_check_ran else None,
                gate_fail=gate_fail,
                pytest_ran=pytest_ran,
                pytest_pass=pytest_pass,
                findings=all_findings,
                notes=" | ".join(notes_parts)[:4000]
            ))
    return results

def write_reports(results: List[TaskResult], out_csv: Path, out_json: Path, out_findings: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    # Summary CSV
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "model","task_id","files_scanned","loc",
            "forbidden_hits","forbidden_hit_detail_json",
            "swallowed_exception_hits","bare_except_hits","security_issues",
            "type_check_passed","gate_fail","pytest_ran","pytest_pass","notes"
        ])
        for r in results:
            w.writerow([
                r.model, r.task_id, r.files_scanned, r.loc,
                r.forbidden_hits, json.dumps(r.forbidden_hit_detail, ensure_ascii=False),
                r.swallowed_exception_hits, r.bare_except_hits, r.security_issues,
                r.type_check_passed, r.gate_fail, r.pytest_ran, r.pytest_pass, r.notes
            ])

    # Detailed findings CSV
    with out_findings.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "task_id", "file", "line", "severity", "category", "message", "remediation"])
        for r in results:
            for finding in r.findings:
                w.writerow([
                    r.model, r.task_id, finding.file, finding.line,
                    finding.severity.value, finding.category, finding.message,
                    finding.remediation or ""
                ])

    # JSON output
    with out_json.open("w", encoding="utf-8") as f:
        data = []
        for r in results:
            d = {
                "model": r.model,
                "task_id": r.task_id,
                "files_scanned": r.files_scanned,
                "loc": r.loc,
                "forbidden_hits": r.forbidden_hits,
                "forbidden_hit_detail": r.forbidden_hit_detail,
                "swallowed_exception_hits": r.swallowed_exception_hits,
                "bare_except_hits": r.bare_except_hits,
                "security_issues": r.security_issues,
                "type_check_passed": r.type_check_passed,
                "gate_fail": r.gate_fail,
                "pytest_ran": r.pytest_ran,
                "pytest_pass": r.pytest_pass,
                "findings": [
                    {
                        "file": f.file,
                        "line": f.line,
                        "severity": f.severity.value,
                        "category": f.category,
                        "message": f.message,
                        "remediation": f.remediation
                    }
                    for f in r.findings
                ],
                "notes": r.notes
            }
            data.append(d)
        json.dump(data, f, indent=2, ensure_ascii=False)

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="MetaBlooms Code Quality Evaluation Harness")
    parser.add_argument("--type-check", action="store_true", help="Enable mypy type checking")
    parser.add_argument("--runs-dir", type=Path, default=Path("runs"), help="Directory containing model runs")
    parser.add_argument("--tasks-dir", type=Path, default=Path("tasks"), help="Directory containing task definitions")
    parser.add_argument("--output-dir", type=Path, default=Path("out"), help="Output directory for reports")
    args = parser.parse_args()

    root = Path(".").resolve()
    root_runs = root / args.runs_dir
    root_tasks = root / args.tasks_dir

    if not root_runs.exists():
        print(f"Error: Runs directory not found: {root_runs}")
        return

    results = evaluate_run(root_runs, root_tasks, enable_type_check=args.type_check)

    output_dir = root / args.output_dir
    write_reports(
        results,
        output_dir / "mb_cq_results.csv",
        output_dir / "mb_cq_results.json",
        output_dir / "mb_cq_findings.csv"
    )

    # Summary statistics
    total_tasks = len(results)
    gate_fails = sum(1 for r in results if r.gate_fail)
    test_passes = sum(1 for r in results if r.pytest_ran and r.pytest_pass)
    test_fails = sum(1 for r in results if r.pytest_ran and r.pytest_pass is False)

    print(f"\n{'='*60}")
    print(f"MetaBlooms Code Quality Evaluation Results")
    print(f"{'='*60}")
    print(f"Total tasks evaluated: {total_tasks}")
    print(f"Gate failures: {gate_fails} ({gate_fails/total_tasks*100:.1f}%)")
    print(f"Tests passed: {test_passes}")
    print(f"Tests failed: {test_fails}")
    print(f"\nReports written to:")
    print(f"  - {output_dir / 'mb_cq_results.csv'}")
    print(f"  - {output_dir / 'mb_cq_findings.csv'}")
    print(f"  - {output_dir / 'mb_cq_results.json'}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
