#!/bin/bash
# Build a self-contained macOS .app — run this ON a Mac.
set -e
cd "$(dirname "$0")"

# macOS's built-in system Python bundles an old Tk 8.5, which has a known bug on
# Big Sur+ that shows a blank white window. Prefer a Homebrew Python (Tk 8.6/9.x)
# if available; fall back to system python3 otherwise.
if command -v /opt/homebrew/bin/python3.12 >/dev/null 2>&1; then
  PYTHON_BIN=/opt/homebrew/bin/python3.12
elif command -v /usr/local/bin/python3 >/dev/null 2>&1; then
  PYTHON_BIN=/usr/local/bin/python3
else
  PYTHON_BIN=python3
  echo "Warning: using system Python — if the built app shows a blank window,"
  echo "run: brew install python-tk@3.12   then re-run this script."
fi

"$PYTHON_BIN" -m venv .buildvenv
source .buildvenv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

pyinstaller --noconfirm --windowed --onedir \
  --name "ProductQuantityTracker" \
  --distpath dist/mac \
  --collect-submodules selenium.webdriver.safari \
  --collect-submodules selenium.webdriver.common \
  --exclude-module webdriver_manager \
  --exclude-module requests \
  --exclude-module charset_normalizer \
  --exclude-module idna \
  app/main.py

deactivate

APP="dist/mac/ProductQuantityTracker.app"
# On macOS the app drives Safari (built into selenium), not Chrome, so none of
# selenium's bundled chromedriver-manager helper binaries (for any OS) are needed.
# Drop them to shrink the app, then re-sign ad-hoc since removing files invalidates
# PyInstaller's signature (Apple Silicon refuses to run unsigned arm64 binaries).
find "$APP" -type f -path "*/webdriver/common/*/selenium-manager*" -delete
codesign --force --deep -s - "$APP"

echo "Done. App bundle is at $APP"
