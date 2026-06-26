@echo off
REM Sunucuyu baslatir. Tarayicida http://localhost:5005 acilir.
cd /d "%~dp0"
".venv\Scripts\python.exe" server.py
pause
