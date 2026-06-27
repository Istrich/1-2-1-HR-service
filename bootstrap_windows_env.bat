@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Bootstrap Windows dependencies for HR 1-2-1 Web
REM Installs (if missing):
REM - Python 3.11 (via winget)
REM - ffmpeg (via winget)

cd /d "%~dp0"

echo === HR121 Windows bootstrap ===
echo.

where winget >nul 2>&1
if not %ERRORLEVEL%==0 (
    echo ERROR: winget is not available on this system.
    echo Install App Installer from Microsoft Store and run again.
    exit /b 1
)

set "NEED_PYTHON=1"
where py >nul 2>&1
if %ERRORLEVEL%==0 (
    py -3.11 -V >nul 2>&1
    if %ERRORLEVEL%==0 set "NEED_PYTHON=0"
)

if "%NEED_PYTHON%"=="1" (
    echo [1/3] Installing Python 3.11 via winget...
    winget install -e --id Python.Python.3.11 --accept-source-agreements --accept-package-agreements
    if errorlevel 1 (
        echo ERROR: Failed to install Python 3.11.
        exit /b 1
    )
) else (
    echo [1/3] Python 3.11 already available.
)

set "NEED_FFMPEG=1"
where ffmpeg >nul 2>&1
if %ERRORLEVEL%==0 set "NEED_FFMPEG=0"

if "%NEED_FFMPEG%"=="1" (
    echo [2/3] Installing ffmpeg via winget...
    winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
    if errorlevel 1 (
        echo WARN: Gyan.FFmpeg install failed, trying BtbN build...
        winget install -e --id BtbN.FFmpeg.GPL --accept-source-agreements --accept-package-agreements
        if errorlevel 1 (
            echo ERROR: Failed to install ffmpeg.
            exit /b 1
        )
    )
) else (
    echo [2/3] ffmpeg already available.
)

echo [3/3] Verifying tools...
set "OK=1"
where py >nul 2>&1
if errorlevel 1 set "OK=0"
where ffmpeg >nul 2>&1
if errorlevel 1 set "OK=0"

if "%OK%"=="0" (
    echo.
    echo Dependencies were installed, but current terminal may not see PATH changes yet.
    echo Close this terminal and open a new one, then run:
    echo   pip install -r requirements.txt ^&^& python app.py
    exit /b 0
)

echo.
echo Bootstrap complete. Next steps:
echo   python -m venv .venv
echo   .\.venv\Scripts\Activate.ps1
echo   pip install -r requirements.txt
echo   copy .env.example .env
echo   python app.py
exit /b 0
