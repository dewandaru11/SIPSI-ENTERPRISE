============================================================
SISTEM SERIAL SIPSI
============================================================

ANDA (PEMILIK) — buat serial:
  1. Jangan bagikan: buat_serial.py, buat_serial.bat, SECRET
  2. Double-klik buat_serial.bat
     atau: python buat_serial.py 100
     atau: python buat_serial.py 3 --jumlah 5
  3. Salin serial, berikan ke klien

KLIEN — aktivasi:
  1. Buka SIPSI → otomatis ke halaman Aktivasi
  2. Input serial → Aktif
  3. Kuota peserta sesuai serial (mis. 3 atau 100)
  4. Jika kuota habis, tidak bisa Mulai Tes baru

FILE DI FOLDER KLIEN SETELAH AKTIF:
  sipsi.lic
  sipsi.lic.sig

GANTI RAHASIA (opsional):
  Edit SECRET di license_core.py
  lalu generate ulang semua serial.
  (App klien harus pakai license_core.py yang sama.)

