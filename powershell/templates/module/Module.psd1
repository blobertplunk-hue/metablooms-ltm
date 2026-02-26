# Module manifest — Module.psd1
# Generated from PS7 competency package template.
# Replace all <REPLACE> placeholders before shipping.

@{
    # --- Identity ---
    RootModule        = 'Module.psm1'
    ModuleVersion     = '1.0.0'          # Semantic versioning: MAJOR.MINOR.PATCH
    GUID              = '00000000-0000-0000-0000-000000000000'  # Replace: [guid]::NewGuid()
    Author            = '<author>'
    CompanyName       = '<company>'
    Copyright         = '(c) <year> <author>. All rights reserved.'
    Description       = '<one-sentence module description>'

    # --- Compatibility ---
    PowerShellVersion = '7.4'

    # --- Exports: enumerate explicitly — never use '*' in production ---
    FunctionsToExport = @(
        'Get-ItemSafe'
        'Invoke-SafeOperation'
    )
    CmdletsToExport   = @()
    VariablesToExport = @()
    AliasesToExport   = @()

    # --- Dependencies (add only what is actually required) ---
    RequiredModules   = @()

    # --- Metadata ---
    PrivateData = @{
        PSData = @{
            Tags         = @('PS7', 'MetaBlooms', '<REPLACE>')
            ProjectUri   = ''
            ReleaseNotes = 'Initial release.'
        }
    }
}
