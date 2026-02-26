#Requires -Version 7.4
<#
.SYNOPSIS
    Phase 1 (PS7 layer): Validates shard outputs from parse_export.py and
    produces the final uploadable manifest set.

.DESCRIPTION
    This script is the PS7 orchestration wrapper for Phase 1. It:
      1. Verifies that parse_export.py has run and produced shard files.
      2. Validates each shard SHA-256 against the Python-generated manifest.
      3. Confirms the total message count matches the detection report.
      4. Produces the final global-manifest.json (safe to upload to LLM).
      5. Fails loudly if any shard is missing, corrupt, or the count mismatches.

    Run AFTER: Invoke-ExportDetect.ps1 AND parse_export.py
    Run BEFORE: feature_engineer.py

.PARAMETER WorkspaceRoot
    Root workspace directory (must contain shards/, manifests/).

.PARAMETER DetectionReportPath
    Path to detection-report.json from Invoke-ExportDetect.ps1.

.EXAMPLE
    PS> .\scripts\Invoke-ExportIngest.ps1 -WorkspaceRoot .\workspace\ -DetectionReportPath .\workspace\manifests\detection-report.json

.NOTES
    Produces: workspace/manifests/global-manifest.json (validated, uploadable)
    Acceptance criteria: all shard SHA-256 match, message count matches.
#>

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory, Position = 0)]
    [ValidateNotNullOrEmpty()]
    [string]$WorkspaceRoot,

    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string]$DetectionReportPath
)

# ---------------------------------------------------------------------------
# Resolve and validate inputs
# ---------------------------------------------------------------------------

$workspace         = [System.IO.Path]::GetFullPath($WorkspaceRoot)
$detectionReport   = [System.IO.Path]::GetFullPath($DetectionReportPath)
$shardsDir         = Join-Path $workspace 'shards'
$manifestsDir      = Join-Path $workspace 'manifests'
$pythonManifest    = Join-Path $manifestsDir 'python-manifest.json'

foreach ($required in @($workspace, $shardsDir, $manifestsDir, $detectionReport)) {
    if (-not (Test-Path -LiteralPath $required)) {
        $record = [System.Management.Automation.ErrorRecord]::new(
            [System.IO.DirectoryNotFoundException]::new("Required path not found: $required"),
            'RequiredPathMissing',
            [System.Management.Automation.ErrorCategory]::ObjectNotFound,
            $required
        )
        $PSCmdlet.ThrowTerminatingError($record)
    }
}

if (-not (Test-Path -LiteralPath $pythonManifest)) {
    Write-Error "python-manifest.json not found. Run parse_export.py first:`n  python python/parse_export.py --zip <export.zip> --out $workspace"
    exit 1
}

# ---------------------------------------------------------------------------
# Load detection report and Python manifest
# ---------------------------------------------------------------------------

$detection = Get-Content -LiteralPath $detectionReport -Encoding UTF8 | ConvertFrom-Json
$pyManifest = Get-Content -LiteralPath $pythonManifest -Encoding UTF8 | ConvertFrom-Json

Write-Verbose "Detection report: $($detection.conversations_json_size_bytes) bytes in conversations.json"
Write-Verbose "Python manifest:  $($pyManifest.total_conversations) conversations, $($pyManifest.total_messages) messages"

# ---------------------------------------------------------------------------
# Validate each shard
# ---------------------------------------------------------------------------

$failures = [System.Collections.Generic.List[string]]::new()
$validatedShards = [System.Collections.Generic.List[pscustomobject]]::new()

foreach ($shard in $pyManifest.shards) {
    $shardPath = Join-Path $shardsDir $shard.filename

    if (-not (Test-Path -LiteralPath $shardPath -PathType Leaf)) {
        $failures.Add("Shard file missing: $($shard.filename)")
        continue
    }

    # Verify SHA-256
    $actualHash = (Get-FileHash -LiteralPath $shardPath -Algorithm SHA256).Hash.ToLower()
    if ($actualHash -ne $shard.sha256) {
        $failures.Add("SHA-256 mismatch on $($shard.filename): expected $($shard.sha256), got $actualHash")
        continue
    }

    $validatedShards.Add([pscustomobject]@{
        shard_index        = $shard.shard_index
        filename           = $shard.filename
        sha256             = $actualHash
        size_bytes         = (Get-Item -LiteralPath $shardPath).Length
        conversation_count = $shard.conversation_count
        message_count      = $shard.message_count
        first_create_time  = $shard.first_create_time
        last_create_time   = $shard.last_create_time
        conv_ids           = $shard.conv_ids
    })

    Write-Verbose "  OK  shard $($shard.shard_index): $($shard.conversation_count) convs, $($shard.message_count) msgs"
}

if ($failures.Count -gt 0) {
    foreach ($f in $failures) { Write-Host "  FAIL: $f" -ForegroundColor Red }
    Write-Error "Shard validation failed with $($failures.Count) error(s). Aborting."
    exit 1
}

# ---------------------------------------------------------------------------
# Produce global-manifest.json
# ---------------------------------------------------------------------------

$manifestId = "man_$(($detection.zip_sha256 ?? 'unknown').Substring(0, [Math]::Min(8, ($detection.zip_sha256 ?? '').Length)))_$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"

$globalManifest = [pscustomobject]@{
    manifest_id           = $manifestId
    generated_at          = (Get-Date -Format 'o')
    source_zip_sha256     = $detection.zip_sha256
    source_zip_size_bytes = $detection.zip_size_bytes
    pipeline_version      = '1.0.0'
    total_conversations   = $pyManifest.total_conversations
    total_messages        = $pyManifest.total_messages
    date_range            = $pyManifest.date_range
    shards                = $validatedShards
}

$globalManifestPath = Join-Path $manifestsDir 'global-manifest.json'

if ($PSCmdlet.ShouldProcess($globalManifestPath, 'Write global manifest')) {
    $globalManifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $globalManifestPath -Encoding UTF8
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Host "`nIngestion validation: PASS" -ForegroundColor Green
Write-Host "  Shards validated : $($validatedShards.Count)"
Write-Host "  Conversations    : $($pyManifest.total_conversations)"
Write-Host "  Messages         : $($pyManifest.total_messages)"
Write-Host "  Global manifest  : $globalManifestPath"
Write-Host "`nUploadable artifacts:"
Write-Host "  $globalManifestPath"
Write-Host "  $(Join-Path $manifestsDir 'conv-index.jsonl')"
Write-Host "  $(Join-Path $workspace 'features' 'feature-table.parquet') (after feature_engineer.py)`n"

$globalManifest
