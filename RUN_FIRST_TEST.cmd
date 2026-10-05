@echo off
setlocal
cd /d "%~dp0"
echo.
echo ============================================
echo        GonkSkate v0.6.0-dev First Test
echo ============================================
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\test-all.ps1"
set GONK_TEST_EXIT=%ERRORLEVEL%
echo.
echo Test script exited with code %GONK_TEST_EXIT%.
echo Logs are in: %~dp0logs
echo.
pause

exit /b %GONK_TEST_EXIT%
