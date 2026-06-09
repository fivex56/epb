@echo off
setlocal
cd /d "%~dp0"

"C:\Program Files (x86)\WinSCP\WinSCP.com" /ini=nul ^
  /log="winscp.log" /loglevel=1 ^
  /script="upload.winscp" ^
  /accept=yes

set ERR=%ERRORLEVEL%
if %ERR% NEQ 0 (
  echo [ERROR] WinSCP завершился с кодом %ERR%. Смотри winscp.log
) else (
  echo [OK] Загрузка завершена.
)
endlocal