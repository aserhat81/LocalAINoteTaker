@echo off
chcp 65001 > nul
title Local AI Note Taker - Setup

echo.
echo ============================================================
echo   Local AI Note Taker by Serhat  ^|  Powered by AMD NPU
echo ============================================================
echo.

python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.11 from:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo Running setup...
echo.
python "%~dp0setup_helper.py"
if errorlevel 1 (
    echo.
    echo Setup failed. See messages above.
    pause
    exit /b 1
)
pause
