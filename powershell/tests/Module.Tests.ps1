#Requires -Version 7.4
#Requires -Modules @{ ModuleName = 'Pester'; ModuleVersion = '5.0' }
<#
    Module.Tests.ps1 — Pester 5 test suite for the Module template.

    Run from the repo root:
        Invoke-Pester ./powershell/tests/ -Output Detailed

    Or with coverage:
        Invoke-Pester ./powershell/tests/ -CodeCoverage ./powershell/templates/module/Module.psm1
#>

BeforeAll {
    # Import the module under test using the manifest so FunctionsToExport is honoured.
    $ModulePath = Join-Path $PSScriptRoot '..' 'templates' 'module' 'Module.psd1'
    Import-Module -Name $ModulePath -Force -ErrorAction Stop
}

AfterAll {
    Remove-Module -Name 'Module' -ErrorAction SilentlyContinue
}

# ---------------------------------------------------------------------------
# Get-ItemSafe
# ---------------------------------------------------------------------------
Describe 'Get-ItemSafe' {

    Context 'Valid path' {

        It 'Returns a FileSystemInfo object for an existing directory' {
            $result = Get-ItemSafe -Path $PSHOME
            $result | Should -Not -BeNullOrEmpty
            $result | Should -BeOfType [System.IO.DirectoryInfo]
        }

        It 'Returns multiple items when given multiple paths' {
            $paths = @($PSHOME, $env:TEMP)
            $results = $paths | Get-ItemSafe
            $results.Count | Should -Be 2
        }

        It 'Accepts pipeline input' {
            $result = $PSHOME | Get-ItemSafe
            $result | Should -Not -BeNullOrEmpty
        }

        It 'Accepts LiteralPath parameter set' {
            $result = Get-ItemSafe -LiteralPath $PSHOME
            $result | Should -Not -BeNullOrEmpty
        }
    }

    Context 'Invalid path' {

        It 'Throws a terminating error for a non-existent path' {
            { Get-ItemSafe -Path 'Z:\this\does\not\exist\__test__' } | Should -Throw
        }

        It 'Throws when piped a non-existent path' {
            { 'Z:\nonexistent\__test__' | Get-ItemSafe } | Should -Throw
        }
    }

    Context 'Parameter validation' {

        It 'Rejects an empty string for Path' {
            { Get-ItemSafe -Path '' } | Should -Throw
        }

        It 'Rejects null for Path' {
            { Get-ItemSafe -Path $null } | Should -Throw
        }
    }
}

# ---------------------------------------------------------------------------
# Invoke-SafeOperation
# ---------------------------------------------------------------------------
Describe 'Invoke-SafeOperation' {

    Context 'Normal execution' {

        It 'Returns a pscustomobject with Target and Success properties' {
            $result = Invoke-SafeOperation -Target 'test-target' -Force
            $result | Should -Not -BeNullOrEmpty
            $result.Target  | Should -Be 'test-target'
            $result.Success | Should -BeTrue
        }

        It 'Accepts pipeline input' {
            $results = 'target-a', 'target-b' | Invoke-SafeOperation -Force
            $results.Count | Should -Be 2
        }
    }

    Context '-WhatIf support' {

        It 'Produces no output when -WhatIf is specified' {
            $result = Invoke-SafeOperation -Target 'test-target' -WhatIf
            $result | Should -BeNullOrEmpty
        }
    }

    Context 'Parameter validation' {

        It 'Rejects an empty Target' {
            { Invoke-SafeOperation -Target '' -Force } | Should -Throw
        }
    }
}

# ---------------------------------------------------------------------------
# Module hygiene
# ---------------------------------------------------------------------------
Describe 'Module hygiene' {

    It 'Exports exactly the functions declared in the manifest' {
        $exported = (Get-Module -Name Module).ExportedFunctions.Keys | Sort-Object
        $expected = @('Get-ItemSafe', 'Invoke-SafeOperation') | Sort-Object
        $exported | Should -Be $expected
    }

    It 'Does not export private helpers' {
        $exported = (Get-Module -Name Module).ExportedFunctions.Keys
        $exported | Should -Not -Contain 'Resolve-SafePath'
    }
}
