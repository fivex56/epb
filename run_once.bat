@echo off
REM ============================================
REM Energy Price Board — Single Run
REM Один цикл: все скраперы → aggregate → ingest → upload
REM ============================================
setlocal
cd /d "%~dp0"

echo.
echo ============================================
echo  Energy Price Board - Single Cycle
echo  Started: %date% %time%
echo ============================================
echo.

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found in PATH!
    pause
    exit /b 1
)

python epb_runner.py --once --timeout 5 --wait 2

echo.
echo Cycle finished at %date% %time%
echo Check status.json for results.
pause
