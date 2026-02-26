#Requires -Version 7.4
<#
.SYNOPSIS
    Redacts PII and sensitive patterns from a text file before upload.

.DESCRIPTION
    Applies the patterns defined in config/redaction-patterns.json to an
    input file, replacing each match with a stable token:
        [REDACTED_{TYPE}_{SEQUENCE}]

    Saves the redacted output to OutputPath and writes a redaction map
    (input → token) locally. The redaction map is NEVER uploaded.

    The replacement tokens preserve approximate token count and allow
    the LLM to reason about redacted content without seeing the values.

    Defect fixes applied:
      - Single-pass, non-overlapping match collection eliminates the
        double-redaction problem that arose when a replacement token
        matched a subsequent pattern.
      - $matches (PS automatic variable) renamed to $foundMatches to
        prevent automatic-variable shadowing.
      - Write-Host replaced with Write-Information ($PSStyle colours).

.PARAMETER InputPath
    File to redact (JSONL, JSON, or plain text).

.PARAMETER OutputPath
    Destination for the redacted file.

.PARAMETER PatternsPath
    Path to redaction-patterns.json. Defaults to .\config\redaction-patterns.json.

.PARAMETER RedactionMapPath
    Where to write the local redaction map. Defaults to .\workspace\redaction-map.json.
    Keep this file local — do not upload it.

.EXAMPLE
    PS> .\scripts\Invoke-Redact.ps1 -InputPath .\workspace\redacted\sample.jsonl -OutputPath .\workspace\redacted\sample-clean.jsonl

.NOTES
    Always run before uploading any artifact to an LLM.
#>

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'
$InformationPreference = 'Continue'

[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory, Position = 0)]
    [ValidateNotNullOrEmpty()]
    [string]$InputPath,

    [Parameter(Mandatory, Position = 1)]
    [ValidateNotNullOrEmpty()]
    [string]$OutputPath,

    [string]$PatternsPath    = (Join-Path '.' 'chatgpt-memory' 'config' 'redaction-patterns.json'),

    [string]$RedactionMapPath = (Join-Path '.' 'workspace' 'redaction-map.json')
)

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------

$resolvedInput    = [System.IO.Path]::GetFullPath($InputPath)
$resolvedOutput   = [System.IO.Path]::GetFullPath($OutputPath)
$resolvedPatterns = [System.IO.Path]::GetFullPath($PatternsPath)
$resolvedMapPath  = [System.IO.Path]::GetFullPath($RedactionMapPath)

foreach ($p in @($resolvedInput, $resolvedPatterns)) {
    if (-not (Test-Path -LiteralPath $p -PathType Leaf)) {
        $record = [System.Management.Automation.ErrorRecord]::new(
            [System.IO.FileNotFoundException]::new("File not found: $p"),
            'FileNotFound',
            [System.Management.Automation.ErrorCategory]::ObjectNotFound,
            $p
        )
        $PSCmdlet.ThrowTerminatingError($record)
    }
}

$outputDir = [System.IO.Path]::GetDirectoryName($resolvedOutput)
if (-not (Test-Path -LiteralPath $outputDir)) {
    $null = New-Item -ItemType Directory -Path $outputDir -Force
}

# ---------------------------------------------------------------------------
# Load patterns
# ---------------------------------------------------------------------------

$patternConfig = Get-Content -LiteralPath $resolvedPatterns -Encoding UTF8 | ConvertFrom-Json
Write-Verbose "Loaded $($patternConfig.patterns.Count) redaction pattern(s)"

# ---------------------------------------------------------------------------
# Pre-compile regexes once (avoids repeated compilation inside the line loop)
# ---------------------------------------------------------------------------

$compiledPatterns = [System.Collections.Generic.List[pscustomobject]]::new()
foreach ($p in $patternConfig.patterns) {
    $compiledPatterns.Add([pscustomobject]@{
        Type  = $p.type
        Regex = [System.Text.RegularExpressions.Regex]::new(
            $p.regex,
            [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor
            [System.Text.RegularExpressions.RegexOptions]::Compiled
        )
    })
}

# ---------------------------------------------------------------------------
# Build redaction state
# ---------------------------------------------------------------------------

$redactionMap     = [System.Collections.Generic.Dictionary[string, string]]::new()
$sequenceCounters = [System.Collections.Generic.Dictionary[string, int]]::new()

foreach ($p in $patternConfig.patterns) {
    $sequenceCounters[$p.type] = 0
}

function Get-RedactionToken {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Type,

        [Parameter(Mandatory)]
        [string]$OriginalValue
    )

    if ($redactionMap.ContainsKey($OriginalValue)) {
        return $redactionMap[$OriginalValue]
    }

    $seq   = $sequenceCounters[$Type]
    $token = "[REDACTED_${Type}_$('{0:D4}' -f $seq)]"
    $sequenceCounters[$Type] = $seq + 1
    $redactionMap[$OriginalValue] = $token
    return $token
}

