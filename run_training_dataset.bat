@echo off
echo ============================================
echo Building Open Banking Training Dataset
echo ============================================

cd /d C:\Dev\GitHub\OpenBankingHCSTCScorer

python build_training_dataset.py ^
 "C:\Users\Massimo Cristi\OneDrive - Savvy Loan Products Ltd\Tick Tock Loans\Scorecard Project\Open Banking Scorecard\Transaction Reports\JsonExport\**\*.json" ^
 outcomes.csv ^
 training_dataset.csv ^
 6

echo.
echo ============================================
echo Finished. Press any key to close.
echo ============================================
pause
