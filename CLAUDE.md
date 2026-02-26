# CLAUDE.md — MetaBlooms LTM

Claude Code reads this file at the start of every session.
All rules below are **mandatory**, not advisory.

---

## PowerShell Code Generation — MANDATORY PROTOCOL

**Trigger:** Any time you write, edit, or review a `.ps1`, `.psm1`, or `.psd1` file.

### Step 1 — Before writing a single line of PS code

Read these files in order:

1. `powershell/competency-map.md`
2. `powershell/defect-prevention-playbook.md`

Do not skip this step even for small edits or one-liners.

### Step 2 — Required headers on every script and module

Every `.ps1` file must open with:

```powershell
#Requires -Version 7.4
Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'
```

Every `.psm1` file must open with:

```powershell
Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'
```

If these headers are absent from existing code you are editing, add them.

### Step 3 — Non-negotiable rules (apply to every function and script)

| Rule | Forbidden | Required |
|------|-----------|----------|
| Accumulation | `$arr += $item` | `[List[T]]::new()` + `.Add()` |
| Terminating errors | `Write-Error` for fatal failures | `$PSCmdlet.ThrowTerminatingError()` |
| Output | String literals to output stream | `[pscustomobject]@{...}` |
| Formatting | `Format-Table`, `Format-List` inside functions | Return objects; let caller format |
| Paths | String concatenation (`"$root\file"`) | `Join-Path $root 'file'` |
| Injection | `Invoke-Expression` | Never. Use `& $cmd @args` |
| StrictMode | `Set-StrictMode -Version Latest` | `Set-StrictMode -Version 3.0` |
| Module exports | `FunctionsToExport = '*'` | Explicit list |
| Validation | Runtime `if` guards on parameters | `[ValidateSet()]`, `[ValidatePattern()]` |
| Functions | Bare functions | `[CmdletBinding()]` always |

### Step 4 — Use the templates as starting points

| Task | Template to copy |
|------|-----------------|
| New script | `powershell/templates/script-template.ps1` |
| New function | `powershell/templates/function-template.ps1` |
| New module | `powershell/templates/module/Module.psm1` + `Module.psd1` |

Run to generate from template:
```powershell
pwsh powershell/scripts/New-PSScript.ps1 -Name MyScript -OutputPath ./scripts/
```

### Step 5 — Tests

Every non-trivial function or script must have a companion Pester 5 test file.
Reference: `powershell/tests/Module.Tests.ps1`.

### Step 6 — Self-verify before outputting

Before finalising any PS code output, mentally run through this checklist:

- [ ] `#Requires -Version 7.4` present (scripts)
- [ ] `Set-StrictMode -Version 3.0` present
- [ ] `$ErrorActionPreference = 'Stop'` present
- [ ] `[CmdletBinding()]` on every function
- [ ] No `+=` inside any loop
- [ ] No `Write-Error` for conditions that must stop execution
- [ ] No string emission to output stream
- [ ] No `Format-*` inside any function
- [ ] All paths use `Join-Path`
- [ ] No `Invoke-Expression`
- [ ] Parameter validation at parameter level, not in `process {}`
- [ ] Pester test file exists or updated

**If any box is unchecked, fix it before outputting.**

### Step 7 — After writing PS code

Run the compliance checker:

```powershell
pwsh powershell/scripts/Invoke-PSCompliance.ps1 -Path <file or directory>
```

Fix every finding before committing. The pre-commit hook and CI will also catch violations.

---

## Repository rules

- `ledger/ledger.ndjson` is append-only. Never modify existing lines.
- Hashes in ledger entries must be computed from the canonical JSON of the event object.
- `manifests/latest.json` updates require a corresponding ledger entry.
- Branch naming: `claude/<description>-<session-id>`.
