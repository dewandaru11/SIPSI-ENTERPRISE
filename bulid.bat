@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0."
title Build SIPSI Terbaru

echo ========================================
echo  BUILD SIPSI.exe (Versi Terbaru)
echo  SIPSI 33 + Enterprise 600 + Psikologi 100 + Psikotes
echo ========================================
echo Folder: %CD%
echo.

REM --- Validasi file wajib ---
if not exist "app.py" goto err_app
if not exist "psikotes_module.py" goto err_psikotes
if not exist "questions_600.json" goto err_questions
if not exist "scoring_enterprise.py" goto err_scoring
if not exist "license_core.py" goto err_license
if not exist "static" goto err_static

echo [1/5] Cek modul Python...
python -c "import flask" 2>nul
if errorlevel 1 (
    echo        Install Flask...
    python -m pip install --quiet flask
)
python -c "import webview" 2>nul
if errorlevel 1 (
    echo        Install pywebview...
    python -m pip install --quiet pywebview
)
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo        Install PyInstaller...
    python -m pip install --quiet pyinstaller
)
echo        Modul siap.

echo.
echo [2/5] Bersihkan build lama...
if exist build rd /s /q build
if exist dist rd /s /q dist
if exist SIPSI.spec del /f /q SIPSI.spec
echo        Bersih.

echo.
echo [3/5] Build dengan PyInstaller...
echo        Mohon tunggu 1-3 menit, jangan tutup jendela ini.
echo.

python -m PyInstaller --noconfirm --clean --onefile --windowed --name SIPSI --add-data "static;static" --add-data "questions_600.json;." --hidden-import flask --hidden-import jinja2 --hidden-import werkzeug --hidden-import license_core --hidden-import scoring_enterprise --hidden-import psikotes_module --collect-all webview app.py

if errorlevel 1 goto err_build

echo.
echo [4/5] Salin file pendamping...
copy /Y questions_600.json dist\ >nul
copy /Y scoring_enterprise.py dist\ >nul
copy /Y license_core.py dist\ >nul
copy /Y psikotes_module.py dist\ >nul

echo        Menyalin folder static & gambar...
xcopy /E /I /Y static dist\static >nul

if exist sipsi.lic copy /Y sipsi.lic dist\ >nul
if exist sipsi.lic.sig copy /Y sipsi.lic.sig dist\ >nul
echo        File pendamping disalin.

echo.
echo [5/5] Verifikasi hasil...
if not exist dist\SIPSI.exe goto err_nofile
for %%F in (dist\SIPSI.exe) do echo        Size: %%~zF bytes

echo.
echo ========================================
echo  SELESAI
echo  EXE: %CD%\dist\SIPSI.exe
echo ========================================
echo.
echo Menu aplikasi:
echo   1. Mulai Tes       - 33 soal SIPSI
echo   2. Enterprise      - 600 soal
echo   3. Tes Psikologi   - 100 soal
echo   4. Tes Psikotes    - 121 soal (Wartegg & Pola Gambar)
echo.
echo Langkah berikutnya:
echo   Jalankan: dist\SIPSI.exe
echo   Pastikan folder dist\static\pola berisi gambar 1.png s/d 10.png
echo.
pause
exit /b 0

:err_app
echo [ERROR] app.py tidak ada di folder %CD%
pause
exit /b 1

:err_psikotes
echo [ERROR] psikotes_module.py tidak ada di folder %CD%
pause
exit /b 1

:err_questions
echo [ERROR] questions_600.json tidak ada
pause
exit /b 1

:err_scoring
echo [ERROR] scoring_enterprise.py tidak ada
pause
exit /b 1

:err_license
echo [ERROR] license_core.py tidak ada
pause
exit /b 1

:err_static
echo [ERROR] Folder 'static' tidak ditemukan.
pause
exit /b 1

:err_build
echo.
echo [ERROR] PyInstaller GAGAL.
echo Cek pesan error di atas.
pause
exit /b 1

:err_nofile
echo [ERROR] dist\SIPSI.exe tidak terbentuk.
echo Cek apakah PyInstaller benar-benar sukses.
pause
exit /b 1