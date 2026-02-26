# PowerShell 7 Competency Package

Production-grade PowerShell 7 (7.4/7.5-era) reference package for MetaBlooms.

## Contents

| Path | Purpose |
|------|---------|
| `competency-map.md` | Canonical pre-script checklist |
| `defect-prevention-playbook.md` | Defect class → prevention pattern mapping |
| `templates/script-template.ps1` | `.ps1` script skeleton |
| `templates/function-template.ps1` | Advanced function skeleton |
| `templates/module/Module.psd1` | Module manifest template |
| `templates/module/Module.psm1` | Module script template |
| `tests/Module.Tests.ps1` | Pester 5 test suite |
| `config/PSScriptAnalyzerSettings.psd1` | Static analysis ruleset |

## Quick Start

```powershell
# Run tests
Invoke-Pester ./tests/

# Run static analysis
Invoke-ScriptAnalyzer -Path . -Recurse -Settings ./config/PSScriptAnalyzerSettings.psd1
```

## Contract

All scripts in this package are:

- PS 7.4+ compatible
- `StrictMode` pinned to `3.0`
- Free of `array +=` anti-patterns
- Validated at the parameter level
- Structured-output only (no `Format-*` in functions)
- Covered by Pester 5 tests
- PSScriptAnalyzer-compliant at Warning+Error severity

## Platform Support

- Windows 10/11
- Linux (glibc-based)
- macOS
