@echo off
REM Build a self-contained Windows .exe — run this ON a Windows machine.
cd /d "%~dp0"

python -m venv .buildvenv
call .buildvenv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

pyinstaller --noconfirm --windowed --onedir ^
  --name "ProductQuantityTracker" ^
  --distpath dist\win ^
  --collect-submodules selenium.webdriver.chrome ^
  --collect-submodules selenium.webdriver.common ^
  app\main.py

call .buildvenv\Scripts\deactivate.bat
echo Done. Executable is at dist\win\ProductQuantityTracker\ProductQuantityTracker.exe
