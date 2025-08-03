@echo off
setlocal

:: ——————————————————————————————————————————————
:: 0. Jump into the script’s own folder (avoids landing in System32)
:: ——————————————————————————————————————————————
pushd "%~dp0"

:: ——————————————————————————————————————————————
:: 1. Ensure script is running as admin (needed for installations)
:: ——————————————————————————————————————————————
net session >nul 2>&1
if errorlevel 1 (
    echo This script must be run as Administrator.
    pause
    exit /b 1
)

:: ——————————————————————————————————————————————
:: 2. Check for Python 3.12 via the Python Launcher (py)
:: ——————————————————————————————————————————————
echo Checking for Python 3.13...
py -3.13 --version >nul 2>&1
if errorlevel 1 (
    echo Python 3.13 not found. Installing now...

    :: 2a. Prefer winget if available
    where winget >nul 2>&1
    if not errorlevel 1 (
        echo Installing Python 3.13 with winget...
        winget install --id Python.Python.3.13 -e --source winget --accept-package-agreements --silent
    ) else (
        :: 2b. Fallback: download official installer & silent-install
        echo Downloading Python 3.13 installer...
        powershell -Command "Invoke-WebRequest `
            -Uri 'https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe' `
            -OutFile '%TEMP%\python313.exe'"

        echo Running silent installer...
        start /wait "" "%TEMP%\python313.exe" ^
            /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1
    )

    :: Re-verify
    echo Verifying Python 3.13 install...
    py -3.13 --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python 3.13 installation failed.
        pause
        exit /b 1
    )
)

:: ——————————————————————————————————————————————
:: 3. Remove existing venv if wrong Python version
:: ——————————————————————————————————————————————
if exist "venv" (
    echo Found existing virtual environment. Checking Python version...
    "venv\Scripts\python.exe" --version > "%TEMP%\venv_version.txt" 2>&1
    findstr /r /c:"Python 3\.13\." "%TEMP%\venv_version.txt" >nul
    if errorlevel 1 (
        echo Existing venv is not Python 3.12. Removing it...
        rmdir /s /q "venv"
    )
)

:: ——————————————————————————————————————————————
:: 4. Create fresh venv with Python 3.12
:: ——————————————————————————————————————————————
if not exist "venv" (
    echo Creating virtual environment using Python 3.13...
    py -3.13 -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create venv with Python 3.13.
        pause
        exit /b 1
    )
)

:: ——————————————————————————————————————————————
:: 5. Activate the venv and lock to its interpreter
:: ——————————————————————————————————————————————
echo Activating virtual environment...
call "%~dp0venv\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: venv activation failed.
    pause
    exit /b 1
)

set "VENV_PY=%~dp0venv\Scripts\python.exe"

:: ——————————————————————————————————————————————
:: 6. Upgrade pip, install deps, run build
:: ——————————————————————————————————————————————
echo Upgrading pip...
"%VENV_PY%" -m pip install --upgrade pip

if exist "requirements.txt" (
    echo Installing dependencies from requirements.txt...
    "%VENV_PY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Dependency installation failed.
        pause
        exit /b 1
    )
) else (
    echo Warning: requirements.txt not found. Skipping dependencies.
)

echo Current directory: %CD%
echo HECHO POR RODRIGO DAVID BENITEZ.

echo Running build.py with Python 3.12…
"%VENV_PY%" "%~dp0main.py"
if errorlevel 1 (
    echo ERROR: automatron execution failed.
    pause
    exit /b 1
)

echo.
echo Success! Your script ran under Python 3.13.
echo Press any key to exit…
pause >nul

:: Restore original directory
popd