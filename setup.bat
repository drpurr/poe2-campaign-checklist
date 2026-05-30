@echo off
REM One-time setup: installs the Python dependency (PyQt6).
echo Installing dependencies for PoE2 Campaign Overlay...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo Done. You can now run the app with run.bat
pause
