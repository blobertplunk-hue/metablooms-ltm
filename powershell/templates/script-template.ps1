#Requires -Version 7.4
<#
.SYNOPSIS
    One-line description of what this script does.

.DESCRIPTION
    Extended description. State inputs, outputs, side effects, and prerequisites.

.PARAMETER InputPath
    Path to the input file that will be processed.

.PARAMETER Verbose
    Enables verbose progress messages (common parameter, no declaration needed).

.EXAMPLE
    PS> .\script-template.ps1 -InputPath C:\data\input.txt

.NOTES
    Author  : <author>
    Version : 1.0.0
    Requires: PowerShell 7.4+
#>

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory, Position = 0)]
    [ValidateNotNullOrEmpty()]
    [string]$InputPath
)

begin {
    Write-Verbose "Starting: InputPath='$InputPath'"

    # Resolve to an absolute path early so downstream code never has to deal
    # with relative paths.
    $resolvedPath = [System.IO.Path]::GetFullPath($InputPath)
}

process {
    try {
        if (-not (Test-Path -LiteralPath $resolvedPath -PathType Leaf)) {
            $record = [System.Management.Automation.ErrorRecord]::new(
                [System.IO.FileNotFoundException]::new("File not found: $resolvedPath"),
                'InputFileNotFound',
                [System.Management.Automation.ErrorCategory]::ObjectNotFound,
                $resolvedPath
            )
            $PSCmdlet.ThrowTerminatingError($record)
        }

        $content = Get-Content -LiteralPath $resolvedPath -Encoding UTF8

        # Emit a structured object — never a raw string.
        [pscustomobject]@{
            Path      = $resolvedPath
            LineCount = $content.Count
            SizeBytes = (Get-Item -LiteralPath $resolvedPath).Length
        }
    }
    catch {
        # Re-throw so the caller's error handler receives the original record.
        throw
    }
}

end {
    Write-Verbose "Completed."
}