# ---------------------------------------------------------------------------
# Process file line by line (streaming — works on large JSONL).
#
# Single-pass strategy: for each line, collect ALL match spans from ALL
# patterns before making any substitution. After removing overlapping spans
# (keep earliest start), apply replacements right-to-left so earlier string
# positions remain valid. This prevents a replacement token from being
# matched and re-redacted by a subsequent pattern.
# ---------------------------------------------------------------------------

$totalReplacements = 0
$processedLines    = 0

if ($PSCmdlet.ShouldProcess($resolvedOutput, 'Write redacted file')) {
    $writer = [System.IO.StreamWriter]::new($resolvedOutput, $false, [System.Text.Encoding]::UTF8)

    try {
        $reader = [System.IO.StreamReader]::new($resolvedInput, [System.Text.Encoding]::UTF8)

        try {
            while (-not $reader.EndOfStream) {
                $line = $reader.ReadLine()
                $processedLines++

                # --- Collect all match spans from all patterns ---
                $candidates = [System.Collections.Generic.List[pscustomobject]]::new()

                foreach ($cp in $compiledPatterns) {
                    $foundMatches = $cp.Regex.Matches($line)
                    foreach ($m in $foundMatches) {
                        $candidates.Add([pscustomobject]@{
                            Start         = $m.Index
                            End           = $m.Index + $m.Length
                            OriginalValue = $m.Value
                            PatternType   = $cp.Type
                        })
                    }
                }

                if ($candidates.Count -eq 0) {
                    $writer.WriteLine($line)
                    continue
                }

                # --- Remove overlapping spans: sort by start, keep earliest ---
                $sorted = $candidates | Sort-Object Start

                $nonOverlapping = [System.Collections.Generic.List[pscustomobject]]::new()
                $currentEnd = -1

                foreach ($r in $sorted) {
                    if ($r.Start -ge $currentEnd) {
                        $nonOverlapping.Add($r)
                        $currentEnd = $r.End
                    }
                }

                # --- Apply right-to-left so earlier positions stay valid ---
                $nonOverlapping.Reverse()

                foreach ($r in $nonOverlapping) {
                    $token = Get-RedactionToken -Type $r.PatternType -OriginalValue $r.OriginalValue
                    $line  = $line.Substring(0, $r.Start) + $token + $line.Substring($r.End)
                    $totalReplacements++
                }

                $writer.WriteLine($line)
            }
        }
        finally {
            $reader.Dispose()
        }
    }
    finally {
        $writer.Dispose()
    }
}

# ---------------------------------------------------------------------------
# Save redaction map (local only — do not upload)
# ---------------------------------------------------------------------------

$mapDir = [System.IO.Path]::GetDirectoryName($resolvedMapPath)
if (-not (Test-Path -LiteralPath $mapDir)) {
    $null = New-Item -ItemType Directory -Path $mapDir -Force
}

$mapObject = [pscustomobject]@{
    generated_at     = (Get-Date -Format 'o')
    source_file      = $resolvedInput
    redacted_file    = $resolvedOutput
    total_redactions = $totalReplacements
    map              = $redactionMap
}

$mapObject | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $resolvedMapPath -Encoding UTF8

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Information "$($PSStyle.Foreground.BrightGreen)Redaction complete.$($PSStyle.Reset)"
Write-Information "  Lines processed   : $processedLines"
Write-Information "  Replacements made : $totalReplacements"
Write-Information "  Redacted output   : $resolvedOutput"
Write-Information "  Redaction map     : $resolvedMapPath $($PSStyle.Foreground.BrightYellow)(LOCAL ONLY — do not upload)$($PSStyle.Reset)"

[pscustomobject]@{
    InputPath            = $resolvedInput
    OutputPath           = $resolvedOutput
    LinesProcessed       = $processedLines
    TotalReplacements    = $totalReplacements
    UniqueValuesRedacted = $redactionMap.Count
}
