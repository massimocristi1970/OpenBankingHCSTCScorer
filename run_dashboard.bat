@echo off
REM Transaction Categorization Review Dashboard Startup Script
REM Created: 2025-12-10 15:57:17 UTC
REM Purpose: Automatically starts the transaction categorization review dashboard

setlocal enabledelayedexpansion

echo ====================================================================
echo Transaction Categorization Review Dashboard
echo ====================================================================
echo.
echo Starting dashboard at %date% %time%
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python or add it to your system PATH
    pause
    exit /b 1
)

REM Check if pip packages are installed
python -m pip list | findstr /i "flask pandas" >nul
if errorlevel 1 (
    echo Installing required dependencies...
    python -m pip install flask pandas openpyxl
    if errorlevel 1 (
        echo Error: Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Start the dashboard application
echo Launching dashboard application...
echo.

REM Look for dashboard script in common locations
if exist "dashboard.py" (
    python dashboard.py
) else if exist "src\dashboard.py" (
    python src\dashboard.py
) else if exist "app\dashboard.py" (
    python app\dashboard.py
) else (
    echo Error: Dashboard script not found
    echo Please ensure dashboard.py exists in the project root, src, or app directory
    pause
    exit /b 1
)

echo.
echo Dashboard has closed
pause
endlocal
