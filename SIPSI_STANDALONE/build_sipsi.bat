@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Build SIPSI.exe
cd /d "%~dp0"

echo.
echo ========================================
echo  BUILD SIPSI.exe  (Desktop App)
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
  if exist "%LocalAppData%\Programs\Python\Python310\python.exe" set "PYEXE=%LocalAppData%\Programs\Python\Python310\python.exe"
)

if not defined PYEXE (
  echo [ERROR] Python tidak ditemukan.
  echo Install Python 3 dan centang Add python.exe to PATH
  pause
  exit /b 1
)

echo Python: %PYEXE%
echo.

echo [1/4] Install Flask, pywebview, PyInstaller...
%PYEXE% -m pip install --upgrade pip
%PYEXE% -m pip install flask pywebview pyinstaller
if errorlevel 1 (
  echo [ERROR] Gagal install paket.
  pause
  exit /b 1
)

if not exist "app.py" (
  echo [ERROR] app.py tidak ditemukan
  pause
  exit /b 1
)
if not exist "static\logo.png" (
  echo [ERROR] static\logo.png tidak ditemukan
  pause
  exit /b 1
)

echo [2/4] Bersihkan build lama...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist SIPSI.spec del /f /q SIPSI.spec

echo [3/4] Build SIPSI.exe (jendela desktop)...
echo Mohon tunggu 1-3 menit.
echo.

%PYEXE% -m PyInstaller --noconfirm --clean --onefile --windowed --name SIPSI --add-data "static;static" --hidden-import flask --hidden-import jinja2 --hidden-import werkzeug --hidden-import webview --hidden-import webview.platforms.edgechromium --hidden-import webview.platforms.winforms --hidden-import license_core --collect-all webview app.py
if errorlevel 1 (
  echo.
  echo [ERROR] Build gagal.
  pause
  exit /b 1
)

echo [4/4] Siapkan folder release...
if not exist release mkdir release
copy /y "dist\SIPSI.exe" "release\SIPSI.exe" >nul
if not exist "release\static" mkdir "release\static"
copy /y "static\logo.png" "release\static\logo.png" >nul
copy /y "license_core.py" "release\license_core.py" >nul 2>nul

echo.
echo ========================================
echo  SELESAI - Aplikasi Desktop
echo ========================================
echo.
echo  File: release\SIPSI.exe
echo.
echo  Double-klik SIPSI.exe → terbuka JENDELA aplikasi
echo  (bukan tab browser), mirip PIK 33.
echo.
echo  Database: sipsida.db di folder yang sama dengan exe
echo.
pause
endlocal
