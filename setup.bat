@echo off
chcp 65001 > nul
title Local AI Suite - Setup

echo.
echo ============================================================
echo   Local AI Suite by Serhat  ^|  FLM / Whisper / Ollama / LM Studio
echo ============================================================
echo.

set "PYTHON_CMD="
set "PYMANAGER=%LOCALAPPDATA%\Microsoft\WindowsApps\pymanager.exe"

echo Checking Python 3.11...

REM 1) Normal python komutu varsa onu dene
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto python_found
)

REM 2) Python Manager'in olusturdugu 3.11 alias'larini dene
python3.11-64 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python3.11-64"
    goto python_found
)

python3.11 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python3.11"
    goto python_found
)

REM 3) En garanti yol: pymanager exec -3.11
if exist "%PYMANAGER%" (
    "%PYMANAGER%" exec -3.11 --version >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_CMD="%PYMANAGER%" exec -3.11"
        goto python_found
    )
)

echo [ERROR] Python 3.11 not found!
echo.
echo Python Manager varsa su komutla kur:
echo "%PYMANAGER%" install 3.11
echo.
echo Ya da Python 3.11'i python.org uzerinden kurarken
echo "Add python.exe to PATH" secenegini isaretle.
echo.
pause
exit /b 1

:python_found
echo Python found:
%PYTHON_CMD% --version
echo.

echo Upgrading pip...
%PYTHON_CMD% -m pip install --upgrade pip
if errorlevel 1 (
    echo.
    echo [WARNING] pip upgrade failed, continuing setup...
    echo.
)

echo Running setup...
echo.
%PYTHON_CMD% "%~dp0setup_helper.py"
if errorlevel 1 (
    echo.
    echo Setup failed. See messages above.
    pause
    exit /b 1
)

echo.
echo Setup completed successfully.
pause
