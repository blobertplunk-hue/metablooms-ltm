#Requires -Version 7.4
<#
    Module.psm1 — root module script
    Loaded automatically when the caller imports the module via Module.psd1.
#>

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Private helpers (not listed in FunctionsToExport — never visible to callers)
# ---------------------------------------------------------------------------

function Resolve-SafePath {
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $resolved = [System.IO.Path]::GetFullPath($Path)
    if (-not (Test-Path -LiteralPath $resolved)) {
        $record = [System.Management.Automation.ErrorRecord]::new(
            [System.IO.FileNotFoundException]::new("Path not found: $resolved"),
            'PathNotFound',
            [System.Management.Automation.ErrorCategory]::ObjectNotFound,
            $resolved
        )
        $PSCmdlet.ThrowTerminatingError($record)
    }
    $resolved
}

# ---------------------------------------------------------------------------
# Public functions (must match FunctionsToExport in Module.psd1)
# ---------------------------------------------------------------------------

function Get-ItemSafe {
<#
.SYNOPSIS
    Retrieves a filesystem item, terminating on failure.

.DESCRIPTION
    Wraps Get-Item with a structured ErrorRecord so callers receive consistent
    error information regardless of the underlying exception type.

.PARAMETER Path
    Path(s) to retrieve. Accepts pipeline input. Supports wildcards.

.PARAMETER LiteralPath
    Path(s) without wildcard expansion. Mutually exclusive with Path.

.INPUTS
    System.String

.OUTPUTS
    System.IO.FileSystemInfo

.EXAMPLE
    PS> Get-ItemSafe -Path $PSHOME

.EXAMPLE
    PS> 'C:\Windows', 'C:\Temp' | Get-ItemSafe
#>
    [CmdletBinding(DefaultParameterSetName = 'Path')]
    [OutputType([System.IO.FileSystemInfo])]
    param(
        [Parameter(
            Mandatory,
            Position = 0,
            ValueFromPipeline,
            ValueFromPipelineByPropertyName,
            ParameterSetName = 'Path'
        )]
        [ValidateNotNullOrEmpty()]
        [string[]]$Path,

        [Parameter(
            Mandatory,
            ValueFromPipelineByPropertyName,
            ParameterSetName = 'LiteralPath'
        )]
        [ValidateNotNullOrEmpty()]
        [Alias('PSPath')]
        [string[]]$LiteralPath
    )

    process {
        $targets = if ($PSCmdlet.ParameterSetName -eq 'LiteralPath') { $LiteralPath } else { $Path }

        foreach ($target in $targets) {
            try {
                $params = if ($PSCmdlet.ParameterSetName -eq 'LiteralPath') {
                    @{ LiteralPath = $target; ErrorAction = 'Stop' }
                }
                else {
                    @{ Path = $target; ErrorAction = 'Stop' }
                }

                Get-Item @params
            }
            catch {
                $PSCmdlet.ThrowTerminatingError($_)
            }
        }
    }
}

function Invoke-SafeOperation {
<#
.SYNOPSIS
    Template for a mutating operation with -WhatIf/-Confirm support.

.PARAMETER Target
    The path or identifier to operate on.

.PARAMETER Force
    Suppresses confirmation prompts.

.OUTPUTS
    pscustomobject with Target and Success properties.

.EXAMPLE
    PS> Invoke-SafeOperation -Target 'C:\Temp\file.txt'

.EXAMPLE
    PS> Invoke-SafeOperation -Target 'C:\Temp\file.txt' -WhatIf
#>
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'Medium')]
    [OutputType([pscustomobject])]
    param(
        [Parameter(Mandatory, ValueFromPipeline)]
        [ValidateNotNullOrEmpty()]
        [string]$Target,

        [switch]$Force
    )

    begin {
        $results = [System.Collections.Generic.List[pscustomobject]]::new()
    }

    process {
        if ($Force -or $PSCmdlet.ShouldProcess($Target, 'Invoke-SafeOperation')) {
            try {
                # Replace with actual operation.
                $results.Add([pscustomobject]@{
                    Target  = $Target
                    Success = $true
                })
            }
            catch {
                $PSCmdlet.ThrowTerminatingError($_)
            }
        }
    }

    end {
        foreach ($r in $results) { $r }
    }
}
