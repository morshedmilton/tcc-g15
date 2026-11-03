@echo off
setlocal

echo === app (onedir) ===
python -m PyInstaller --noconfirm --clean --windowed --uac-admin --name tcc-g15 ^
  --icon=icons/gaugeIcon.ico ^
  --add-data "icons/gaugeIcon.png;icons" ^
  --add-data "tcc_g15_task.xml;." ^
  --hidden-import PySide6 ^
  --collect-all winrt ^
  src/tcc-g15.py || goto :error

echo === watchdog (onefile, no Qt) ===
python -m PyInstaller --noconfirm --clean --windowed --onefile --name tcc-watchdog ^
  src/tcc-watchdog.py || goto :error

copy /Y dist\tcc-watchdog.exe dist\tcc-g15\tcc-watchdog.exe >nul || goto :error

echo === installer ===
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
%ISCC% installer-inno-config.iss || goto :error

echo === done ===
exit /b 0

:error
echo Failed with error #%errorlevel%.
exit /b %errorlevel%
