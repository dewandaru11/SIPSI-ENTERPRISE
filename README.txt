============================================================
SIPSI — Aplikasi Desktop
BK Tech · Support: Adha H.Y
============================================================

MODE DEFAULT: JENDELA DESKTOP (bukan browser)

STRUKTUR
--------
SIPSI_STANDALONE/
  app.py
  requirements.txt
  start_sipsi.bat      ← uji desktop (butuh Python)
  build_sipsi.bat      ← buat SIPSI.exe
  static/logo.png
  release/SIPSI.exe    ← hasil build

CARA CEPAT
----------
1. Double-klik start_sipsi.bat
   → muncul jendela aplikasi SIPSI (bukan Chrome/Edge tab)

2. Double-klik build_sipsi.bat
   → hasil: release\SIPSI.exe
   → double-klik exe = jendela desktop

MODE BROWSER (opsional)
-----------------------
set SIPSI_MODE=web
start_sipsi.bat

CATATAN WINDOWS
---------------
- pywebview memakai WebView2 / Edge Chromium di Windows 10/11
- Jika WebView2 belum ada, Windows biasanya mengarahkan install runtime
- Antivirus kadang memblokir hasil PyInstaller (false positive)

DISCLAIMER
----------
Alat skrining, bukan diagnosis klinis.
