#Requires -Version 7.4
<#
.SYNOPSIS
    Runs the full PS7 compliance check against one or more PowerShell files.

.DESCRIPTION
    Combines two checks:
      1. Header audit  — verifies required directives are present.
      2. PSScriptAnalyzer — runs with the project ruleset.

    Exits with code 0 on full compliance, 1 on any finding.
    Designed to be called by the pre-commit hook and CI, and manually during development.

.PARAMETER Path
    File or directory to check. Directories are searched recursively for *.ps1, *.psm1.
    Excludes *.psd1 from header audit (manifests have different structure) but still
    runs PSSA on them.

.PARAMETER Fix
    Attempt to auto-fix PSSA findings where the analyser supports it.
    Does NOT fix header violations — those must be corrected manually.

.PARAMETER Severity
    PSSA severity filter. Default: Warning,Error.

.EXAMPLE
    PS> ./powershell/scripts/Invoke-PSCompliance.ps1 -Path ./powershell/

.EXAMPLE
    PS> ./powershell/scripts/Invoke-PSCompliance.ps1 -Path ./scripts/Deploy.ps1

.EXAMPLE
    PS> ./powershell/scripts/Invoke-PSCompliance.ps1 -Path . -Severity Error
#>

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

[CmdletBinding()]
param(
    [Parameter(Mandatory, Position = 0)]
    [ValidateNotNullOrEmpty()]
    [string]$Path,

    [switch]$Fix,

    [ValidateSet('Information', 'Warning', 'Error')]
    [string[]]$Severity = @('Warning', 'Error')
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

$SettingsFile  = Join-Path $PSScriptRoot '..' 'config' 'PSScriptAnalyzerSettings.psd1'
$ScriptHeaders = @(
    '#Requires -Version 7',
    'Set-StrictMode',
    '$ErrorActionPreference'
)
$ModuleHeaders = @(
    'Set-StrictMode',
    '$ErrorActionPreference'
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Finding {
    param(
        [string]$File,
        [string]$Severity,
        [string]$Rule,
        [string]$Message,
        [int]$Line = 0
    )

    $lineInfo = if ($Line -gt 0) { ":$Line" } else { '' }
    $label    = $Severity.ToUpper().PadRight(7)

    Write-Host "[$label] $File$lineInfo — $Rule" -ForegroundColor $(
        switch ($Severity) {
            'Error'       { 'Red'    }
            'Warning'     { 'Yellow' }
            default       { 'Cyan'   }
        }
    )
    Write-Host "         $Message"
}

function Test-RequiredHeaders {
    param(
        [string]$FilePath,
        [string[]]$RequiredPrefixes
    )

    $content = Get-Content -LiteralPath $FilePath -Encoding UTF8 -ErrorAction Stop
    # Only inspect the first 20 lines — headers must be at the top.
    $head    = $content | Select-Object -First 20

    $findings = [System.Collections.Generic.List[pscustomobject]]::new()

    foreach ($prefix in $RequiredPrefixes) {
        $found = $head | Where-Object { $_.TrimStart().StartsWith($prefix) }
        if (-not $found) {
            $findings.Add([pscustomobject]@{
                File     = $FilePath
                Severity = 'Error'
                Rule     = 'RequiredHeader'
                Message  = "Missing required header: '$prefix'"
                Line     = 0
            })
        }
    }

    $findings
}

# ---------------------------------------------------------------------------
# Resolve files
# ---------------------------------------------------------------------------

$resolvedPath = [System.IO.Path]::GetFullPath($Path)

if (Test-Path -LiteralPath $resolvedPath -PathType Container) {
    $psFiles = Get-ChildItem -LiteralPath $resolvedPath -Recurse -Include '*.ps1', '*.psm1', '*.psd1' |
               Where-Object { $_.FullName -notmatch '[\\/]\.git[\\/]' }
}
elseif (Test-Path -LiteralPath $resolvedPath -PathType Leaf) {
    $psFiles = @(Get-Item -LiteralPath $resolvedPath)
}
else {
    Write-Error "Path not found: $resolvedPath"
    exit 1
}

if ($psFiles.Count -eq 0) {
    Write-Host "No PowerShell files found at: $resolvedPath" -ForegroundColor Yellow
    exit 0
}

Write-Host "`nPS7 Compliance Check — $($psFiles.Count) file(s)" -ForegroundColor Cyan
Write-Host "Settings: $SettingsFile`n"

# ---------------------------------------------------------------------------
# Check 1: Required headers
# ---------------------------------------------------------------------------

$allFindings = [System.Collections.Generic.List[pscustomobject]]::new()

foreach ($file in $psFiles) {
    $ext = $file.Extension.ToLower()

    if ($ext -eq '.psd1') { continue }   # Manifests: skip header audit

    $requiredPrefixes = if ($ext -eq '.psm1') { $ModuleHeaders } else { $ScriptHeaders }

    $headerFindings = Test-RequiredHeaders -FilePath $file.FullName -RequiredPrefixes $requiredPrefixes
    foreach ($f in $headerFindings) { $allFindings.Add($f) }
}

# ---------------------------------------------------------------------------
# Check 2: PSScriptAnalyzer
# ---------------------------------------------------------------------------

if (-not (Get-Module -ListAvailable -Name PSScriptAnalyzer)) {
    Write-Warning "PSScriptAnalyzer not installed. Skipping static analysis."
    Write-Warning "Install with: Install-Module PSScriptAnalyzer -Force"
}
else {
    $pssaParams = @{
        Path      = $resolvedPath
        Recurse   = (Test-Path -LiteralPath $resolvedPath -PathType Container)
        Severity  = $Severity
        ErrorAction = 'Stop'
    }

    if (Test-Path -LiteralPath $SettingsFile) {
        $pssaParams['Settings'] = $SettingsFile
    }
    else {
        Write-Warning "Settings file not found at $SettingsFile — using default rules."
    }

    if ($Fix) { $pssaParams['Fix'] = $true }

    $pssaResults = Invoke-ScriptAnalyzer @pssaParams

    foreach ($r in $pssaResults) {
        $allFindings.Add([pscustomobject]@{
            File     = $r.ScriptPath
            Severity = $r.Severity.ToString()
            Rule     = $r.RuleName
            Message  = $r.Message
            Line     = $r.Line
        })
    }
}

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

$errorCount   = ($allFindings | Where-Object Severity -eq 'Error').Count
$warningCount = ($allFindings | Where-Object Severity -eq 'Warning').Count

if ($allFindings.Count -eq 0) {
    Write-Host "PASS — No findings." -ForegroundColor Green
    exit 0
}

foreach ($f in $allFindings | Sort-Object File, Line) {
    Write-Finding -File $f.File -Severity $f.Severity -Rule $f.Rule -Message $f.Message -Line $f.Line
}

Write-Host "`nSummary: $errorCount error(s), $warningCount warning(s) across $($psFiles.Count) file(s)" -ForegroundColor Red
exit 1
