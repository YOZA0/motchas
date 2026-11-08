@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ====================================
echo       OUR LITTLE UNIVERSE
 echo    Mustafa and Tosh Tosh
 echo ====================================
echo.
where py >nul 2>nul
if %errorlevel% equ 0 (
  set "PYTHON=py -3"
) else (
  set "PYTHON=python"
)
%PYTHON% --version
if errorlevel 1 (
  echo Python is not installed or not in PATH.
  echo Install Python 3.10 or newer from python.org
  pause
  exit /b 1
)
echo Installing the small Python server dependency...
%PYTHON% -m pip install -r requirements.txt
if errorlevel 1 (
  echo Could not install requirements. Check internet access and try again.
  pause
  exit /b 1
)
echo.
echo Open http://localhost:8080 in your browser.
echo The game server will stop when this window closes.
start "" "http://localhost:8080"
%PYTHON% server.py
pause
