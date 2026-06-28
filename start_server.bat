@echo off
REM Starts the FollowLens server. Open http://localhost:5005 in your browser.
cd /d "%~dp0"
".venv\Scripts\python.exe" run.py
pause
