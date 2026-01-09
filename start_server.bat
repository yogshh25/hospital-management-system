@echo off
echo Stopping any existing Flask servers...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *Flask*" 2>nul
timeout /t 2 /nobreak >nul

echo Starting Flask server...
cd /d %~dp0
python app.py
pause

