# Defect Prevention Playbook — PS7

Each rule maps to a known, recurring defect class.

---

## Rule 1 — Avoid Array `+=` in Loops

**Defect class:** O(n²) memory growth; performance collapse at scale

**Why it fails:** PowerShell arrays (`[object[]]`) are fixed-size. `+=` allocates a new array, copies all existing elements, then appends — every iteration.

**Bad**

```powershell
$items = @()
foreach ($i in 1..10000) {
    $items += $i          # Full copy on every iteration
}
```

**Good**

```powershell
$list = [System.Collections.Generic.List[int]]::new()
foreach ($i in 1..10000) {
    $list.Add($i)         # O(1) amortised append
}
$items = $list.ToArray()  # One allocation at the end
```

**Alternative (streaming):** emit objects inside `process {}` and let the pipeline collect them — no buffering required.

---

## Rule 2 — Terminating vs Non-Terminating Errors

**Defect class:** Silent continuation after critical failure

**Why it fails:** `Write-Error` emits a non-terminating error. Execution continues. Callers that do not inspect `$?` or `$Error` never know the operation failed.

**Bad**

```powershell
Write-Error "Critical failure"
# Execution continues here
```

**Good — in an advanced function**

```powershell
$record = [System.Management.Automation.ErrorRecord]::new(
    [Exception]::new("Critical failure"),
    "CriticalFailure",
    [System.Management.Automation.ErrorCategory]::InvalidOperation,
    $TargetObject
)
$PSCmdlet.ThrowTerminatingError($record)
```

**Good — in a simple script**

```powershell
throw "Critical failure"   # Or set $ErrorActionPreference = 'Stop' at top
```

---

## Rule 3 — Avoid Stringly-Typed Output

**Defect class:** Pipeline breakage; downstream consumers cannot filter or select properties

**Bad**

```powershell
"User count: $count"        # String emitted to output stream
```

**Good**

```powershell
[pscustomobject]@{
    UserCount = $count
}
```

Callers can then do: `Get-UserStats | Where-Object UserCount -gt 100`

---

## Rule 4 — No `Format-*` Inside Functions

**Defect class:** Downstream pipeline corruption — `Format-*` emits formatting objects, not data objects

**Bad**

```powershell
function Get-ProcessInfo {
    Get-Process | Format-Table Name, CPU    # Destroys downstream use
}
```

**Good**

```powershell
function Get-ProcessInfo {
    Get-Process | Select-Object Name, CPU   # Returns data objects
}
# Caller decides how to display:
Get-ProcessInfo | Format-Table
Get-ProcessInfo | Export-Csv results.csv
```

---

## Rule 5 — Pin `StrictMode` to a Version

**Defect class:** Silent breakage when PowerShell introduces new strict checks under `Latest`

**Bad**

```powershell
Set-StrictMode -Version Latest   # Behaviour can change with PS upgrades
```

**Good**

```powershell
Set-StrictMode -Version 3.0      # Pinned; predictable across PS releases
```

---

## Rule 6 — Parameter-Level Validation

**Defect class:** Late runtime validation failures with poor error messages

**Bad**

```powershell
param([string]$Priority)
process {
    if ($Priority -notin 'Low','Medium','High') {
        throw "Invalid priority"    # Late, generic message
    }
}
```

**Good**

```powershell
param(
    [Parameter(Mandatory)]
    [ValidateSet('Low', 'Medium', 'High')]
    [string]$Priority
)
# PowerShell rejects invalid values before process{} runs, with a clear message
```

---

## Rule 7 — Cross-Platform Path Construction

**Defect class:** Windows/Linux path separator incompatibility

**Bad**

```powershell
$path = "$Root\subdir\file.txt"    # Backslash breaks on Linux/macOS
```

**Good**

```powershell
$path = Join-Path $Root 'subdir' 'file.txt'    # Works on all platforms
```

---

## Rule 8 — Avoid `Invoke-Expression`

**Defect class:** Command injection; arbitrary code execution

**Bad**

```powershell
Invoke-Expression "git $UserInput"     # Injection vector
```

**Good**

```powershell
& git $SafeArguments                   # Array form; no shell interpolation
# Or:
Start-Process git -ArgumentList $SafeArguments -Wait
```

---

## Rule 9 — Wrap External Commands with Error Handling

**Defect class:** External command failure silently ignored

**Bad**

```powershell
git push origin main    # Non-zero exit ignored unless $ErrorActionPreference = 'Stop'
```

**Good**

```powershell
$result = & git push origin main 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "git push failed (exit $LASTEXITCODE): $result"
}
```

---

## Rule 10 — Explicit Module Exports

**Defect class:** Accidental exposure of internal helpers; unstable public surface

**Bad**

```powershell
# Module.psd1
FunctionsToExport = '*'    # All functions exported, including internal ones
```

**Good**

```powershell
# Module.psd1
FunctionsToExport = @('Get-ItemSafe', 'Invoke-SafeOperation')
```
