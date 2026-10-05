@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
    python scripts\gonkskate.py %*
) else (
    py -3 scripts\gonkskate.py %*
)
set "GonkExitCode=%ERRORLEVEL%"
if not "%GonkExitCode%"=="0" (
    echo.
    echo GonkSkate could not finish. Results are saved under logs\.
    echo Python 3 with Tkinter is required. Use the standard python.org Windows installer.
    pause
)
exit /b %GonkExitCode%
