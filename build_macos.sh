#!/bin/sh
# ------------------------------
# Builds "dist/NanoVNA Mirror.app" and a zip of it for sharing.
# Run from Terminal on a Mac:   ./build_macos.sh
# The app runs on Macs with the same processor type as the build machine
# (Apple silicon or Intel).
# ------------------------------
set -e
cd "$(dirname "$0")"
python3 -m pip install --upgrade -r requirements.txt pyinstaller
python3 -m PyInstaller --noconfirm --clean --windowed --name "NanoVNA Mirror" nanovna_mirror.py
ditto -c -k --keepParent "dist/NanoVNA Mirror.app" "dist/NanoVNA-Mirror-macOS-$(uname -m).zip"
echo "Done: dist/NanoVNA Mirror.app and dist/NanoVNA-Mirror-macOS-$(uname -m).zip"
# ------------------------------
