@echo off
setlocal
cd /d "%~dp0.."
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0studio.ps1" %*
set ERR=%ERRORLEVEL%
if not %ERR%==0 (
  echo.
  echo Task Studio Launcher failed with exit code %ERR%.
  if /I "%CI%"=="true" exit /b %ERR%
  if /I "%GITHUB_ACTIONS%"=="true" exit /b %ERR%
  if not "%TASK_STUDIO_NO_PAUSE%"=="" exit /b %ERR%
  pause
)
exit /b %ERR%
