#Requires -Version 7.4
<#
.SYNOPSIS
    Generates a new PowerShell script or module from the project's compliant templates.

.DESCRIPTION
    Copies the appropriate template (script, function, or module) to the target path,
    substitutes the author placeholder, and opens the file for editing.

    Ensures every new PS file starts fully compliant — correct headers, StrictMode,
    ErrorActionPreference, and CmdletBinding already in place.

.PARAMETER Name
    Name of the new script or module (without extension).

.PARAMETER Type
    Kind of file to generate. One of: Script, Function, Module.

.PARAMETER OutputPath
    Directory where the new file(s) will be written. Created if it does not exist.

.PARAMETER Author
    Author name substituted into the template. Defaults to the current user.

.PARAMETER Open
    Open the generated file in the default editor after creation.

.EXAMPLE
    PS> ./powershell/scripts/New-PSScript.ps1 -Name Deploy -Type Script -OutputPath ./scripts/
    Creates: ./scripts/Deploy.ps1

.EXAMPLE
    PS> ./powershell/scripts/New-PSScript.ps1 -Name FileUtils -Type Module -OutputPath ./modules/
    Creates: ./modules/FileUtils/FileUtils.psd1
             ./modules/FileUtils/FileUtils.psm1
             ./modules/FileUtils/FileUtils.Tests.ps1

.EXAMPLE
    PS> ./powershell/scripts/New-PSScript.ps1 -Name Get-Widget -Type Function -OutputPath ./scripts/
    Creates: ./scripts/Get-Widget.ps1
#>

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory, Position = 0)]
    [ValidateNotNullOrEmpty()]
    [string]$Name,

    [Parameter(Mandatory)]
    [ValidateSet('Script', 'Function', 'Module')]
    [string]$Type,

    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string]$OutputPath,

    [string]$Author = $env:USER ?? $env:USERNAME ?? 'unknown',

    [switch]$Open
)

# ---------------------------------------------------------------------------
# Resolve template root (relative to this script's directory)
# ---------------------------------------------------------------------------

$templateRoot = Join-Path $PSScriptRoot '..' 'templates'
$testsTemplate = Join-Path $PSScriptRoot '..' 'tests' 'Module.Tests.ps1'

function Expand-Template {
    param([string]$TemplatePath, [string]$DestinationPath, [hashtable]$Replacements)

    $content = Get-Content -LiteralPath $TemplatePath -Raw -Encoding UTF8

    foreach ($key in $Replacements.Keys) {
        $content = $content.Replace($key, $Replacements[$key])
    }

    Set-Content -LiteralPath $DestinationPath -Value $content -Encoding UTF8 -NoNewline
    Write-Host "  Created: $DestinationPath" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# Common substitutions
# ---------------------------------------------------------------------------

$year         = (Get-Date).Year
$replacements = @{
    '<author>'  = $Author
    '<company>' = 'MetaBlooms'
    '<year>'    = $year.ToString()
    '00000000-0000-0000-0000-000000000000' = [guid]::NewGuid().ToString()
}

# ---------------------------------------------------------------------------
# Ensure output directory exists
# ---------------------------------------------------------------------------

$resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
if (-not (Test-Path -LiteralPath $resolvedOutput)) {
    if ($PSCmdlet.ShouldProcess($resolvedOutput, 'Create directory')) {
        $null = New-Item -ItemType Directory -Path $resolvedOutput -Force
    }
}

# ---------------------------------------------------------------------------
# Generate by type
# ---------------------------------------------------------------------------

$generatedFiles = [System.Collections.Generic.List[string]]::new()

switch ($Type) {

    'Script' {
        $destFile = Join-Path $resolvedOutput "$Name.ps1"
        $srcTemplate = Join-Path $templateRoot 'script-template.ps1'

        if ($PSCmdlet.ShouldProcess($destFile, 'Create script from template')) {
            Expand-Template -TemplatePath $srcTemplate -DestinationPath $destFile -Replacements $replacements
            $generatedFiles.Add($destFile)
        }
    }

    'Function' {
        $destFile = Join-Path $resolvedOutput "$Name.ps1"
        $srcTemplate = Join-Path $templateRoot 'function-template.ps1'

        if ($PSCmdlet.ShouldProcess($destFile, 'Create function file from template')) {
            Expand-Template -TemplatePath $srcTemplate -DestinationPath $destFile -Replacements $replacements
            $generatedFiles.Add($destFile)
        }
    }

    'Module' {
        $moduleDir = Join-Path $resolvedOutput $Name

        if ($PSCmdlet.ShouldProcess($moduleDir, 'Create module directory and files')) {
            $null = New-Item -ItemType Directory -Path $moduleDir -Force

            # Module replacements also substitute the generic module name.
            $moduleReplacements = $replacements + @{
                'Module.psm1' = "$Name.psm1"
                "'Get-ItemSafe', 'Invoke-SafeOperation'" = "'Get-ItemSafe', 'Invoke-SafeOperation'"
            }

            # psd1
            $psd1Src  = Join-Path $templateRoot 'module' 'Module.psd1'
            $psd1Dest = Join-Path $moduleDir "$Name.psd1"
            $psd1Content = (Get-Content -LiteralPath $psd1Src -Raw -Encoding UTF8).
                Replace('Module.psm1', "$Name.psm1").
                Replace('<author>', $Author).
                Replace('<company>', 'MetaBlooms').
                Replace('<year>', $year.ToString()).
                Replace('00000000-0000-0000-0000-000000000000', [guid]::NewGuid().ToString()).
                Replace('<one-sentence module description>', "Module: $Name").
                Replace("'<REPLACE>'", "'$Name'")
            Set-Content -LiteralPath $psd1Dest -Value $psd1Content -Encoding UTF8 -NoNewline
            Write-Host "  Created: $psd1Dest" -ForegroundColor Green
            $generatedFiles.Add($psd1Dest)

            # psm1
            $psm1Src  = Join-Path $templateRoot 'module' 'Module.psm1'
            $psm1Dest = Join-Path $moduleDir "$Name.psm1"
            Expand-Template -TemplatePath $psm1Src -DestinationPath $psm1Dest -Replacements $replacements
            $generatedFiles.Add($psm1Dest)

            # Tests
            $testDest = Join-Path $moduleDir "$Name.Tests.ps1"
            $testContent = (Get-Content -LiteralPath $testsTemplate -Raw -Encoding UTF8).
                Replace("'Module'", "'$Name'").
                Replace('Module.psd1', "$Name.psd1")
            Set-Content -LiteralPath $testDest -Value $testContent -Encoding UTF8 -NoNewline
            Write-Host "  Created: $testDest" -ForegroundColor Green
            $generatedFiles.Add($testDest)
        }
    }
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Host "`nGenerated $($generatedFiles.Count) file(s). Run compliance check:" -ForegroundColor Cyan
Write-Host "  pwsh ./powershell/scripts/Invoke-PSCompliance.ps1 -Path $resolvedOutput`n"

if ($Open -and $generatedFiles.Count -gt 0) {
    $editor = $env:EDITOR ?? $env:VISUAL ?? 'code'
    & $editor $generatedFiles[0]
}

# Return file paths as structured output.
foreach ($f in $generatedFiles) {
    [pscustomobject]@{ GeneratedFile = $f }
}
