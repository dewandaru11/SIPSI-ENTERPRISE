# -*- coding: utf-8 -*-
"""install_psikotes_v2.py — Installer DIAGNOSTIC untuk app.py SIPSI."""
from pathlib import Path
import py_compile, shutil, sys, re

APP = Path("app.py")
BAK = Path("app.py.bak-sebelum-psikotes")
MODULE = Path("psikotes_module.py")

REGISTER_CODE = '''

# ===================== REGISTER MODUL PSIKOTES =====================
try:
    from psikotes_module import register_psikotes as _register_psikotes
    _register_psikotes(app, {
        "get_db": get_db,
        "page": page,
        "license_gate": _license_gate,
        "consume_peserta": consume_peserta,
        "base_dir": BASE_DIR,
    })
    print("[OK] Psikotes module registered")
except Exception as _e:
    print(f"[WARN] Psikotes module gagal dimuat: {_e}")
# ==================================================================

'''


def preview(src, idx, before=150, after=250):
    s = max(0, idx - before)
    e = min(len(src), idx + after)
    return src[s:e]


def main():
    print("=" * 70)
    print("  INSTALLER MODUL PSIKOTES v2 — DIAGNOSTIC")
    print("=" * 70)
    print(f"  Folder  : {Path.cwd()}")
    print(f"  app.py  : {'ADA (' + str(APP.stat().st_size) + ' bytes)' if APP.exists() else 'TIDAK ADA'}")
    print(f"  modul   : {'ADA (' + str(MODULE.stat().st_size) + ' bytes)' if MODULE.exists() else 'TIDAK ADA'}")
    print()

    if not APP.exists():
        print("[FATAL] app.py tidak ditemukan. Jalankan installer di folder yang sama.")
        return 1
    if not MODULE.exists():
        print("[FATAL] psikotes_module.py tidak ditemukan di folder ini.")
        print("        Salin dulu file psikotes_module.py.")
        return 1

    src = APP.read_text(encoding="utf-8")
    print(f"[1] Baca app.py: {len(src)} karakter")

    # Sudah terpasang?
    if "PSIKOTES_SOAL" in src or "from psikotes_module import" in src:
        print("[SKIP] Modul psikotes sudah terpasang. Tidak melakukan apa-apa.")
        return 0

    # ===== NAV =====
    print()
    print("[2] Mencari marker nav (url_for('psikologi_index'))...")
    nav_pat = re.compile(
        r'(<a\s+class="nav-item[^"]*"[^>]*url_for\(\s*[\'"]psikologi_index[\'"]\s*\)[^>]*>.*?</a>)',
        re.DOTALL,
    )
    m = nav_pat.search(src)
    if not m:
        print("[ERR] Marker nav TIDAK ditemukan.")
        idx = src.find("psikologi_index")
        if idx >= 0:
            print(f"      'psikologi_index' ada di posisi {idx}, tapi pola <a ... url_for('psikologi_index') ...> tidak match.")
            print("      Preview sekitar:")
            print("      " + "-" * 60)
            print(preview(src, idx))
            print("      " + "-" * 60)
            print("      Fallback: sisipkan nav item MANUAL setelah menu 'Tes Psikologi'.")
        else:
            print("      'psikologi_index' TIDAK ada sama sekali di app.py!")
            print("      Cek: apakah app.py ini memang versi dengan menu Tes Psikologi?")
        return 2
    nav_str = m.group(1)
    print(f"[OK] Nav marker ditemukan ({len(nav_str)} char).")

    NAV_ADD = '''
      <a class="nav-item {{ 'active' if active=='psikotes' else '' }}" href="{{ url_for('psikotes') }}">
        <i class="fas fa-clipboard-check" style="width:18px"></i> Tes Psikotes 100
      </a>'''
    src = src.replace(nav_str, nav_str + NAV_ADD, 1)
    print("[OK] Nav item disisipkan.")

    # ===== __MAIN__ =====
    print()
    print("[3] Mencari marker 'if __name__ == \"__main__\":'...")
    main_pat = re.compile(r'(if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:)')
    m2 = main_pat.search(src)
    if not m2:
        print("[ERR] Marker __main__ TIDAK ditemukan.")
        idx = src.find("__main__")
        if idx >= 0:
            print(f"      '__main__' ada di posisi {idx}, tapi pola tidak match.")
            print("      Preview:")
            print("      " + "-" * 60)
            print(repr(preview(src, idx, 100, 150)))
            print("      " + "-" * 60)
        else:
            print("      '__main__' TIDAK ada sama sekali di app.py!")
        return 3
    print(f"[OK] Marker __main__ ditemukan di posisi {m2.start()}.")

    # ===== BACKUP =====
    print()
    print("[4] Backup app.py...")
    if not BAK.exists():
        shutil.copy2(APP, BAK)
        print(f"[OK] Backup: {BAK}")
    else:
        print(f"[OK] Backup sudah ada: {BAK}")

    # ===== SISIP =====
    print()
    print("[5] Sisip kode registrasi sebelum __main__...")
    src = src[:m2.start()] + REGISTER_CODE + src[m2.start():]
    APP.write_text(src, encoding="utf-8")
    print(f"[OK] app.py ditulis ulang: {len(src)} karakter.")

    # ===== VERIFIKASI =====
    print()
    print("[6] Verifikasi syntax...")
    try:
        py_compile.compile(str(APP), doraise=True)
        print("[OK] Syntax valid.")
    except Exception as e:
        print(f"[ERR] Syntax invalid: {e}")
        print("[ROLLBACK] Restore dari backup...")
        shutil.copy2(BAK, APP)
        print("[OK] app.py dipulihkan.")
        return 4

    print()
    print("=" * 70)
    print("  SELESAI — Modul Psikotes terpasang.")
    print("=" * 70)
    print("  Jalankan: python app.py")
    print("  Menu: 'Tes Psikotes 100' di sidebar.")
    print(f"  Rollback: Copy-Item {BAK.name} app.py -Force")
    return 0


if __name__ == "__main__":
    sys.exit(main())