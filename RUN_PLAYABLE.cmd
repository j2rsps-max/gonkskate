@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
    python scripts\run-playable.py %*
) else (
    py -3 scripts\run-playable.py %*
)
set "GonkExitCode=%ERRORLEVEL%"
echo.
echo Results are saved under logs\. Return the GonkSkate-playable-results ZIP.
pause
exit /b %GonkExitCode%
