# PS7 Competency Map

Canonical pre-script checklist for PowerShell 7.4+.

---

## 1. Execution Model & Strictness

- [ ] Pin `Set-StrictMode` to a deliberate version — avoid `Latest` (future PS releases may add new checks that break scripts silently)
- [ ] Define `$ErrorActionPreference` explicitly at script/module top
- [ ] Avoid implicit output; emit structured objects only
- [ ] Use UTF-8 encoding explicitly for file I/O (PS7 default is UTF-8 without BOM; PS5.1 default differs)

## 2. Advanced Function Design

- [ ] Decorate every non-trivial function with `[CmdletBinding()]`
- [ ] Declare pipeline behavior: `ValueFromPipeline`, `ValueFromPipelineByPropertyName`
- [ ] Define `ParameterSetName` where two or more parameter combinations are mutually exclusive
- [ ] Common parameters (`-Verbose`, `-ErrorAction`, `-WhatIf`, etc.) are added automatically by `CmdletBinding`

## 3. Input Validation

- [ ] Use `[ValidateSet()]` when the domain is a closed, enumerable set
- [ ] Use `[ValidatePattern()]` for regex-constrained strings
- [ ] Use `[ValidateScript()]` only when the other validators are insufficient (it runs for every bound value; keep predicates cheap)
- [ ] Prefer parameter-level validation over `if` guards in `process {}` — errors surface earlier with better messages

## 4. Error Model

- [ ] Distinguish terminating errors (stop execution) from non-terminating errors (logged, execution continues)
- [ ] Use `$PSCmdlet.ThrowTerminatingError()` in advanced functions — it records the correct invocation position
- [ ] Build a structured `[System.Management.Automation.ErrorRecord]` when rethrowing to preserve category and target
- [ ] Wrap every external command (`git`, `dotnet`, etc.) in `try/catch` when failures must be terminating

## 5. Pipeline & Object Correctness

- [ ] Emit consistent object shapes per function — never mix types in the same pipeline output stream
- [ ] Route human-readable text through `Write-Verbose` / `Write-Information`, not the output stream
- [ ] Never place `Format-Table`, `Format-List`, or `Out-*` inside a reusable function

## 6. Cross-Platform Readiness

- [ ] Build all paths with `Join-Path` or `[System.IO.Path]::Combine()`, not string concatenation
- [ ] Gate Windows-only APIs (`registry`, `COM`, `WMI`) behind `$IsWindows`
- [ ] Never assume `cmd.exe`, batch extensions, or drive letters
- [ ] Use `#!/usr/bin/env pwsh` shebang on Unix scripts

## 7. Performance Safety

- [ ] Never append to arrays with `+=` inside loops — each iteration copies the entire array (O(n²))
- [ ] Accumulate into `[System.Collections.Generic.List[T]]` and call `.ToArray()` once at the end
- [ ] Prefer streaming (emit objects inside `process {}`) over buffering the entire result set

## 8. Security Baseline

- [ ] Avoid `Invoke-Expression` — use proper PowerShell syntax or `Start-Process` with explicit argument lists
- [ ] Validate all external/user-supplied input before constructing command arguments
- [ ] Write code that remains correct under Constrained Language Mode (no type method calls on untrusted types)

## 9. Tooling

- [ ] Every non-trivial script or module has a companion Pester 5 test file
- [ ] `PSScriptAnalyzer` is run with the project's custom ruleset before merge

## 10. Module Hygiene

- [ ] `FunctionsToExport` listed explicitly in `.psd1` (never `'*'` in production)
- [ ] `ModuleVersion` follows semantic versioning (`MAJOR.MINOR.PATCH`)
- [ ] Every exported function has comment-based help (`.SYNOPSIS`, `.PARAMETER`, `.EXAMPLE`)
