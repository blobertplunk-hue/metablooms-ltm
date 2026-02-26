#Requires -Version 7.4
<#
    Advanced function template — PS7.4+

    Copy this file into your module's .psm1 or dot-source it into a script.
    Replace every placeholder marked with <REPLACE>.
#>

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

function Get-ItemSafe {
<#
.SYNOPSIS
    Retrieves a filesystem item, terminating on failure.

.DESCRIPTION
    Wraps Get-Item with a structured terminating error so callers receive a
    well-formed ErrorRecord rather than a raw exception.

.PARAMETER Path
    One or more paths to retrieve. Accepts pipeline input.

.PARAMETER LiteralPath
    Same as Path, but no wildcard expansion. Mutually exclusive with Path.

.INPUTS
    System.String — path strings piped from upstream.

.OUTPUTS
    System.IO.FileSystemInfo — the retrieved item.

.EXAMPLE
    PS> Get-ItemSafe -Path C:\Windows

.EXAMPLE
    PS> 'C:\Windows', 'C:\Temp' | Get-ItemSafe

.NOTES
    Author  : <author>
    Version : 1.0.0
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
        $targets = if ($PSCmdlet.ParameterSetName -eq 'LiteralPath') {
            $LiteralPath
        }
        else {
            $Path
        }

        foreach ($target in $targets) {
            try {
                $getItemParams = if ($PSCmdlet.ParameterSetName -eq 'LiteralPath') {
                    @{ LiteralPath = $target; ErrorAction = 'Stop' }
                }
                else {
                    @{ Path = $target; ErrorAction = 'Stop' }
                }

                Get-Item @getItemParams
            }
            catch {
                # Preserve the original ErrorRecord; re-surface as terminating.
                $PSCmdlet.ThrowTerminatingError($_)
            }
        }
    }
}

# ---------------------------------------------------------------------------
# Additional function skeleton — replace <VERB> and <NOUN>
# ---------------------------------------------------------------------------

function Invoke-SafeOperation {
<#
.SYNOPSIS
    Template for a function that mutates state (use SupportsShouldProcess).

.PARAMETER Target
    The object or path to operate on.

.PARAMETER Force
    Skips confirmation prompts.

.EXAMPLE
    PS> Invoke-SafeOperation -Target 'C:\Temp\file.txt'
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
        # Initialise any expensive resources once, not per-item.
        $results = [System.Collections.Generic.List[pscustomobject]]::new()
    }

    process {
        if ($Force -or $PSCmdlet.ShouldProcess($Target, 'Invoke-SafeOperation')) {
            try {
                # --- perform the operation ---
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
        # Stream results after all pipeline input is consumed.
        foreach ($r in $results) {
            $r    # Emit structured object; caller decides how to display.
        }
    }
}
