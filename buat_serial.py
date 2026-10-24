# -*- coding: utf-8 -*-
"""
GENERATOR SERIAL SIPSI — HANYA UNTUK ANDA (pemilik)
Jangan dibagikan ke klien bersama app.

Cara pakai:
  python buat_serial.py
  python buat_serial.py 100
  python buat_serial.py 3 --jumlah 5
"""
from __future__ import annotations

import argparse
from datetime import datetime
from license_core import generate_serial, validate_serial, SECRET

def main():
    ap = argparse.ArgumentParser(description="Generator serial SIPSI")
    ap.add_argument("max_peserta", type=int, nargs="?", default=None,
                    help="Batas peserta (contoh: 3, 50, 100)")
    ap.add_argument("--jumlah", type=int, default=1, help="Berapa serial dibuat")
    ap.add_argument("--note", type=str, default="", help="Catatan (nama RS, dll)")
    args = ap.parse_args()

    print("=" * 56)
    print("  GENERATOR SERIAL SIPSI")
    print("  BK Tech · Support: Adha H.Y")
    print("=" * 56)
    print()
    print("  WARNING: File ini + SECRET hanya untuk Anda.")
    print("  Jangan kirim buat_serial.py ke klien.")
    print()

    if args.max_peserta is None:
        try:
            raw = input("Batas peserta (contoh 3 / 100): ").strip()
            max_p = int(raw)
        except Exception:
            print("Input tidak valid.")
            return
        try:
            j = input("Jumlah serial [1]: ").strip() or "1"
            jumlah = int(j)
        except Exception:
            jumlah = 1
        note = input("Catatan (opsional): ").strip()
    else:
        max_p = args.max_peserta
        jumlah = args.jumlah
        note = args.note

    if max_p < 1 or max_p > 65535:
        print("max_peserta harus 1..65535")
        return

    print()
    print(f"  Membuat {jumlah} serial | max peserta = {max_p}")
    if note:
        print(f"  Catatan: {note}")
    print("-" * 56)

    lines = []
    for i in range(jumlah):
        serial = generate_serial(max_p, note)
        chk = validate_serial(serial)
        assert chk["ok"] and chk["max_peserta"] == max_p
        print(f"  [{i+1}] {serial}")
        lines.append(f"{serial}\tmax={max_p}\t{note}\t{datetime.now().isoformat(timespec='seconds')}")

    # simpan log
    log_name = f"serial_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(log_name, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("-" * 56)
    print(f"  Log disimpan: {log_name}")
    print()
    print("  Berikan serial ke klien. Mereka input di layar Aktivasi SIPSI.")
    print("=" * 56)

if __name__ == "__main__":
    main()
