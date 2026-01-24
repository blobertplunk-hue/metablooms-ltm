@echo off
title MetaBlooms Sync
cd /d "%~dp0"

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

REM Run the app
python metablooms_sync.py
if errorlevel 1 pause
