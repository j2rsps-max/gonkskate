@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
    python scripts\run-thug-file-check.py %*
) else (
    py -3 scripts\run-thug-file-check.py %*
)
set "GonkExitCode=%ERRORLEVEL%"
echo.
echo Return the GonkSkate-thug-files-results ZIP under logs\.
pause
exit /b %GonkExitCode%
