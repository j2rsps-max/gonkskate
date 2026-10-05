@echo off
setlocal
cd /d "%~dp0"
echo.
echo ============================================
echo        GonkSkate v0.5.1 First Test
echo ============================================
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\test-all.ps1"
echo.
echo Test script exited with code %ERRORLEVEL%.
echo Logs are in: %~dp0logs
echo.
pause
