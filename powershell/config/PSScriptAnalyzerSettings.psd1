# PSScriptAnalyzerSettings.psd1
# Project-level ruleset for PSScriptAnalyzer.
#
# Run:
#   Invoke-ScriptAnalyzer -Path . -Recurse -Settings ./powershell/config/PSScriptAnalyzerSettings.psd1
#
# Reference: https://github.com/PowerShell/PSScriptAnalyzer

@{
    # -----------------------------------------------------------------------
    # Severity filter — warn on everything Warning and above.
    # Set to @('Error') for CI pipelines that must not break on warnings.
    # -----------------------------------------------------------------------
    Severity = @('Warning', 'Error')

    # -----------------------------------------------------------------------
    # Rules to INCLUDE (explicit allow-list)
    # Add/remove rules to match project conventions.
    # -----------------------------------------------------------------------
    IncludeRules = @(
        # Security
        'PSAvoidUsingInvokeExpression'          # Prevents command injection
        'PSAvoidUsingPlainTextForPassword'      # Prevents credential leakage
        'PSAvoidUsingConvertToSecureStringWithPlainText'

        # Code quality
        'PSUseApprovedVerbs'                   # Verb-Noun naming
        'PSUseDeclaredVarsMoreThanAssignments'  # Unused variable detection
        'PSReviewUnusedParameter'              # Unused parameter detection
        'PSUseSingularNouns'                   # Noun normalisation
        'PSUseConsistentIndentation'
        'PSUseConsistentWhitespace'
        'PSAlignAssignmentStatement'

        # Safety
        'PSAvoidUsingWriteHost'                # Forces Write-Information/Verbose
        'PSAvoidGlobalVars'                    # Prevents global state pollution
        'PSAvoidDefaultValueForMandatoryParameter'
        'PSAvoidUsingPositionalParameters'     # Enforces named parameters

        # Pipeline correctness
        'PSUseShouldProcessForStateChangingFunctions'

        # Portability
        'PSAvoidUsingCmdletAliases'            # Aliases differ across OS/versions
        'PSAvoidUsingWMICmdlet'                # WMI not available on Linux/macOS

        # Module hygiene
        'PSMissingModuleManifestField'
        'PSUseOutputTypeCorrectly'
    )

    # -----------------------------------------------------------------------
    # Rules to EXCLUDE
    # Document the reason for every exclusion.
    # -----------------------------------------------------------------------
    ExcludeRules = @(
        # 'PSAvoidUsingWriteHost'  # Example: uncomment to allow Write-Host in scripts
    )

    # -----------------------------------------------------------------------
    # Per-rule configuration
    # -----------------------------------------------------------------------
    Rules = @{
        PSUseConsistentIndentation = @{
            Enable          = $true
            IndentationSize = 4
            Kind            = 'space'
        }

        PSUseConsistentWhitespace = @{
            Enable                          = $true
            CheckOpenBrace                  = $true
            CheckOpenParen                  = $true
            CheckOperator                   = $true
            CheckSeparator                  = $true
            CheckPipe                       = $true
            CheckPipeForRedundantWhitespace = $true
            CheckParameter                  = $true
        }

        PSAlignAssignmentStatement = @{
            Enable         = $true
            CheckHashtable = $true
        }

        PSAvoidUsingCmdletAliases = @{
            # Allow common shell aliases in interactive scripts but not in modules.
            # Remove this block entirely to enforce strict alias avoidance everywhere.
            AllowedAliases = @()
        }
    }
}
