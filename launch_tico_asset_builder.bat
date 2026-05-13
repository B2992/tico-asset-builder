@echo off
setlocal

echo Tico Asset Builder launcher
echo This only prepares the local project environment and opens the GUI.
echo It does not touch ROM libraries or output folders.
echo.

cd /d "%~dp0" || goto error

set "PYTHON_CMD="
py -3.12 --version >nul 2>&1
if %errorlevel%==0 set "PYTHON_CMD=py -3.12"
if not defined PYTHON_CMD (
  py -3.11 --version >nul 2>&1
  if %errorlevel%==0 set "PYTHON_CMD=py -3.11"
)
if not defined PYTHON_CMD (
  py -3 --version >nul 2>&1
  if %errorlevel%==0 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
  python --version >nul 2>&1
  if %errorlevel%==0 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
  echo Python 3 was not found. Please install Python 3.12 or newer, then try again.
  goto error
)

if not exist ".venv\Scripts\activate.bat" (
  echo Creating local Python environment...
  %PYTHON_CMD% -m venv .venv || goto error
)

call ".venv\Scripts\activate.bat" || goto error

echo Updating installer tools...
python -m pip install --upgrade pip
if errorlevel 1 echo Could not update pip. Continuing with the current pip version.

echo Installing Tico Asset Builder...
python -m pip install -e ".[modern-gui]"
if errorlevel 1 (
  echo Modern GUI dependencies could not be installed. Falling back to the stable GUI install.
  python -m pip install -e . || goto error
)

echo Launching the GUI...
tico-asset-builder-modern-gui
if not errorlevel 1 goto done

echo Modern GUI did not start. Trying the stable GUI...
tico-asset-builder-gui
if not errorlevel 1 goto done

:error
echo.
echo Something went wrong. This launcher did not modify your ROM library.
echo You can inspect this .bat file because it is plain text.
pause
exit /b 1

:done
exit /b 0
