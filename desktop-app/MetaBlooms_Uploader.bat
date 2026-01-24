@echo off
title MetaBlooms GitHub Uploader
echo Starting MetaBlooms GitHub Uploader...

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH!
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

:: Run the uploader
python "%~dp0metablooms_uploader.py"

if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)
