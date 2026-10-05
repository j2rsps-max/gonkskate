@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
    python scripts\run-skate3-capture.py %*
) else (
    py -3 scripts\run-skate3-capture.py %*
)
set "GonkExitCode=%ERRORLEVEL%"
echo.
echo Return only the GonkSkate-skate3-capture-results ZIP and playable-results ZIP under logs\.
echo Keep the ISO, memory captures and local-worlds\ on your PC.
pause
exit /b %GonkExitCode%
