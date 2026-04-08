@echo off
setlocal

REM Launch built HR 1-2-1 desktop app on Windows

cd /d "%~dp0"

set "EXE_PATH=dist\HR121Desktop\HR121Desktop.exe"

if not exist "%EXE_PATH%" (
    echo ERROR: "%EXE_PATH%" not found.
    echo Build it first: build_windows_exe.bat
    exit /b 1
)

if not exist ".env" (
    if exist ".env.example" (
        echo WARNING: .env not found. Creating from .env.example...
        copy /Y ".env.example" ".env" >nul
        echo Created .env. Please edit it before first real use.
    ) else (
        echo WARNING: .env not found. App may fail without required variables.
    )
)

echo Starting HR121 Desktop...
start "" "%EXE_PATH%"

exit /b 0
