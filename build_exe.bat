@echo off
REM Build a standalone Windows executable with PyInstaller.
REM After this finishes you'll find the app in: dist\PoE2CampaignOverlay\
REM The acts\ folder is copied next to the .exe so you can keep editing it.

python -m pip install pyinstaller
pyinstaller --noconfirm --windowed --name "PoE2CampaignOverlay" main.py

echo Copying acts folder next to the executable...
xcopy /E /I /Y acts "dist\PoE2CampaignOverlay\acts"

echo.
echo Build complete. Run: dist\PoE2CampaignOverlay\PoE2CampaignOverlay.exe
pause
