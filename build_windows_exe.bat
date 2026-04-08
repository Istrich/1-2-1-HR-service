@echo off
setlocal ENABLEDELAYEDEXPANSION

REM HR 1-2-1 Web desktop build script (Windows)
REM - Creates/uses .venv
REM - Installs desktop dependencies
REM - Builds EXE via PyInstaller

cd /d "%~dp0"

echo [1/5] Detecting Python launcher...
where py >nul 2>&1
if %ERRORLEVEL%==0 (
    set "PY=py -3.11"
) else (
    where python >nul 2>&1
    if %ERRORLEVEL%==0 (
        set "PY=python"
    ) else (
        echo ERROR: Python not found. Install Python 3.11+ first.
        exit /b 1
    )
)

echo [2/5] Creating virtual environment if needed...
if not exist ".venv\Scripts\python.exe" (
    %PY% -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create .venv
        exit /b 1
    )
)

echo [3/5] Installing desktop dependencies...
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate .venv
    exit /b 1
)

python -m pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip
    exit /b 1
)

pip install -r requirements-desktop.txt pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    exit /b 1
)

echo [4/5] Building EXE...
pyinstaller --noconfirm --windowed --onedir --name HR121Desktop --add-data "static;static" --add-data "outputs;outputs" desktop_main.py
if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    exit /b 1
)

echo [5/5] Done.
echo EXE: dist\HR121Desktop\HR121Desktop.exe
echo.
echo Note: Put your .env next to the app working directory.

exit /b 0
