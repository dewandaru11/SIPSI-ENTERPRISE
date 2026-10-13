@echo off
setlocal EnableExtensions
chcp 65001 >nul
title SIPSI Desktop
cd /d "%~dp0"

echo.
echo ========================================
echo  SIPSI Desktop - seperti PIK 33
echo  BK Tech - Support: Adha H.Y
echo ========================================
echo.

set "PYEXE="
where python >nul 2>&1
if not errorlevel 1 (
  for /f "delims=" %%i in ('where python 2^>nul') do (
    if not defined PYEXE set "PYEXE=%%i"
  )
)
if not defined PYEXE (
  where py >nul 2>&1
  if not errorlevel 1 set "PYEXE=py -3"
)
if not defined PYEXE (
  if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYEXE=%LocalAppData%\Programs\Python\Python312\python.exe"
)
if not defined PYEXE (
  if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "PYEXE=%LocalAppData%\Programs\Python\Python311\python.exe"
)

if not defined PYEXE (
  echo [ERROR] Python tidak ditemukan di PATH.
  pause
  exit /b 1
)

echo Python: %PYEXE%
%PYEXE% -c "import flask" 2>nul
if errorlevel 1 (
  echo Install Flask...
  %PYEXE% -m pip install flask
)
%PYEXE% -c "import webview" 2>nul
if errorlevel 1 (
  echo Install pywebview (jendela desktop)...
  %PYEXE% -m pip install pywebview
)

echo.
echo Membuka jendela SIPSI...
echo.
%PYEXE% app.py
pause
endlocal
