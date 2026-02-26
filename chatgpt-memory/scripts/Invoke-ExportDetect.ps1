#Requires -Version 7.4
<#
.SYNOPSIS
    Phase 0: Detects, validates, and maps the structure of a ChatGPT export zip.

.DESCRIPTION
    Reads the zip file without fully extracting it. Produces a detection report
    (JSON) that confirms the export format, file inventory, and zip integrity.

    If any required file is missing or the zip is corrupt, exits with code 1
    and describes exactly what is wrong. This is the fail-closed gate for the
    entire pipeline — nothing downstream runs until this passes.

.PARAMETER ZipPath
    Path to the ChatGPT export zip file (e.g. C:\exports\export-2024-01-15.zip).

.PARAMETER OutputPath
    Directory where detection-report.json is written. Defaults to .\workspace\manifests\.

.PARAMETER SkipHashCheck
    Skip SHA-256 computation (useful on very slow storage for a quick structural check).

.EXAMPLE
    PS> .\scripts\Invoke-ExportDetect.ps1 -ZipPath C:\exports\export.zip

.EXAMPLE
    PS> .\scripts\Invoke-ExportDetect.ps1 -ZipPath C:\exports\export.zip -OutputPath C:\work\manifests\

.NOTES
    Produces: detection-report.json
    Acceptance criteria: conversations_json_size_bytes > 0, no error-level warnings.
#>

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory, Position = 0)]
    [ValidateNotNullOrEmpty()]
    [string]$ZipPath,

    [string]$OutputPath = (Join-Path '.' 'workspace' 'manifests'),

    [switch]$SkipHashCheck
)

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------

$resolvedZip = [System.IO.Path]::GetFullPath($ZipPath)

if (-not (Test-Path -LiteralPath $resolvedZip -PathType Leaf)) {
    $record = [System.Management.Automation.ErrorRecord]::new(
        [System.IO.FileNotFoundException]::new("Zip not found: $resolvedZip"),
        'ZipNotFound',
        [System.Management.Automation.ErrorCategory]::ObjectNotFound,
        $resolvedZip
    )
    $PSCmdlet.ThrowTerminatingError($record)
}

$resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
if (-not (Test-Path -LiteralPath $resolvedOutput)) {
    $null = New-Item -ItemType Directory -Path $resolvedOutput -Force
    Write-Verbose "Created output directory: $resolvedOutput"
}

# ---------------------------------------------------------------------------
# Known ChatGPT export file inventory
# ---------------------------------------------------------------------------

$knownFiles = @{
    'conversations.json'         = @{ Required = $true;  Description = 'Primary conversation corpus' }
    'user.json'                  = @{ Required = $false; Description = 'Account metadata' }
    'message_feedback.json'      = @{ Required = $false; Description = 'Thumbs up/down feedback' }
    'model_comparisons.json'     = @{ Required = $false; Description = 'A/B test comparison data' }
    'shared_conversations.json'  = @{ Required = $false; Description = 'Shared conversation links' }
}

# ---------------------------------------------------------------------------
# Open zip and inventory entries
# ---------------------------------------------------------------------------

Write-Verbose "Opening zip: $resolvedZip"

$warnings   = [System.Collections.Generic.List[string]]::new()
$detectedFiles = [System.Collections.Generic.List[pscustomobject]]::new()
$convoSizeBytes = 0L

try {
    $zip = [System.IO.Compression.ZipFile]::OpenRead($resolvedZip)

    try {
        foreach ($entry in $zip.Entries) {
            $name      = $entry.Name
            $fullName  = $entry.FullName
            $sizeBytes = $entry.Length

            $known = $knownFiles[$name]
            $detectedFiles.Add([pscustomobject]@{
                FullName    = $fullName
                Name        = $name
                SizeBytes   = $sizeBytes
                Known       = ($null -ne $known)
                Required    = if ($null -ne $known) { $known.Required } else { $false }
                Description = if ($null -ne $known) { $known.Description } else { 'Unknown file' }
            })

            if ($name -eq 'conversations.json') {
                $convoSizeBytes = $sizeBytes
            }
        }
    }
    finally {
        $zip.Dispose()
    }
}
catch {
    $PSCmdlet.ThrowTerminatingError($_)
}

# ---------------------------------------------------------------------------
# Validation checks
# ---------------------------------------------------------------------------

foreach ($kv in $knownFiles.GetEnumerator()) {
    if ($kv.Value.Required) {
        $found = $detectedFiles | Where-Object Name -eq $kv.Key
        if (-not $found) {
            $warnings.Add("REQUIRED file missing: $($kv.Key)")
        }
    }
}

if ($convoSizeBytes -eq 0) {
    $warnings.Add("conversations.json has zero bytes — corrupt or empty export.")
}

$zipInfo    = Get-Item -LiteralPath $resolvedZip
$zipSizeBytes = $zipInfo.Length

# ---------------------------------------------------------------------------
# SHA-256 of zip
# ---------------------------------------------------------------------------

$zipHash = $null
if (-not $SkipHashCheck) {
    Write-Verbose "Computing SHA-256 of zip ($([math]::Round($zipSizeBytes / 1MB, 1)) MB)…"
    $zipHash = (Get-FileHash -LiteralPath $resolvedZip -Algorithm SHA256).Hash.ToLower()
}

# ---------------------------------------------------------------------------
# Format version heuristic
# ---------------------------------------------------------------------------

$formatGuess = switch ($true) {
    ($convoSizeBytes -gt 1GB) { '2024-large-corpus' }
    ($convoSizeBytes -gt 100MB) { '2024-medium-corpus' }
    default { '2024-small-corpus' }
}

# ---------------------------------------------------------------------------
# Produce report
# ---------------------------------------------------------------------------

$report = [pscustomobject]@{
    zip_path                   = $resolvedZip
    zip_sha256                 = $zipHash
    zip_size_bytes             = $zipSizeBytes
    conversations_json_size_bytes = $convoSizeBytes
    total_entries              = $detectedFiles.Count
    detected_files             = $detectedFiles | ForEach-Object { $_.Name }
    file_inventory             = $detectedFiles
    format_version_guess       = $formatGuess
    warnings                   = $warnings
    passed                     = ($warnings.Count -eq 0)
    generated_at               = (Get-Date -Format 'o')
}

$reportPath = Join-Path $resolvedOutput 'detection-report.json'

if ($PSCmdlet.ShouldProcess($reportPath, 'Write detection report')) {
    $report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportPath -Encoding UTF8
    Write-Host "Detection report written: $reportPath" -ForegroundColor Cyan
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

if ($report.passed) {
    Write-Host "PASS — Export structure valid. $($detectedFiles.Count) entries detected." -ForegroundColor Green
    Write-Host "       conversations.json: $([math]::Round($convoSizeBytes / 1GB, 2)) GB"
}
else {
    Write-Host "FAIL — $($warnings.Count) warning(s):" -ForegroundColor Red
    foreach ($w in $warnings) {
        Write-Host "  ! $w" -ForegroundColor Yellow
    }
    exit 1
}

# Return structured object for pipeline chaining.
$report
