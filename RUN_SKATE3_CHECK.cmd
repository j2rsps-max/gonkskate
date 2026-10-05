@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
    python scripts\run-skate3-check.py %*
) else (
    py -3 scripts\run-skate3-check.py %*
)
set "GonkExitCode=%ERRORLEVEL%"
echo.
echo Results are saved under logs\. Return the GonkSkate-skate3-check-results ZIP.
pause
exit /b %GonkExitCode%
