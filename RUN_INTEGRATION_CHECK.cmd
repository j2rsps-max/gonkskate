@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
    python scripts\run-integration-check.py %*
) else (
    py -3 scripts\run-integration-check.py %*
)
set "GonkExitCode=%ERRORLEVEL%"
echo.
echo Return the GonkSkate-integration-results ZIP under logs\.
pause
exit /b %GonkExitCode%
