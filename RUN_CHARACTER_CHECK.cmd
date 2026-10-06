@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
    python scripts\run-character-check.py %*
) else (
    py -3 scripts\run-character-check.py %*
)
set "GonkExitCode=%ERRORLEVEL%"
echo.
echo Return the GonkSkate-character-results ZIP under logs\.
pause
exit /b %GonkExitCode%
