# MetaBlooms Sync - PowerShell Launcher
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  MetaBlooms Sync v2.0" -ForegroundColor Cyan
Write-Host "  ====================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Check Python
try {
    $py = python --version 2>&1
    Write-Host "  [OK] $py" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Python not found!" -ForegroundColor Red
    Write-Host "  Install from: https://python.org" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Git
try {
    $git = git --version 2>&1
    Write-Host "  [OK] $git" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Git not found" -ForegroundColor Yellow
}

# Check optional dependencies
Write-Host ""
Write-Host "  Checking optional features..." -ForegroundColor Gray

$hasTray = python -c "import pystray; print('ok')" 2>&1
if ($hasTray -eq "ok") {
    Write-Host "  [OK] System tray support" -ForegroundColor Green
} else {
    Write-Host "  [--] System tray not available" -ForegroundColor Gray
    Write-Host "       Run: pip install pystray Pillow" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  Starting app..." -ForegroundColor Cyan
Write-Host ""

# Run
python metablooms_sync.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "App exited with error" -ForegroundColor Red
    Read-Host "Press Enter to exit"
}
