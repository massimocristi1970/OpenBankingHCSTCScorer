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
    REM Start Python in background and open browser after a delay
    start "" python dashboard.py
    timeout /t 3 /nobreak
    start http://localhost:5001
    echo.
    echo ====================================================================
    echo Dashboard is running at http://localhost:5001
    echo Your browser should open automatically in a moment... 
    echo ====================================================================
    echo.
    echo Press Ctrl+C in this window to stop the dashboard
    echo.
    
    REM Keep the window open
    pause
) else if exist "src\dashboard. py" (
    start "" python src\dashboard.py
    timeout /t 3 /nobreak
    start http://localhost:5001
    echo.
    echo ====================================================================
    echo Dashboard is running at http://localhost:5001
    echo Your browser should open automatically in a moment...
    echo ====================================================================
    echo.
    echo Press Ctrl+C in this window to stop the dashboard
    echo.
    
    pause
) else if exist "app\dashboard.py" (
    start "" python app\dashboard.py
    timeout /t 3 /nobreak
    start http://localhost:5001
    echo. 
    echo ====================================================================
    echo Dashboard is running at http://localhost:5001
    echo Your browser should open automatically in a moment...
    echo ====================================================================
    echo. 
    echo Press Ctrl+C in this window to stop the dashboard
    echo.
    
    pause
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