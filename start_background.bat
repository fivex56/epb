@echo off
REM ============================================
REM Energy Price Board — Background Runner
REM Запускает бесконечный цикл сбора цен
REM ============================================
setlocal
cd /d "%~dp0"

echo.
echo ============================================
echo  Energy Price Board - Background Service
echo  Started: %date% %time%
echo  Working dir: %cd%
echo ============================================
echo.

REM Проверяем Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found in PATH!
    pause
    exit /b 1
)

REM Запускаем runner в непрерывном режиме
REM --timeout 5 = таймаут на скрапер 5 мин
REM --wait 2   = пауза между скраперами 2 мин
python epb_runner.py --continuous --timeout 5 --wait 2

echo.
echo Runner stopped at %date% %time%
pause
