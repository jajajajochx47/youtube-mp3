@echo off
cd /d "%~dp0"
set "VENV_DIR=%~dp0.venv"

if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo Creating Python environment...
  where py >nul 2>nul
  if %ERRORLEVEL% EQU 0 (
    py -3 -m venv "%VENV_DIR%"
  ) else (
    python -m venv "%VENV_DIR%"
  )
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo Could not find Python. Please install Python 3 from https://www.python.org/
  pause
  exit /b 1
)

"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
"%VENV_DIR%\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo Installation complete. Run run.bat to start the app.
pause
