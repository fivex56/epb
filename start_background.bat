@echo off
REM ============================================
REM Energy Price Board — Background Runner
REM Запускает сбор цен + Twitter авто-постинг
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

REM 1. Запускаем сборщик цен в непрерывном режиме
echo [1/2] Starting price scraper...
start "EPB Scraper" /MIN python epb_runner.py --continuous --timeout 5 --wait 2

REM 2. Запускаем Twitter постер (1 пост/день в случайное время)
echo [2/2] Starting Twitter poster...
start "EPB Twitter" /MIN python twitter_poster.py --loop

echo.
echo Both services started. Close this window to keep them running.
echo Press any key to stop ALL services...
pause >nul

REM Убиваем оба процесса при выходе
taskkill /FI "WINDOWTITLE eq EPB Scraper*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq EPB Twitter*" /F >nul 2>&1
echo All services stopped at %date% %time%
pause
