@echo off
setlocal enabledelayedexpansion

echo ============================================
echo Building Open Banking Training Dataset
echo ============================================

cd /d "C:\Dev\GitHub\OpenBankingHCSTCScorer" || (
  echo ERROR: Repo folder not found: C:\Dev\GitHub\OpenBankingHCSTCScorer
  pause
  exit /b 1
)

REM --- Prefer OneDrive Business path if available ---
set "ODROOT=%OneDriveCommercial%"
if not defined ODROOT set "ODROOT=%OneDrive%"

REM Fallback: assume standard location under current user profile
if not defined ODROOT set "ODROOT=%USERPROFILE%\OneDrive - Savvy Loan Products Ltd"

set "JSON_ROOT=%ODROOT%\Tick Tock Loans\Scorecard Project\Open Banking Scorecard\Transaction Reports\JsonExport"

if not exist "%JSON_ROOT%" (
  echo ERROR: JSON folder not found:
  echo   "%JSON_ROOT%"
  echo.
  echo HINT: Check OneDrive root on this machine or update the folder name.
  pause
  exit /b 1
)

set "JSON_GLOB=%JSON_ROOT%\**\*.json"

set "OUTCOMES=outcomes.csv"
set "OUTPUT=training_dataset.csv"
set "MONTHS=6"

echo.
echo Step 1: Building training dataset from JSON files...
echo Source: %JSON_ROOT%
echo.

python build_training_dataset.py ^
  "%JSON_GLOB%" ^
  "%OUTCOMES%" ^
  "%OUTPUT%" ^
  %MONTHS%

if %ERRORLEVEL% NEQ 0 (
  echo.
  echo ERROR: Training dataset build failed!
  pause
  exit /b 1
)

echo.
echo ============================================
echo Step 2: Running Backtest Analysis
echo ============================================
echo.

python backtest_scoring.py "%OUTPUT%"

echo.
echo ============================================
echo Complete! 
echo   - Training dataset: %OUTPUT%
echo   - Backtest results shown above
echo ============================================
pause
