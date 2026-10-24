@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Generator Serial SIPSI
cd /d "%~dp0"
echo.
echo  GENERATOR SERIAL SIPSI (pemilik saja)
echo.
where python >nul 2>&1
if errorlevel 1 (
  echo Python tidak ditemukan
  pause
  exit /b 1
)
python buat_serial.py %*
echo.
pause
