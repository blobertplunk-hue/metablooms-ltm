# MetaBlooms GitHub Uploader - PowerShell Launcher
# Run this script to start the uploader application

$ErrorActionPreference = "Stop"

Write-Host "MetaBlooms GitHub Uploader" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan
Write-Host ""

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Check for Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python is not installed or not in PATH!" -ForegroundColor Red
    Write-Host "Please install Python from https://python.org" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Check for Git
try {
    $gitVersion = git --version 2>&1
    Write-Host "Found: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "WARNING: Git is not installed or not in PATH!" -ForegroundColor Yellow
    Write-Host "Git is required for uploading to GitHub." -ForegroundColor Yellow
}

# Check for Git LFS
try {
    $lfsVersion = git lfs version 2>&1
    Write-Host "Found: Git LFS $lfsVersion" -ForegroundColor Green
} catch {
    Write-Host "WARNING: Git LFS is not installed!" -ForegroundColor Yellow
    Write-Host "Git LFS is required for large files (>50MB)" -ForegroundColor Yellow
    Write-Host "Install from: https://git-lfs.github.com" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Starting application..." -ForegroundColor Cyan
Write-Host ""

# Run the uploader
$uploaderPath = Join-Path $ScriptDir "metablooms_uploader.py"
python $uploaderPath

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Application exited with error code: $LASTEXITCODE" -ForegroundColor Red
    Read-Host "Press Enter to exit"
}
