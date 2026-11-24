#!/bin/sh
# ------------------------------
# Builds dist/nanovna-mirror (single file).
# Needs Tk for Python first, e.g.  sudo apt install python3-tk
# Run:   ./build_linux.sh
# ------------------------------
set -e
cd "$(dirname "$0")"
python3 -m pip install --upgrade -r requirements.txt pyinstaller
python3 -m PyInstaller --noconfirm --clean --onefile --name nanovna-mirror nanovna_mirror.py
echo "Done: dist/nanovna-mirror"
# ------------------------------
