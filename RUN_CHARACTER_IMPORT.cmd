@echo off
call "%~dp0RUN_CHARACTER_CHECK.cmd" --pick-files
exit /b %ERRORLEVEL%
