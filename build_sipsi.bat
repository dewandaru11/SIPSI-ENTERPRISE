@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title Build SIPSI.exe + Enterprise + Psikologi

echo.
echo ========================================
echo  BUILD SIPSI.exe
echo  (SIPSI 33 + Enterprise 600 + Psikologi 100)
echo ========================================
echo Folder: %CD%
echo.

REM --- Validasi file wajib ---
set MISSING=0
if not exist "app.py"                ( echo [X] app.py & set MISSING=1 )                else echo [OK] app.py
if not exist "questions_600.json"    ( echo [X] questions_600.json & set MISSING=1 )    else echo [OK] questions_600.json
if not exist "scoring_enterprise.py" ( echo [X] scoring_enterprise.py & set MISSING=1 ) else echo [OK] scoring_enterprise.py
if not exist "license_core.py"       ( echo [X] license_core.py & set MISSING=1 )       else echo [OK] license_core.py
if not exist "static\logo.png"       ( echo [!] static\logo.png opsional - UI tanpa logo ) else echo [OK] static\logo.png
if "%MISSING%"=="1" ( echo. & echo [ERROR] File wajib kurang. & pause & exit /b 1 )

REM --- Cari Python ---
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
  if exist "%LocalAppData%\Programs\Python\Python313\python.exe" set "PYEXE=%LocalAppData%\Programs\Python\Python313\python.exe"
  if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYEXE=%LocalAppData%\Programs\Python\Python312\python.exe"
  if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "PYEXE=%LocalAppData%\Programs\Python\Python311\python.exe"
)
if not defined PYEXE (
  echo [ERROR] Python tidak ditemukan.
  pause & exit /b 1
)
echo Python: %PYEXE%
echo.

echo [1/4] Cek modul Python...
%PYEXE% -c "import flask" 2>nul
if errorlevel 1 (
  echo   Install Flask...
  %PYEXE% -m pip install --quiet flask
)
%PYEXE% -c "import webview" 2>nul
if errorlevel 1 (
  echo   Install pywebview...
  %PYEXE% -m pip install --quiet pywebview
)
%PYEXE% -c "import PyInstaller" 2>nul
if errorlevel 1 (
  echo   Install PyInstaller...
  %PYEXE% -m pip install --quiet pyinstaller
)
echo   Semua modul siap.

echo.
echo [2/4] Tulis SIPSI.spec...
(
echo # -*- mode: python ; coding: utf-8 -*-
echo from PyInstaller.utils.hooks import collect_all
echo.
echo # HANYA data file — JANGAN taruh .py di sini!
echo datas = [
echo     ^('static', 'static'^),
echo     ^('questions_600.json', '.'^),
echo ]
echo.
echo # Modul .py WAJIB di hiddenimports (bukan datas)
echo hiddenimports = [
echo     'flask', 'jinja2', 'werkzeug',
echo     'webview',
echo     'webview.platforms.edgechromium',
echo     'webview.platforms.winforms',
echo     'license_core',
echo     'scoring_enterprise',
echo ]
echo.
echo tmp_ret = collect_all^('webview'^)
echo datas += tmp_ret[0]
echo binaries = tmp_ret[1]
echo hiddenimports += tmp_ret[2]
echo.
echo a = Analysis(
echo     ['app.py'],
echo     pathex=[],
echo     binaries=binaries,
echo     datas=datas,
echo     hiddenimports=hiddenimports,
echo     hookspath=[], hooksconfig={}, runtime_hooks=[],
echo     excludes=[], noarchive=False, optimize=0,
echo )
echo pyz = PYZ(a.pure)
echo exe = EXE(
echo     pyz, a.scripts, a.binaries, a.datas, [],
echo     name='SIPSI',
echo     debug=False, bootloader_ignore_signals=False,
echo     strip=False, upx=False,
echo     upx_exclude=[], runtime_tmpdir=None,
echo     console=False, disable_windowed_traceback=False,
echo     argv_emulation=False, target_arch=None,
echo     codesign_identity=None, entitlements_file=None,
echo )
) > SIPSI.spec
echo   SIPSI.spec tertulis.

echo.
echo [3/4] Bersihkan build lama...
if exist build rd /s /q build
if exist dist  rd /s /q dist

echo.
echo [4/4] Build dengan PyInstaller...
echo Mohon tunggu 1-3 menit.
echo.
%PYEXE% -m PyInstaller --noconfirm SIPSI.spec
if errorlevel 1 (
  echo.
  echo [ERROR] Build GAGAL.
  pause & exit /b 1
)

REM --- Salin file pendamping ke dist ---
if not exist dist mkdir dist
copy /Y questions_600.json dist\ >nul
copy /Y scoring_enterprise.py dist\ >nul
if exist license_core.py copy /Y license_core.py dist\ >nul
if not exist dist\static mkdir dist\static
if exist static\logo.png copy /Y static\logo.png dist\static\ >nul

REM --- SALIN lisensi lama (agar tidak aktivasi ulang) ---
if exist sipsi.lic copy /Y sipsi.lic dist\ >nul
if exist sipsi.lic.sig copy /Y sipsi.lic.sig dist\ >nul

echo.
echo ========================================
echo  SELESAI
echo  EXE: %CD%\dist\SIPSI.exe
echo ========================================
echo.
echo Yang di-bundle:
echo   - SIPSI 33 soal
echo   - Enterprise 600 soal
echo   - Tes Psikologi 100 soal  ^(BARU^)
echo.
echo Langkah selanjutnya:
echo   1. Jalankan dist\SIPSI.exe
echo   2. Jika minta aktivasi, isi serial
echo   3. Klik menu "Tes Psikologi" untuk uji
echo.
pause
endlocal