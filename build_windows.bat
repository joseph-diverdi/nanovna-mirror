@echo off
rem ------------------------------
rem Builds dist\NanoVNA-Mirror.exe (single file, no console window).
rem Run from a Command Prompt on Windows:   build_windows.bat
rem ------------------------------
cd /d "%~dp0"
py -m pip install --upgrade -r requirements.txt pyinstaller || exit /b 1
py -m PyInstaller --noconfirm --clean --onefile --windowed --name NanoVNA-Mirror nanovna_mirror.py || exit /b 1
echo Done: dist\NanoVNA-Mirror.exe
rem ------------------------------
