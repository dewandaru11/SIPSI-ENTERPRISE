# -*- coding: utf-8 -*-
"""
SIPSI — Sistem Skrining Psikometri
=============================================================
Web app Flask + SQLite. Tidak membutuhkan DevExpress / Access / MySQL.
RSUD Damanhuri Barabai · Skrining Psikometri

Fitur:
  - Data peserta
  - 33 soal (Ya / Tidak) per domain
  - Timer opsional
  - Skor per domain + interpretasi ringkas
  - Riwayat & cetak laporan

PENTING:
  Ini versi DEMO/EDUKASI yang disederhanakan.
  Bukan instrumen klinis tervalidasi dan bukan pengganti diagnosis tenaga profesional.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    flash,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
)

import sys

def _app_dir():
    """Folder kerja: di samping .exe jika frozen, else folder app.py."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def _resource_dir():
    """Resource bundel (static) — PyInstaller onefile di _MEIPASS."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = _app_dir()
DB_PATH = os.path.join(BASE_DIR, "sipsida.db")
STATIC_DIR = os.path.join(_resource_dir(), "static")
# fallback: static di samping exe
if not os.path.isdir(STATIC_DIR):
    STATIC_DIR = os.path.join(BASE_DIR, "static")

# --- Lisensi / Serial ---
try:
    from license_core import (
        validate_serial,
        load_license,
        save_license,
        mask_serial,
        get_used_peserta,
        consume_peserta,
    )
except ImportError:
    import sys as _sys
    _mp = getattr(_sys, "_MEIPASS", None)
    if _mp and _mp not in _sys.path:
        _sys.path.insert(0, _mp)
    from license_core import (
        validate_serial,
        load_license,
        save_license,
        mask_serial,
        get_used_peserta,
        consume_peserta,
    )


def _lic():
    return load_license(BASE_DIR)


def _count_peserta():
    """Jumlah baris di DB (statistik saja). Kuota lisensi pakai used_peserta di sipsi.lic."""
    try:
        conn = get_db()
        n = conn.execute("SELECT COUNT(*) FROM peserta").fetchone()[0]
        conn.close()
        return int(n or 0)
    except Exception:
        return 0


def _license_gate(for_new_peserta=False):
    """Gate lisensi. Kuota = used_peserta permanen di sipsi.lic (tidak turun saat hapus riwayat)."""
    lic = _lic()
    if not lic.get("ok"):
        flash(lic.get("error") or "SIPSI belum diaktivasi. Masukkan serial number.", "error")
        return redirect(url_for("aktivasi"))
    used = int(lic.get("used_peserta") or 0)
    max_p = int(lic.get("max_peserta") or 0)
    if for_new_peserta and used >= max_p:
        flash(
            "Kuota peserta habis (%s/%s). Hubungi penyedia serial untuk upgrade." % (used, max_p),
            "error",
        )
        return redirect(url_for("index"))
    if used > max_p:
        flash(
            "Pemakaian (%s) melebihi kuota lisensi (%s). Aktivasi serial dengan kuota lebih besar." % (used, max_p),
            "error",
        )
        return redirect(url_for("aktivasi"))
    return None


app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")
app.secret_key = os.environ.get("SIPSIDA_SECRET", "sipsi-damanhuri-2026")
app.config["PERMANENT_SESSION_LIFETIME"] = 3600

# ---------------------------------------------------------------------------
# Bank soal (33 item, domain skrining sederhana — DEMO)
# Format: (id, domain, teks_soal)
# Skor: Ya = 1, Tidak = 0  (semua item berarah positif ke gejala)
# ---------------------------------------------------------------------------
SOAL = [
    # Domain diselaraskan dengan label chart asli SIPSIDA
    # reverse=True → Ya = sehat (skor 0)
    (1, "Depresi", "Saya kehilangan minat dalam banyak hal ?", False),
    (2, "Fatigue", "Hampir sepanjang waktu saya merasa lelah ?", False),
    (3, "Depresi", "Saya merasa tidak berharga ?", False),
    (4, "Konsentrasi", "Mengambil keputusan adalah suatu yang sulit ?", False),
    (5, "Neurosis", "Segala permasalahan saya mampu saya hadapi terselesaikan dengan baik dan cepat kembali pulih ?", True),
    (6, "Neurosis", "Dari anak-anak sampai remaja saya tidak mengalami kesulitan dalam hidup ?", True),
    (7, "Somatoform", "Saya sering sakit kepala ?", False),
    (8, "Fatigue", "Banyak kegiatan harian yang tidak selesai ?", False),
    (9, "Ansietas", "Tangan dan kaki saya sering gemetar ?", False),
    (10, "Panik", "Saya pernah ketakutan yang luar biasa dan takut akan mati ?", False),
    (11, "Gangguan Tidur", "Saya sering sulit tidur dan mudah terbangun ?", False),
    (12, "Somatoform", "Nafsu makan saya berkurang ?", False),
    (13, "Fatigue", "Beberapa waktu ini saya merasa kurang sehat ?", False),
    (14, "PTSD", "Saya sering mimpi buruk tentang peristiwa luar biasa tersebut ?", False),
    (15, "PTSD", "Saya sering menghindar segala sesuatu yang mengingatkan peristiwa luar biasa tersebut ?", False),
    (16, "Psikosis", "Ada hal yang tidak biasa dalam pikiran saya dan mengganggu ?", False),
    (17, "Neurosis", "Segala potensi dan lingkungan yang saya punya, mampu mengatasi tantangan dan masalah yang ada ?", True),
    (18, "Konsentrasi", "Konsentrasi saya sering terganggu ?", False),
    (19, "Depresi", "Saya merasa kurang bahagia ?", False),
    (20, "Agorafobia", "Saya sering takut sesuatu akan terjadi pada saat sendiri atau di keramaian ?", False),
    (21, "Psikosis", "Saya pernah mendengar suara yang orang lain tidak dapat mendengar ?", False),
    (22, "Depresi", "Saya kesulitan menikmati kegiatan rutin ?", False),
    (23, "Neurosis", "Saya kurang mampu berperan dalam hidup ini ?", False),
    (24, "Panik", "Napas saya sering merasa sesak dan berat ?", False),
    (25, "Ansietas", "Saya mudah merasa takut ?", False),
    (26, "PTSD", "Ada suatu peristiwa luar biasa yang sering seperti merasa terulang kembali ?", False),
    (27, "Ansietas", "Saya sering merasa tegang dan khawatir ?", False),
    (28, "Konsentrasi", "Akhir-akhir ini kemampuan saya kurang optimal dalam semua hal ?", False),
    (29, "Napza", "Saya berani minum alkohol dan menggunakan Narkoba ?", False),
    (30, "Risiko BD", "Saya pernah ada ide untuk bunuh diri ?", False),
    (31, "Psikosis", "Saya yakin ada seseorang ingin mencelakaiku ?", False),
    (32, "Somatoform", "Pencernaan saya sering terganggu ?", False),
    (33, "Konsentrasi", "Kemampuan berpikir saya kurang jernih ?", False),
]

# Urutan domain pada grafik (sesuai cetakan asli)
DOMAIN_ORDER = [
    "Fatigue", "Neurosis", "Depresi", "Ansietas", "Somatoform",
    "Risiko BD", "Gangguan Tidur", "Napza", "Agorafobia", "Panik",
    "Konsentrasi", "Psikosis", "PTSD",
]

DOMAIN_META = {
    "Fatigue": {"max": 3, "rendah": 0, "sedang": 1},
    "Neurosis": {"max": 4, "rendah": 0, "sedang": 1},
    "Depresi": {"max": 4, "rendah": 0, "sedang": 1},
    "Ansietas": {"max": 3, "rendah": 0, "sedang": 1},
    "Somatoform": {"max": 3, "rendah": 0, "sedang": 1},
    "Risiko BD": {"max": 1, "rendah": 0, "sedang": 0},
    "Gangguan Tidur": {"max": 1, "rendah": 0, "sedang": 0},
    "Napza": {"max": 1, "rendah": 0, "sedang": 0},
    "Agorafobia": {"max": 1, "rendah": 0, "sedang": 0},
    "Panik": {"max": 2, "rendah": 0, "sedang": 0},
    "Konsentrasi": {"max": 4, "rendah": 0, "sedang": 1},
    "Psikosis": {"max": 3, "rendah": 0, "sedang": 0},
    "PTSD": {"max": 3, "rendah": 0, "sedang": 1},
}

# Teks deskripsi & saran mirip cetakan asli (muncul jika skor domain >= 1)
DESKRIPSI_MAP = {
    "Fatigue": "Kemungkinan anda merasa tidak sehat dan kurang baik (wellness). Fatigue dan lelah",
    "Neurosis": "Ada indikasi anda mempunyai permasalahan psikis atau mental",
    "Depresi": "Kemungkinan anda mengalami masalah dengan perasaan atau mood (Depresi)",
    "Ansietas": "Mengindikasikan anda mengalami permasalahan dengan pikiran anda (Cemas)",
    "Somatoform": "Kemungkinan anda mengalami keluhan fisik yang berhubungan dengan stres",
    "Risiko BD": "Anda mungkin mengalami perasaan putus asa",
    "Gangguan Tidur": "Kemungkinan anda mengalami gangguan tidur (Insomnia)",
    "Napza": "Ada indikasi penggunaan alkohol atau zat",
    "Agorafobia": "Kemungkinan anda mengalami cemas antisipasi (Agorafobia)",
    "Panik": "Anda pernah mengalami serangan panik",
    "Konsentrasi": "Konsentrasi anda mungkin terganggu",
    "Psikosis": "Anda kemungkinan pernah mengalami kejadian Halusinasi",
    "PTSD": "Kemungkinan anda pernah mengalami kejadian traumatik dan masih mengganggu sampai saat ini (PTSD)",
}

SARAN_MAP = {
    "Fatigue": "Fatigue dan lelah",
    "Neurosis": "Gangguan jiwa ringan sampai sedang (Neurosis)",
    "Depresi": "Gangguan Mood",
    "Ansietas": "Gangguan Kecemasan",
    "Somatoform": "Keluhan somatik terkait stres",
    "Risiko BD": "Perasaan pesimis dan putus asa",
    "Gangguan Tidur": "Gangguan tidur / Insomnia dan Higiene tidur",
    "Napza": "Penggunaan alkohol / zat",
    "Agorafobia": "Agorafobia",
    "Panik": "Serangan Panik",
    "Konsentrasi": "Kemampuan konsentrasi dan menjaga fokus",
    "Psikosis": "Halusinasi dengar",
    "PTSD": "Kejadian Trauma yang pernah dialami",
}

UJIAN_DETIK = 12 * 60  # ~12 menit


def hitung_skor(jawaban_map: dict) -> dict:
    """jawaban_map: {no_soal: Ya/Tidak}. Ya=1 Tidak=0 (selaras PIK_33.exe)."""
    domain_skor = {d: 0 for d in DOMAIN_META}
    for item in SOAL:
        no, domain, _teks, reverse = item[0], item[1], item[2], item[3]
        j = (jawaban_map.get(no) or "").strip().lower()
        # Samakan PIK_33.exe: Ya=1, Tidak=0 (semua Tidak -> semua domain 0)
        skor = 1 if j == "ya" else 0
        domain_skor[domain] = domain_skor.get(domain, 0) + skor

    detail = {}
    for d in DOMAIN_ORDER:
        skor = domain_skor.get(d, 0)
        meta = DOMAIN_META[d]
        if skor <= meta["rendah"]:
            level = "rendah"
        elif skor <= meta["sedang"]:
            level = "sedang"
        else:
            level = "tinggi"
        # Domain kritis: skor 1 sudah perlu perhatian
        if d in ("Risiko BD", "Psikosis", "Napza") and skor >= 1:
            level = "tinggi" if skor >= 2 else "sedang"
        detail[d] = {
            "skor": skor,
            "max": meta["max"],
            "level": level,
        }

    total = sum(v["skor"] for v in detail.values())
    max_total = sum(v["max"] for v in DOMAIN_META.values())
    return {"total": total, "max_total": max_total, "domain": detail}


def buat_deskripsi_saran(hasil: dict) -> tuple:
    """Hasil teks DESKRIPSI dan SARAN mirip cetakan asli."""
    deskripsi = []
    saran = []
    for d in DOMAIN_ORDER:
        v = hasil["domain"].get(d, {})
        if v.get("skor", 0) >= 1:
            if d in DESKRIPSI_MAP:
                deskripsi.append(DESKRIPSI_MAP[d])
            if d in SARAN_MAP:
                saran.append(SARAN_MAP[d])
    # Tambahan khusus Neurosis jika daya tahan rendah (skor reverse tinggi)
    if hasil["domain"].get("Neurosis", {}).get("skor", 0) >= 1:
        extra = "Kurang mampu mengatasi permasalahan dan daya tahan stres rendah"
        if extra not in deskripsi:
            deskripsi.append(extra)
        if "Daya tahan stres" not in saran:
            saran.append("Daya tahan stres")

    # Semua domain 0 (semua jawaban Tidak) — teks sehat seperti app asli
    if not deskripsi:
        deskripsi = [
            "Anda mempunyai kesehatan yang cukup baik, permasalahan yang ada tidak lebih dari permasalahan harian yang mampu diatasi.",
            "Anda mempunyai perkembangan mental emosional yang baik.",
            "Anda saat ini tidak mempunyai permasalahan kesehatan jiwa.",
            "Anda mempunyai mental yang resilience dan berfungsi baik dengan mempunyai faktor pendukung psikosocial yang optimal.",
        ]
        saran = []
    return deskripsi, saran


def buat_ringkasan(hasil: dict) -> str:
    deskripsi, saran = buat_deskripsi_saran(hasil)
    lines = [f"Skor total: {hasil['total']} / {hasil['max_total']}."]
    if hasil["domain"].get("Risiko BD", {}).get("skor", 0) >= 1:
        lines.append(
            "PERHATIAN: Ada indikasi ide terkait menyakiti diri. "
            "Segera hubungi bantuan profesional / IGD."
        )
    if deskripsi:
        lines.append("Indikasi: " + "; ".join(deskripsi[:3]) + ".")
    lines.append(
        "Hasil ini bersifat skrining awal, bukan diagnosis. Konsultasikan dengan profesional bila diperlukan."
    )
    return " ".join(lines)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS peserta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode TEXT UNIQUE,
            nama TEXT NOT NULL,
            jk TEXT,
            tgl_lahir TEXT,
            pendidikan TEXT,
            pekerjaan TEXT,
            alamat TEXT,
            email TEXT,
            no_telp TEXT,
            suku_bangsa TEXT,
            status_perkawinan TEXT,
            mulai_at TEXT,
            selesai_at TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS jawaban (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            peserta_id INTEGER NOT NULL,
            no_soal INTEGER NOT NULL,
            domain TEXT,
            jawaban TEXT NOT NULL,
            skor INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (peserta_id) REFERENCES peserta(id)
        );
        CREATE TABLE IF NOT EXISTS hasil (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            peserta_id INTEGER NOT NULL UNIQUE,
            skor_total INTEGER,
            detail_json TEXT,
            ringkasan TEXT,
            created_at TEXT,
            FOREIGN KEY (peserta_id) REFERENCES peserta(id)
        );
        """
    )
    conn.commit()
    conn.close()


init_db()

def migrate_db():
    """Tambah kolom baru jika DB lama belum punya."""
    conn = get_db()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(peserta)").fetchall()}
    if "suku_bangsa" not in cols:
        conn.execute("ALTER TABLE peserta ADD COLUMN suku_bangsa TEXT")
    if "status_perkawinan" not in cols:
        conn.execute("ALTER TABLE peserta ADD COLUMN status_perkawinan TEXT")
    conn.commit()
    conn.close()


migrate_db()



BASE_CSS = """
:root {
  --bg: #0f172a;
  --panel: #1e293b;
  --border: #334155;
  --text: #e2e8f0;
  --muted: #94a3b8;
  --accent: #38bdf8;
  --accent2: #2563eb;
  --warn: #f59e0b;
  --danger: #ef4444;
  --ok: #10b981;
}
* { box-sizing: border-box; }
body {
  margin: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  background: var(--bg); color: var(--text); min-height: 100vh;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.layout { display: flex; min-height: 100vh; }
.sidebar {
  width: 240px; background: #0b1220; border-right: 1px solid var(--border);
  padding: 18px 14px; flex-shrink: 0;
}
.brand { font-weight: 800; font-size: 1.15rem; letter-spacing: .06em; margin-bottom: 2px; text-align: center; }
.brand span { color: var(--accent); }
.brand-sub { font-size: 0.72rem; color: var(--muted); margin-bottom: 14px; text-align: center; line-height: 1.3; }
.nav-item {
  display: block; padding: 10px 12px; border-radius: 10px; color: var(--text);
  margin-bottom: 4px; font-size: 0.92rem;
}
.nav-item:hover { background: #1e293b; text-decoration: none; }
.nav-item.active { background: #1e3a5f; color: #fff; font-weight: 700; }
.main { flex: 1; padding: 20px 22px 40px; min-width: 0; }
.topbar { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 16px; gap: 12px; }
.topbar h1 { margin: 0; font-size: 1.25rem; }
.topbar .sub { color: var(--muted); font-size: 0.85rem; }
.card {
  background: var(--panel); border: 1px solid var(--border); border-radius: 14px;
  padding: 18px; margin-bottom: 16px;
}
.card h2, .card h3 { margin-top: 0; }
.muted { color: var(--muted); }
.btn {
  display: inline-block; background: var(--accent2); color: #fff; border: none;
  border-radius: 10px; padding: 10px 16px; font-weight: 700; cursor: pointer;
  font-size: 0.9rem; margin: 4px 4px 4px 0;
}
.btn:hover { filter: brightness(1.08); text-decoration: none; color: #fff; }
.btn.secondary { background: #334155; }
.btn.danger { background: var(--danger); }
label { display: block; font-size: 0.8rem; color: var(--muted); margin-bottom: 4px; }
input, select, textarea {
  width: 100%; background: #0b1220; border: 1px solid var(--border); color: var(--text);
  border-radius: 10px; padding: 10px 12px; margin-bottom: 12px; font-size: 0.95rem;
}
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.stat {
  background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 14px;
}
.stat .label { font-size: 0.75rem; color: var(--muted); }
.stat .value { font-size: 1.5rem; font-weight: 800; margin-top: 4px; }
.action-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.action-card {
  background: var(--panel); border: 1px solid var(--border); border-radius: 14px;
  padding: 16px; display: block; color: inherit;
}
.action-card:hover { border-color: #3b82f6; text-decoration: none; }
.action-card .t { font-weight: 800; margin-bottom: 4px; }
.action-card .d { font-size: 0.82rem; color: var(--muted); }
table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
th, td { border-bottom: 1px solid var(--border); padding: 8px 6px; text-align: left; }
th { color: var(--muted); font-weight: 600; font-size: 0.78rem; }
.flash { padding: 10px 12px; border-radius: 10px; margin-bottom: 12px; font-size: 0.9rem; }
.flash.error { background: #450a0a; border: 1px solid #7f1d1d; color: #fecaca; }
.flash.success { background: #052e16; border: 1px solid #14532d; color: #bbf7d0; }
.flash.info { background: #0c4a6e; border: 1px solid #075985; color: #bae6fd; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 99px; font-size: 0.72rem; font-weight: 700; }
.badge.rendah { background: #064e3b; color: #6ee7b7; }
.badge.sedang { background: #78350f; color: #fcd34d; }
.badge.tinggi { background: #7f1d1d; color: #fca5a5; }
.warnbox {
  background: #450a0a; border: 1px solid #b91c1c; color: #fecaca;
  padding: 12px; border-radius: 10px; margin: 10px 0;
}
@media (max-width: 900px) {
  .layout { flex-direction: column; }
  .sidebar { width: 100%; border-right: none; border-bottom: 1px solid var(--border); }
  .stats, .action-grid, .form-grid { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 560px) {
  .stats, .action-grid, .form-grid { grid-template-columns: 1fr; }
}

.stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }
.stat-grid .stat { position: relative; overflow: hidden; }
.stat-grid .stat .icon {
  width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center;
  justify-content: center; color: #fff; font-size: 0.95rem; margin-bottom: 8px;
}
.action-card .ico {
  width: 42px; height: 42px; border-radius: 12px; display: flex; align-items: center;
  justify-content: center; color: #fff; font-size: 1.1rem; margin-bottom: 10px;
}
.grid2, .form-grid-3 {
  display: grid; grid-template-columns: 1fr 1fr; gap: 4px 16px;
}
.form-grid-3 { grid-template-columns: 1fr 1fr 1fr; }
.infobox {
  background: #0c4a6e33; border: 1px solid #075985; color: #bae6fd;
  padding: 12px 14px; border-radius: 12px; font-size: 0.85rem;
}
.form-section-title {
  font-size: 0.8rem; font-weight: 800; color: #38bdf8; letter-spacing: .06em;
  text-transform: uppercase; margin: 16px 0 10px; padding-bottom: 6px;
  border-bottom: 1px solid #334155;
}
.form-section-title:first-child { margin-top: 0; }
.locked-note {
  background: #422006; border: 1px solid #b45309; color: #fde68a;
  padding: 10px 12px; border-radius: 10px; font-size: 0.85rem; margin: 12px auto 0;
  max-width: 480px; text-align: center;
}
.ans-row button:disabled { opacity: 0.55; cursor: not-allowed; filter: grayscale(0.3); }
.checkbox-cell input { width: auto; margin: 0; }
@media (max-width: 900px) {
  .stat-grid, .form-grid-3 { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 560px) {
  .stat-grid, .form-grid-3, .grid2 { grid-template-columns: 1fr; }
}
@media print {
  .sidebar, .topbar, .no-print, .btn { display: none !important; }
  body { background: #fff; color: #000; }
  .main { padding: 0; }
  .card { border: none; background: #fff; }
}

.app-footer {
  text-align: center; padding: 14px 12px 18px; color: #64748b;
  font-size: 0.78rem; border-top: 1px solid var(--border); margin-top: 20px;
}
.app-footer strong { color: #94a3b8; }
.exam-footer {
  text-align: center; margin-top: 8px; color: #94a3b8; font-size: 0.8rem; font-weight: 600;
}
.menu-btn {
  display: none; position: fixed; top: 12px; left: 12px; z-index: 1001;
  width: 42px; height: 42px; border-radius: 12px; border: 1px solid var(--border);
  background: #1e293b; color: #e2e8f0; cursor: pointer; align-items: center;
  justify-content: center; font-size: 1.15rem; box-shadow: 0 4px 14px rgba(0,0,0,.35);
}
.sidebar-overlay {
  display: none; position: fixed; inset: 0; background: rgba(2,6,23,.55); z-index: 999;
}
.sidebar-overlay.show { display: block; }
.sidebar { display: flex; flex-direction: column; }
.brand span {
  background: linear-gradient(90deg, #38bdf8, #818cf8);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.stat-grid .stat, .action-card {
  background: linear-gradient(145deg, #1e293b, #0f172a);
  box-shadow: 0 4px 16px rgba(0,0,0,.18);
}
.action-card:hover { transform: translateY(-3px); border-color: #38bdf8; }
@media (max-width: 900px) {
  .menu-btn { display: flex; }
  .sidebar {
    position: fixed; left: 0; top: 0; bottom: 0; z-index: 1000;
    transform: translateX(-105%); transition: transform .25s ease;
    width: 260px; box-shadow: 8px 0 24px rgba(0,0,0,.4);
    border-right: 1px solid var(--border);
  }
  .sidebar.open { transform: translateX(0); }
  .main { padding: 56px 14px 28px; }
  .layout { flex-direction: row; }
  .exam-meta { grid-template-columns: repeat(2, 1fr) !important; }
}
@media (max-width: 560px) {
  .stat-grid, .form-grid-3, .grid2, .stats, .action-grid, .form-grid { grid-template-columns: 1fr; }
}
@media print {
  .sidebar, .topbar, .no-print, .btn, .menu-btn, .sidebar-overlay, .app-footer { display: none !important; }
  body { background: #fff; color: #000; }
  .main { padding: 0; }
  .card { border: none; background: #fff; }
}


/* ========== MOBILE ONLY — desktop tidak berubah ========== */
@media (max-width: 900px) {
  html { -webkit-text-size-adjust: 100%; }
  body {
    overflow-x: hidden;
    padding-left: env(safe-area-inset-left);
    padding-right: env(safe-area-inset-right);
  }
  .main {
    padding: 56px 12px 28px !important;
    width: 100%;
    max-width: 100vw;
  }
  .topbar h1 { font-size: 1.1rem; }
  .card { padding: 14px 12px; border-radius: 12px; }
  .stat-grid, .action-grid, .stats {
    grid-template-columns: 1fr 1fr !important;
    gap: 10px;
  }
  .stat { padding: 14px 12px; border-radius: 14px; }
  .stat .value { font-size: 1.45rem; }
  .action-card {
    padding: 14px 12px; border-radius: 14px; min-height: 110px;
  }
  .action-card .t { font-size: 0.92rem; }
  .action-card .d { font-size: 0.75rem; line-height: 1.3; }
  .form-grid, .form-grid-3, .grid2, .bio-grid {
    grid-template-columns: 1fr !important;
  }
  input, select, textarea {
    font-size: 16px !important;
    padding: 12px; min-height: 44px;
  }
  .btn {
    min-height: 44px; padding: 12px 16px;
    width: 100%; text-align: center; margin: 6px 0;
  }
  table { font-size: 0.8rem; display: block; overflow-x: auto; }
  .menu-btn {
    top: max(10px, env(safe-area-inset-top));
    left: max(10px, env(safe-area-inset-left));
  }
  .sidebar {
    width: min(280px, 86vw) !important;
    padding-top: env(safe-area-inset-top);
  }
  .print-sheet { padding: 12px 10px !important; }
  .print-sheet h1 { font-size: 0.95rem !important; }
  .bio-grid { grid-template-columns: 1fr !important; font-size: 0.78rem !important; }
  .chart-v { overflow-x: auto; -webkit-overflow-scrolling: touch; }
  .cbar { min-width: 40px !important; }
  .exam-wrap { max-width: 100% !important; }
  .exam-meta { grid-template-columns: 1fr 1fr !important; }
  .exam-nav {
    display: grid !important;
    grid-template-columns: 48px 1fr 48px;
    align-items: center; gap: 6px !important;
  }
  .exam-q { font-size: 1.05rem !important; max-width: 100% !important; }
  .ans-row { max-width: 100% !important; width: 100% !important; }
  .ans-row button { padding: 16px 8px !important; min-height: 52px; }
}
@media (max-width: 560px) {
  .main { padding: 52px 10px 24px !important; }
  .stat-grid, .action-grid, .stats {
    grid-template-columns: 1fr 1fr !important;
    gap: 8px;
  }
}

"""

LAYOUT = """
<!doctype html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover, maximum-scale=1">
  <title>{{ title }} · SIPSI</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <style>{{ css }}</style>
</head>
<body>
  <button type="button" class="menu-btn no-print" id="menuBtn" aria-label="Menu">
    <i class="fas fa-bars"></i>
  </button>
  <div class="sidebar-overlay no-print" id="sidebarOverlay"></div>
  <div class="layout">
    <aside class="sidebar" id="sidebar">
      <div style="text-align:center;margin-bottom:10px">
        <img src="{{ url_for('static', filename='logo.png') }}" alt="SIPSI"
             style="width:72px;height:72px;object-fit:contain;display:block;margin:0 auto 6px">
        <div class="brand">SIP<span>SI</span></div>
        <div class="brand-sub">Sistem Skrining Psikometri</div>
      </div>
      <a class="nav-item {{ 'active' if active=='dashboard' else '' }}" href="{{ url_for('index') }}">
        <i class="fas fa-home" style="width:18px"></i> Dashboard
      </a>
      <a class="nav-item {{ 'active' if active=='mulai' else '' }}" href="{{ url_for('mulai') }}">
        <i class="fas fa-play" style="width:18px"></i> Mulai Tes
      </a>
      <a class="nav-item {{ 'active' if active=='riwayat' else '' }}" href="{{ url_for('riwayat') }}">
        <i class="fas fa-history" style="width:18px"></i> Riwayat
      </a>
      <a class="nav-item" href="{{ url_for('aktivasi') }}">
        <i class="fas fa-key" style="width:18px"></i> Aktivasi
      </a>
      <div style="padding:16px 8px 8px;font-size:0.72rem;color:#64748b;border-top:1px solid #1e293b;margin-top:24px;text-align:center">
        <strong style="color:#94a3b8">BK Tech</strong><br>Support: Adha H.Y
      </div>
    </aside>
    <main class="main">
      <div class="topbar">
        <div>
          <h1>{{ title }}</h1>
          {% if subtitle %}<div class="sub">{{ subtitle }}</div>{% endif %}
        </div>
      </div>
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          {% for cat, msg in messages %}
            <div class="flash {{ cat }}">{{ msg }}</div>
          {% endfor %}
        {% endif %}
      {% endwith %}
      {{ body|safe }}
      <div class="app-footer no-print" style="text-align:center">
        <strong>BK Tech</strong> · Support: Adha H.Y
      </div>
    </main>
  </div>
  <script>
  (function(){
    var btn = document.getElementById('menuBtn');
    var sb = document.getElementById('sidebar');
    var ov = document.getElementById('sidebarOverlay');
    if (!btn || !sb) return;
    function close(){ sb.classList.remove('open'); ov.classList.remove('show'); }
    function toggle(){ sb.classList.toggle('open'); ov.classList.toggle('show'); }
    btn.addEventListener('click', toggle);
    ov.addEventListener('click', close);
    sb.querySelectorAll('a').forEach(function(a){ a.addEventListener('click', close); });
  })();
  </script>
</body>
</html>
"""


def page(title: str, body: str, active: str = "", subtitle: str = ""):
    return render_template_string(
        LAYOUT,
        title=title,
        subtitle=subtitle,
        active=active,
        css=BASE_CSS,
        body=body,
        get_flashed_messages=__import__("flask").get_flashed_messages,
    )


@app.route("/")
def index():
    if not _lic().get("ok"):
        return redirect(url_for("aktivasi"))
    conn = get_db()
    total_peserta = conn.execute("SELECT COUNT(*) FROM peserta").fetchone()[0]
    total_selesai = conn.execute(
        "SELECT COUNT(*) FROM peserta WHERE selesai_at IS NOT NULL AND selesai_at != ''"
    ).fetchone()[0]
    total_hasil = conn.execute("SELECT COUNT(*) FROM hasil").fetchone()[0]
    _L = _lic()
    # Kuota dari counter permanen di sipsi.lic (bukan jumlah baris DB)
    _used = int(_L.get("used_peserta") or 0) if _L.get("ok") else 0
    _maxp = int(_L.get("max_peserta") or 0) if _L.get("ok") else 0
    _kuota_label = ("%s/%s" % (_used, _maxp)) if _L.get("ok") else "—"
    terakhir = conn.execute(
        """
        SELECT p.nama, p.kode, p.selesai_at, h.skor_total
        FROM peserta p LEFT JOIN hasil h ON h.peserta_id = p.id
        ORDER BY p.id DESC LIMIT 5
        """
    ).fetchall()
    conn.close()

    rows = ""
    for r in terakhir:
        skor = r["skor_total"] if r["skor_total"] is not None else "—"
        rows += f"""
        <tr>
          <td class="muted">{r['kode']}</td>
          <td>{r['nama']}</td>
          <td>{r['selesai_at'] or '—'}</td>
          <td><strong>{skor}</strong></td>
        </tr>"""
    if not rows:
        rows = '<tr><td colspan="4" class="muted">Belum ada data peserta</td></tr>'

    body = f"""
    <div class="stat-grid">
      <div class="stat">
        <div class="icon" style="background:linear-gradient(135deg,#2563eb,#1d4ed8)"><i class="fas fa-users"></i></div>
        <div class="label">Total peserta</div>
        <div class="value">{total_peserta}</div>
      </div>
      <div class="stat">
        <div class="icon" style="background:linear-gradient(135deg,#059669,#047857)"><i class="fas fa-check-circle"></i></div>
        <div class="label">Tes selesai</div>
        <div class="value">{total_selesai}</div>
      </div>
      <div class="stat">
        <div class="icon" style="background:linear-gradient(135deg,#7c3aed,#6d28d9)"><i class="fas fa-file-medical"></i></div>
        <div class="label">Laporan hasil</div>
        <div class="value">{total_hasil}</div>
      </div>
      <div class="stat">
        <div class="icon" style="background:linear-gradient(135deg,#b45309,#f59e0b)"><i class="fas fa-key"></i></div>
        <div class="label">Kuota lisensi</div>
        <div class="value">{_kuota_label}</div>
      </div>
    </div>

    <div class="action-grid">
      <a class="action-card" href="{url_for('mulai')}">
        <div class="ico" style="background:linear-gradient(135deg,#2563eb,#06b6d4)"><i class="fas fa-play"></i></div>
        <div class="t">Mulai Tes Baru</div>
        <div class="d">Isi data peserta &amp; kerjakan 33 soal</div>
      </a>
      <a class="action-card" href="{url_for('riwayat')}">
        <div class="ico" style="background:linear-gradient(135deg,#059669,#10b981)"><i class="fas fa-history"></i></div>
        <div class="t">Riwayat Peserta</div>
        <div class="d">Lihat hasil &amp; cetak laporan + grafik</div>
      </a>
      <a class="action-card" href="{url_for('riwayat')}">
        <div class="ico" style="background:linear-gradient(135deg,#7c3aed,#a78bfa)"><i class="fas fa-print"></i></div>
        <div class="t">Cetak Laporan</div>
        <div class="d">Lembar hasil psikometri dengan grafik</div>
      </a>
    </div>

    <div class="card" style="margin-top:18px">
      <h3 style="margin-bottom:8px"><i class="fas fa-clock" style="color:#64748b"></i> Aktivitas terbaru</h3>
      <table>
        <thead><tr><th>Kode</th><th>Nama</th><th>Selesai</th><th>Skor</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>

    <div class="infobox" style="margin-top:8px">
      <strong>Disclaimer:</strong> SIPSI (Sistem Skrining Psikometri). Bukan instrumen klinis resmi / diagnosis.
      Jika dalam krisis, hubungi IGD atau profesional kesehatan jiwa.
    </div>
    """
    return page("Dashboard", body, active="dashboard", subtitle="Ringkasan skrining psikometri SIPSI")



@app.route("/mulai", methods=["GET", "POST"])
def mulai():
    gate = _license_gate(for_new_peserta=(request.method == "POST"))
    if gate is not None:
        return gate
    if request.method == "POST":
        nama = (request.form.get("nama") or "").strip()
        if not nama:
            flash("Nama wajib diisi.", "error")
            return redirect(url_for("mulai"))
        kode = datetime.now().strftime("BKTech-%Y%m%d%H%M%S")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db()
        cur = conn.execute(
            """INSERT INTO peserta
               (kode, nama, jk, tgl_lahir, pendidikan, pekerjaan, alamat, email, no_telp,
                suku_bangsa, status_perkawinan, mulai_at, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                kode,
                nama.upper(),
                (request.form.get("jk") or "").strip().upper(),
                (request.form.get("tgl_lahir") or "").strip(),
                (request.form.get("pendidikan") or "").strip().upper(),
                (request.form.get("pekerjaan") or "").strip().upper(),
                (request.form.get("alamat") or "").strip().upper(),
                (request.form.get("email") or "").strip().lower(),
                (request.form.get("no_telp") or "").strip(),
                (request.form.get("suku_bangsa") or "").strip().upper(),
                (request.form.get("status_perkawinan") or "").strip().upper(),
                now,
                now,
            ),
        )
        conn.commit()
        pid = cur.lastrowid
        conn.close()
        # Kuota permanen: naik 1, tidak turun saat hapus riwayat
        cns = consume_peserta(BASE_DIR)
        if not cns.get("ok"):
            # rollback peserta jika kuota gagal (race / file rusak)
            try:
                conn2 = get_db()
                conn2.execute("DELETE FROM jawaban WHERE peserta_id=?", (pid,))
                conn2.execute("DELETE FROM hasil WHERE peserta_id=?", (pid,))
                conn2.execute("DELETE FROM peserta WHERE id=?", (pid,))
                conn2.commit()
                conn2.close()
            except Exception:
                pass
            flash(cns.get("error") or "Kuota peserta habis.", "error")
            return redirect(url_for("index"))
        session["peserta_id"] = pid
        session["soal_index"] = 0
        import random
        order = [s[0] for s in SOAL]
        random.shuffle(order)
        session["soal_order"] = order
        session["ujian_mulai_ts"] = datetime.now().timestamp()
        session["ujian_detik"] = UJIAN_DETIK
        return redirect(url_for("ujian"))

    body = """
    <div class="card" style="max-width:820px;margin:0 auto">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
        <div style="width:48px;height:48px;border-radius:14px;background:linear-gradient(135deg,#2563eb,#06b6d4);
          display:flex;align-items:center;justify-content:center;color:#fff;font-size:1.3rem">
          <i class="fas fa-user-edit"></i>
        </div>
        <div>
          <h2 style="margin:0">Data Peserta</h2>
          <div class="muted" style="font-size:0.85rem">Lengkapi identitas sebelum memulai skrining Psikometri</div>
        </div>
      </div>

      <form method="post" id="formPeserta">
        <style>
          #formPeserta input[type="text"],
          #formPeserta input:not([type]),
          #formPeserta textarea,
          #formPeserta select {
            text-transform: uppercase;
          }
          #formPeserta input[type="email"] {
            text-transform: none;
          }
        </style>
        <div class="form-section-title">Identitas</div>
        <div class="form-grid-3">
          <div style="grid-column: span 2">
            <label>Nama lengkap *</label>
            <input name="nama" required placeholder="Sesuai identitas">
          </div>
          <div>
            <label>Jenis kelamin</label>
            <select name="jk">
              <option value="">— Pilih —</option>
              <option>Laki - Laki</option>
              <option>Perempuan</option>
            </select>
          </div>
          <div>
            <label>Tanggal lahir</label>
            <input type="date" name="tgl_lahir">
          </div>
          <div>
            <label>Status pernikahan</label>
            <select name="status_perkawinan">
              <option value="">— Pilih —</option>
              <option>Belum Menikah</option>
              <option>Menikah</option>
              <option>Cerai Hidup</option>
              <option>Cerai Mati</option>
            </select>
          </div>
          <div>
            <label>Suku bangsa</label>
            <input name="suku_bangsa" placeholder="Contoh: JAWA, BATAK, SUNDA">
          </div>
        </div>

        <div class="form-section-title">Pendidikan &amp; Pekerjaan</div>
        <div class="grid2">
          <div>
            <label>Pendidikan terakhir</label>
            <select name="pendidikan">
              <option value="">— Pilih —</option>
              <option>SD</option>
              <option>SMP</option>
              <option>SMA / SMK</option>
              <option>Diploma 1</option>
              <option>Diploma 2</option>
              <option>Diploma 3</option>
              <option>S1</option>
              <option>S2</option>
              <option>S3</option>
              <option>Lainnya</option>
            </select>
          </div>
          <div>
            <label>Pekerjaan</label>
            <input name="pekerjaan" placeholder="Contoh: Ibu Rumah Tangga, Karyawan">
          </div>
        </div>

        <div class="form-section-title">Kontak</div>
        <div class="grid2">
          <div>
            <label>No. HP / WA</label>
            <input name="no_telp" placeholder="08xxxxxxxxxx">
          </div>
          <div>
            <label>Email</label>
            <input type="email" name="email" placeholder="opsional">
          </div>
        </div>
        <label>Alamat</label>
        <textarea name="alamat" rows="2" placeholder="Alamat lengkap (opsional)"></textarea>

        <div style="display:flex;gap:10px;align-items:center;margin-top:8px;flex-wrap:wrap">
          <button class="btn" type="submit"><i class="fas fa-play"></i> Mulai Ujian</button>
          <a class="btn secondary" href="/">Batal</a>
          <span class="muted" style="font-size:0.8rem">Urutan 33 soal akan diacak otomatis</span>
        </div>
      </form>
      <script>
      (function(){
        var form = document.getElementById('formPeserta');
        if (!form) return;
        form.querySelectorAll('input, textarea').forEach(function(el){
          if (el.type === 'email' || el.type === 'date' || el.type === 'tel') return;
          el.addEventListener('input', function(){
            var s = el.selectionStart, e = el.selectionEnd;
            el.value = el.value.toUpperCase();
            if (s != null) try { el.setSelectionRange(s, e); } catch(_){}
          });
        });
      })();
      </script>
    </div>
    """
    return page("Data Peserta", body, active="mulai", subtitle="Form identitas sebelum ujian")



@app.route("/ujian", methods=["GET", "POST"])
def ujian():
    gate = _license_gate(False)
    if gate is not None:
        return gate
    pid = session.get("peserta_id")
    if not pid:
        flash("Silakan isi data peserta dulu.", "error")
        return redirect(url_for("mulai"))

    order = session.get("soal_order")
    if not order:
        import random
        order = [s[0] for s in SOAL]
        random.shuffle(order)
        session["soal_order"] = order
        session["ujian_mulai_ts"] = datetime.now().timestamp()
        session["ujian_detik"] = UJIAN_DETIK

    soal_by_id = {s[0]: s for s in SOAL}
    idx = int(session.get("soal_index") or 0)
    if idx < 0:
        idx = 0

    mulai_ts = float(session.get("ujian_mulai_ts") or datetime.now().timestamp())
    total_detik = int(session.get("ujian_detik") or UJIAN_DETIK)
    sisa = int(total_detik - (datetime.now().timestamp() - mulai_ts))
    if sisa < 0:
        sisa = 0

    if request.method == "POST":
        aksi = (request.form.get("aksi") or "jawab").strip()
        if aksi == "goto":
            try:
                target = int(request.form.get("goto_idx") or 0)
            except ValueError:
                target = idx
            if 0 <= target < len(order):
                session["soal_index"] = target
            return redirect(url_for("ujian"))
        if aksi == "prev":
            if idx > 0:
                session["soal_index"] = idx - 1
            return redirect(url_for("ujian"))
        if aksi == "next":
            if idx < len(order) - 1:
                session["soal_index"] = idx + 1
            return redirect(url_for("ujian"))
        if aksi == "selesai":
            return redirect(url_for("selesai"))

        no = int(request.form.get("no_soal") or 0)
        jaw = (request.form.get("jawaban") or "").strip()
        if jaw not in ("Ya", "Tidak"):
            flash("Pilih Ya atau Tidak.", "error")
            return redirect(url_for("ujian"))
        item = soal_by_id.get(no)
        if not item:
            flash("Soal tidak valid.", "error")
            return redirect(url_for("ujian"))
        # Jawaban terkunci: tidak bisa diubah jika sudah pernah dijawab
        conn = get_db()
        existing = conn.execute(
            "SELECT id FROM jawaban WHERE peserta_id=? AND no_soal=?", (pid, no)
        ).fetchone()
        if existing:
            conn.close()
            flash("Soal ini sudah dijawab dan tidak dapat diubah.", "error")
            # pindah ke soal berikutnya yang belum dijawab
            answered = {
                r["no_soal"]
                for r in get_db().execute(
                    "SELECT no_soal FROM jawaban WHERE peserta_id=?", (pid,)
                ).fetchall()
            }
            for i, n in enumerate(order):
                if n not in answered:
                    session["soal_index"] = i
                    return redirect(url_for("ujian"))
            return redirect(url_for("selesai"))
        domain = item[1]
        reverse = item[3]
        skor = 1 if jaw == "Ya" else 0
        conn.execute(
            "INSERT INTO jawaban (peserta_id, no_soal, domain, jawaban, skor) VALUES (?,?,?,?,?)",
            (pid, no, domain, jaw, skor),
        )
        conn.commit()
        conn.close()
        # loncat ke soal berikutnya yang belum dijawab
        answered = set()
        conn2 = get_db()
        answered = {r["no_soal"] for r in conn2.execute(
            "SELECT no_soal FROM jawaban WHERE peserta_id=?", (pid,)
        ).fetchall()}
        conn2.close()
        next_idx = None
        for i, n in enumerate(order):
            if n not in answered:
                next_idx = i
                break
        if next_idx is None:
            return redirect(url_for("selesai"))
        session["soal_index"] = next_idx
        return redirect(url_for("ujian"))

    if idx >= len(order):
        return redirect(url_for("selesai"))

    no = order[idx]
    item = soal_by_id[no]
    domain, teks = item[1], item[2]
    progress = int((idx / len(order)) * 100)
    menit, detik = divmod(sisa, 60)
    jam, menit = divmod(menit, 60)
    sisa_str = f"{jam:02d}:{menit:02d}:{detik:02d}"

    conn = get_db()
    prev = conn.execute(
        "SELECT jawaban FROM jawaban WHERE peserta_id=? AND no_soal=?", (pid, no)
    ).fetchone()
    p = conn.execute("SELECT * FROM peserta WHERE id=?", (pid,)).fetchone()
    answered_rows = conn.execute(
        "SELECT no_soal FROM jawaban WHERE peserta_id=?", (pid,)
    ).fetchall()
    conn.close()
    jaw_prev = prev["jawaban"] if prev else ""
    answered = {r["no_soal"] for r in answered_rows}

    # Panel nomor soal (navigasi)
    grid = ""
    for i, sid in enumerate(order):
        is_cur = i == idx
        is_ans = sid in answered
        if is_cur:
            bg, fg, border = "#2563eb", "#fff", "#93c5fd"
        elif is_ans:
            bg, fg, border = "#1e293b", "#e2e8f0", "#ef4444"
        else:
            bg, fg, border = "#0b1220", "#94a3b8", "#334155"
        dot = '<span style="position:absolute;top:4px;right:5px;width:7px;height:7px;border-radius:50%;background:#ef4444"></span>' if is_ans else ""
        grid += f"""
        <form method="post" style="margin:0;display:inline">
          <input type="hidden" name="aksi" value="goto">
          <input type="hidden" name="goto_idx" value="{i}">
          <button type="submit" style="position:relative;width:44px;height:44px;margin:3px;border-radius:8px;
            border:2px solid {border};background:{bg};color:{fg};font-weight:700;cursor:pointer;font-size:0.9rem">
            {i+1}{dot}
          </button>
        </form>"""

    body = f"""
    <style>
      .exam-wrap {{ max-width: 920px; margin: 0 auto; }}
      .exam-head {{
        background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 45%, #059669 100%);
        color: #fff; border-radius: 14px 14px 0 0;
        padding: 12px 14px 10px; text-align: center;
      }}
      .exam-head img {{
        width: 52px; height: 52px; object-fit: contain;
        display: block; margin: 0 auto 4px;
        filter: drop-shadow(0 2px 4px rgba(0,0,0,.18));
      }}
      .exam-head .exam-title {{
        font-weight: 800; letter-spacing: .08em; font-size: 1.15rem; line-height: 1.2;
        color: #fff;
      }}
      .exam-head .exam-sub {{
        font-weight: 600; font-size: 0.78rem; letter-spacing: .02em;
        margin-top: 2px; color: #ecfdf5;
      }}
      .exam-meta {{
        background: #1e293b; border: 1px solid #334155; border-top: none;
        padding: 10px 12px; display: grid;
        grid-template-columns: repeat(6, 1fr); gap: 8px; font-size: 0.72rem;
      }}
      .exam-meta .k {{ color: #94a3b8; font-size: 0.65rem; }}
      .exam-meta strong {{ color: #f8fafc; }}
      .exam-body {{
        background: #0f172a; border: 1px solid #334155; border-top: none;
        border-radius: 0 0 14px 14px; padding: 28px 18px 22px;
        text-align: center; min-height: 260px;
      }}
      .exam-q {{
        font-size: 1.2rem; font-weight: 700; line-height: 1.5;
        color: #f1f5f9; padding: 18px 12px; max-width: 640px; margin: 0 auto;
      }}
      .exam-nav {{ display: flex; align-items: center; justify-content: space-between; gap: 8px; }}
      .exam-nav .arrow {{
        background: linear-gradient(135deg, #0ea5e9, #059669);
        color: #fff; border: none; border-radius: 20px;
        padding: 10px 16px; font-weight: 800; cursor: pointer;
        box-shadow: 0 2px 8px rgba(14,165,233,.35);
      }}
      .exam-nav .arrow:disabled {{ opacity: .35; cursor: not-allowed; }}
      .ans-row {{
        display: flex; max-width: 480px; margin: 18px auto 0; width: 100%;
      }}
      .ans-row button {{
        flex: 1; border: none; padding: 14px; font-weight: 800; font-size: 1rem;
        cursor: pointer; color: white;
      }}
      .ans-ya {{
        background: linear-gradient(135deg, #0ea5e9, #0284c7);
        border-radius: 10px 0 0 10px;
      }}
      .ans-mid {{
        width: 52px; background: linear-gradient(180deg, #34d399, #059669);
        color: #fff;
        display: flex; align-items: center; justify-content: center; font-weight: 800;
      }}
      .ans-tidak {{
        background: linear-gradient(135deg, #0f766e, #134e4a);
        border-radius: 0 10px 10px 0;
      }}
      .ans-ya.on {{ outline: 3px solid #7dd3fc; }}
      .ans-tidak.on {{ outline: 3px solid #5eead4; }}
      .panel-num {{
        margin-top: 16px; background: #1e293b; border: 1px solid #334155;
        border-radius: 14px; padding: 14px; text-align: center;
      }}
      .panel-num .title {{ color: #facc15; font-weight: 800; margin-bottom: 10px; letter-spacing: .06em; }}
      .panel-hint {{ font-size: 0.75rem; color: #94a3b8; margin-top: 10px; }}
      #sisaWaktu {{ color: #f87171; font-variant-numeric: tabular-nums; }}
    </style>

    <div class="exam-wrap">
      <div class="exam-head">
        <img src="{url_for('static', filename='logo.png')}" alt="SIPSI">
        <div class="exam-title">SIPSI</div>
        <div class="exam-sub">Sistem Skrining Psikometri Kesehatan Jiwa</div>
      </div>
      <div class="exam-meta">
        <div><div class="k">SOAL NO.</div><strong>{idx + 1} / {len(order)}</strong></div>
        <div><div class="k">ID PESERTA</div><strong>{p['kode'] if p else '—'}</strong></div>
        <div><div class="k">Nama Peserta</div><strong>{p['nama'] if p else '—'}</strong></div>
        <div><div class="k">JENIS KELAMIN</div><strong>{(p['jk'] if p else '') or '—'}</strong></div>
        <div><div class="k">TANGGAL UJIAN</div><strong>{(p['mulai_at'] or '')[:10] if p else '—'}</strong></div>
        <div><div class="k">SISA WAKTU</div><strong id="sisaWaktu">{sisa_str}</strong></div>
      </div>
      <div class="exam-body">
        <div class="exam-nav">
          <form method="post" style="margin:0">
            <input type="hidden" name="aksi" value="prev">
            <button class="arrow" type="submit" {"disabled" if idx==0 else ""}>◀</button>
          </form>
          <div class="exam-q">{teks}</div>
          <form method="post" style="margin:0">
            <input type="hidden" name="aksi" value="next">
            <button class="arrow" type="submit" {"disabled" if idx>=len(order)-1 else ""}>▶</button>
          </form>
        </div>
        {('<form method="post" class="ans-row">' if not jaw_prev else '<div class="ans-row">')}
          <input type="hidden" name="no_soal" value="{no}">
          <button class="ans-ya {'on' if jaw_prev=='Ya' else ''}" name="jawaban" value="Ya" type="submit" {'disabled' if jaw_prev else ''}>YA</button>
          <div class="ans-mid">···</div>
          <button class="ans-tidak {'on' if jaw_prev=='Tidak' else ''}" name="jawaban" value="Tidak" type="submit" {'disabled' if jaw_prev else ''}>TIDAK</button>
        {('</form>' if not jaw_prev else '</div>')}
        {('<div class="locked-note">🔒 Soal ini sudah dijawab (<b>' + jaw_prev + '</b>) dan tidak dapat diubah. Gunakan tombol ◀ ▶ untuk pindah soal.</div>') if jaw_prev else ''}
        <div style="height:8px;background:#1e293b;border-radius:99px;overflow:hidden;max-width:480px;margin:16px auto 0;width:100%;border:1px solid #334155">
          <div style="height:100%;width:{progress}%;background:#38bdf8"></div>
        </div>
        <p style="margin:10px 0 0;color:#64748b;font-size:0.8rem">Domain: {domain} · Urutan diacak · Jawaban terkunci setelah dipilih</p>
      </div>

      <div style="margin-top:16px;text-align:center">
        <form method="post" style="display:inline">
          <input type="hidden" name="aksi" value="selesai">
          <button type="submit" style="background:#dc2626;color:#fff;border:none;border-radius:10px;padding:12px 28px;font-weight:800;cursor:pointer">
            SELESAI
          </button>
        </form>
        <div class="panel-hint exam-footer" style="text-align:center;margin-top:10px">BK Tech · Support: Adha H.Y</div>
      </div>
    </div>

    <script>
    (function() {{
      var sisa = {sisa};
      var el = document.getElementById('sisaWaktu');
      function tick() {{
        if (sisa <= 0) {{
          el.textContent = '00:00:00';
          window.location.href = '{url_for("selesai")}';
          return;
        }}
        var t = sisa;
        var h = Math.floor(t/3600); t %= 3600;
        var m = Math.floor(t/60); var s = t % 60;
        el.textContent = String(h).padStart(2,'0')+':'+String(m).padStart(2,'0')+':'+String(s).padStart(2,'0');
        sisa -= 1;
        setTimeout(tick, 1000);
      }}
      tick();
    }})();
    </script>
    """
    return page(f"Soal {idx + 1}", body, active="mulai", subtitle="Ujian psikometri")



@app.route("/selesai")
def selesai():
    gate = _license_gate(False)
    if gate is not None:
        return gate
    pid = session.get("peserta_id")
    if not pid:
        return redirect(url_for("mulai"))

    conn = get_db()
    rows = conn.execute(
        "SELECT no_soal, jawaban FROM jawaban WHERE peserta_id=? ORDER BY no_soal",
        (pid,),
    ).fetchall()
    # Jika waktu habis, tetap hitung dari yang sudah dijawab; jika belum habis wajib lengkap
    mulai_ts = float(session.get("ujian_mulai_ts") or 0)
    total_detik = int(session.get("ujian_detik") or UJIAN_DETIK)
    waktu_habis = mulai_ts and (datetime.now().timestamp() - mulai_ts) >= total_detik
    if len(rows) < len(SOAL) and not waktu_habis:
        flash(f"Masih ada soal belum dijawab ({len(rows)}/{len(SOAL)}).", "error")
        # kembali ke soal pertama yang belum dijawab dalam urutan acak
        answered = {r["no_soal"] for r in rows}
        order = session.get("soal_order") or [s[0] for s in SOAL]
        for i, n in enumerate(order):
            if n not in answered:
                session["soal_index"] = i
                break
        conn.close()
        return redirect(url_for("ujian"))

    jawaban_map = {r["no_soal"]: r["jawaban"] for r in rows}
    hasil = hitung_skor(jawaban_map)
    ringkasan = buat_ringkasan(hasil)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    import json

    conn.execute("UPDATE peserta SET selesai_at=? WHERE id=?", (now, pid))
    conn.execute("DELETE FROM hasil WHERE peserta_id=?", (pid,))
    conn.execute(
        "INSERT INTO hasil (peserta_id, skor_total, detail_json, ringkasan, created_at) VALUES (?,?,?,?,?)",
        (pid, hasil["total"], json.dumps(hasil, ensure_ascii=False), ringkasan, now),
    )
    conn.commit()
    conn.close()
    session.pop("soal_index", None)
    return redirect(url_for("hasil", pid=pid))


@app.route("/hasil/<int:pid>")
def hasil(pid):
    gate = _license_gate(False)
    if gate is not None:
        return gate
    import json

    conn = get_db()
    p = conn.execute("SELECT * FROM peserta WHERE id=?", (pid,)).fetchone()
    h = conn.execute("SELECT * FROM hasil WHERE peserta_id=?", (pid,)).fetchone()
    jaw = conn.execute(
        "SELECT * FROM jawaban WHERE peserta_id=? ORDER BY no_soal",
        (pid,),
    ).fetchall()
    conn.close()
    if not p or not h:
        flash("Data tidak ditemukan.", "error")
        return redirect(url_for("riwayat"))

    detail = json.loads(h["detail_json"])
    deskripsi, saran = buat_deskripsi_saran(detail)

    # --- grafik batang vertikal (skala 0-5 seperti app asli) ---
    chart_bars = ""
    skala = 5
    for d in DOMAIN_ORDER:
        v = detail["domain"].get(d, {"skor": 0, "max": 1})
        skor = int(v["skor"] or 0)
        h_px = int(round(100 * min(skor, skala) / skala)) if skala else 0
        if skor > 0:
            y = 100 - h_px
            ty = max(12, y - 4)
            fill_svg = (
                f'<rect x="8" y="{y}" width="24" height="{h_px}" fill="#0d9488" rx="3"/>'
                f'<text x="20" y="{ty}" text-anchor="middle" font-size="11" font-weight="700" fill="#0f172a">{skor}</text>'
            )
        else:
            fill_svg = (
                '<text x="20" y="96" text-anchor="middle" font-size="10" '
                'font-weight="600" fill="#64748b">0</text>'
            )
        chart_bars += (
            f'<div class="cbar"><div class="cbar-col">'
            f'<svg viewBox="0 0 40 100" width="36" height="110" xmlns="http://www.w3.org/2000/svg">'
            f'<line x1="0" y1="100" x2="40" y2="100" stroke="#94a3b8" stroke-width="1"/>'
            f'{fill_svg}</svg></div>'
            f'<div class="cbar-label">{d}</div></div>'
        )


    deskripsi_html = ""
    if deskripsi:
        deskripsi_html = "<br>".join(deskripsi)
    else:
        deskripsi_html = "Tidak ada indikasi menonjol pada domain yang diukur dalam skrining ini."

    saran_html = ""
    if saran:
        saran_html = (
            "Disarankan anda untuk meningkatkan kesehatan anda dan konsultasi permasalahan pada :<br>"
            + "<br>".join(saran)
        )
    else:
        saran_html = ""  # kosong seperti cetakan asli saat sehat

    risiko = detail["domain"].get("Risiko BD", {})
    warn = ""
    if risiko.get("skor", 0) >= 1:
        warn = """
        <div class="warnbox" style="border:2px solid #dc2626;padding:10px;margin:10px 0;background:#fef2f2;color:#7f1d1d">
          <strong>PERHATIAN:</strong> Terdapat jawaban terkait ide menyakiti diri.
          Segera arahkan ke bantuan profesional / IGD.
        </div>"""

    mulai_jam = (p["mulai_at"] or "")[-8:] if p["mulai_at"] else "—"
    selesai_jam = (p["selesai_at"] or "")[-8:] if p["selesai_at"] else "—"
    tgl_tes = (p["mulai_at"] or "")[:10] if p["mulai_at"] else "—"

    # Tanggal tanda tangan otomatis (hari/bulan/tahun Indonesia)
    HARI_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    BULAN_ID = [
        "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember",
    ]
    ttd_tanggal = "........ ................ 20...."
    try:
        sumber = (p["selesai_at"] or p["mulai_at"] or "") or ""
        dt = None
        if sumber:
            for fmt, n in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d", 10)):
                try:
                    dt = datetime.strptime(sumber[:n], fmt)
                    break
                except ValueError:
                    continue
        if dt is None:
            dt = datetime.now()
        ttd_tanggal = f"{HARI_ID[dt.weekday()]} {dt.day} {BULAN_ID[dt.month]} {dt.year}"
    except Exception:
        dt = datetime.now()
        ttd_tanggal = f"{HARI_ID[dt.weekday()]} {dt.day} {BULAN_ID[dt.month]} {dt.year}"

    body = f"""
    <style>
      .print-sheet {{
        background: #fff; color: #111; border-radius: 8px; padding: 18px 20px;
        border: 1px solid #cbd5e1; max-width: 900px; margin: 0 auto;
      }}
      .print-sheet h1 {{
        text-align: center; font-size: 1.15rem; margin: 0; letter-spacing: .04em;
        font-weight: 800; color: #0f172a;
      }}
      .print-sheet .sub-title {{
        text-align: center; font-size: 0.95rem; font-weight: 700; margin: 2px 0 4px;
      }}
      .print-sheet .kode-big {{
        text-align: center; font-weight: 800; font-size: 1rem; margin-bottom: 12px;
      }}
      .bio-grid {{
        display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 4px 16px;
        font-size: 0.82rem; margin-bottom: 12px; line-height: 1.45;
      }}
      .bio-grid .lab {{ color: #475569; }}
      .chart-v {{
        display: flex; align-items: flex-end; justify-content: space-between;
        gap: 2px; padding: 8px 4px 4px; border: 1px solid #94a3b8;
        border-radius: 4px; background: #f8fafc; margin: 8px 0 14px;
        overflow-x: auto;
      }}
      .cbar {{ flex: 1; min-width: 48px; text-align: center; }}
      .cbar-col {{ display: flex; justify-content: center; }}
      .cbar-label {{
        font-size: 0.58rem; line-height: 1.15; margin-top: 4px;
        color: #0f172a; word-break: break-word; max-width: 56px; margin-left: auto; margin-right: auto;
      }}
      .section-title {{
        font-weight: 800; font-size: 0.9rem; border-bottom: 1px solid #94a3b8;
        padding-bottom: 2px; margin: 12px 0 6px; color: #0f172a;
      }}
      .deskripsi-box, .saran-box {{
        font-size: 0.85rem; line-height: 1.5; color: #0f172a;
      }}
      .legend-note {{
        font-size: 0.7rem; color: #64748b; text-align: right; margin-top: -8px;
      }}
      @media print {{
        body, .main, .sidebar, .topbar {{ background: #fff !important; }}
        .sidebar, .topbar, .no-print, nav, .btn {{ display: none !important; }}
        .print-sheet {{ border: none; padding: 0; max-width: 100%; }}
        .main {{ margin: 0 !important; padding: 0 !important; }}
      }}
    </style>

    <div class="print-sheet">
      <div style="text-align:center;margin-bottom:6px">
        <img src="{url_for('static', filename='logo.png')}" alt="SIPSI"
             style="width:64px;height:64px;object-fit:contain;margin:0 auto 4px;display:block">
      </div>
      <h1>LEMBAR JAWABAN PSIKOMETRI KESEHATAN JIWA</h1>
      <div class="kode-big">{p['kode']}</div>

      <div class="bio-grid">
        <div><span class="lab">TANGGAL TES</span> : {tgl_tes}</div>
        <div><span class="lab">JENIS KELAMIN</span> : {p['jk'] or '—'}</div>
        <div><span class="lab">PENDIDIKAN TERAKHIR</span> : {p['pendidikan'] or '—'}</div>
        <div><span class="lab">NAMA LENGKAP</span> : {p['nama']}</div>
        <div><span class="lab">TGL. LAHIR</span> : {p['tgl_lahir'] or '—'}</div>
        <div><span class="lab">STATUS PERKAWINAN</span> : {(p['status_perkawinan'] if 'status_perkawinan' in p.keys() else None) or '—'}</div>
        <div><span class="lab">NO. HP/WA</span> : {p['no_telp'] or '—'}</div>
        <div><span class="lab">TES DI MULAI PUKUL</span> : {mulai_jam}</div>
        <div><span class="lab">PEKERJAAN</span> : {p['pekerjaan'] or '—'}</div>
        <div><span class="lab">SUKU BANGSA</span> : {(p['suku_bangsa'] if 'suku_bangsa' in p.keys() else None) or '—'}</div>
        <div><span class="lab">SELESAI PUKUL</span> : {selesai_jam}</div>
        <div></div>
      </div>

      {warn}

      <div class="chart-v">
        {chart_bars}
      </div>
      <div class="legend-note">■ SIPSI</div>

      <div class="section-title">DESKRIPSI :</div>
      <div class="deskripsi-box">{deskripsi_html}</div>

      <div class="section-title">SARAN :</div>
      <div class="saran-box">{saran_html}</div>

      <p style="font-size:0.72rem;color:#64748b;margin-top:16px">
        * Hasil skrining awal (SIPSI), bukan diagnosis klinis. Konsultasikan dengan tenaga profesional kesehatan jiwa bila diperlukan.
      </p>

      <div style="margin-top:36px;display:flex;justify-content:flex-end">
        <div style="text-align:center;font-size:0.82rem;line-height:1.55;min-width:240px">
          <div>................................ , {ttd_tanggal}</div>
          <div style="margin-top:4px;color:#475569">Tempat, Hari / Bulan / Tahun</div>
          <div style="height:56px"></div>
          <div style="border-top:1px solid #334155;width:180px;margin:0 auto 4px"></div>
          <div style="font-weight:700">{p['nama']}</div>
        </div>
      </div>
    </div>

    <div style="max-width:900px;margin:16px auto;text-align:center" class="no-print">
      <button class="btn" onclick="window.print()">🖨 Cetak Laporan</button>
      <a class="btn secondary" href="{url_for('riwayat')}">Riwayat</a>
      <a class="btn secondary" href="{url_for('mulai')}">Tes Baru</a>
    </div>
    """
    return page("Hasil Skrining", body, active="riwayat", subtitle="Lembar jawaban psikometri")



@app.route("/riwayat", methods=["GET", "POST"])
def riwayat():
    gate = _license_gate(False)
    if gate is not None:
        return gate
    if request.method == "POST":
        aksi = (request.form.get("aksi") or "").strip()
        if aksi == "hapus":
            ids = request.form.getlist("ids")
            ids = [int(x) for x in ids if str(x).isdigit()]
            if not ids:
                flash("Pilih minimal satu data untuk dihapus.", "error")
            else:
                conn = get_db()
                for pid in ids:
                    conn.execute("DELETE FROM jawaban WHERE peserta_id=?", (pid,))
                    conn.execute("DELETE FROM hasil WHERE peserta_id=?", (pid,))
                    conn.execute("DELETE FROM peserta WHERE id=?", (pid,))
                conn.commit()
                conn.close()
                flash(f"{len(ids)} data riwayat berhasil dihapus.", "success")
            return redirect(url_for("riwayat"))

    conn = get_db()
    rows = conn.execute(
        """
        SELECT p.id, p.kode, p.nama, p.selesai_at, h.skor_total
        FROM peserta p
        LEFT JOIN hasil h ON h.peserta_id = p.id
        ORDER BY p.id DESC LIMIT 200
        """
    ).fetchall()
    conn.close()
    tr = ""
    for r in rows:
        link = url_for("hasil", pid=r["id"]) if r["skor_total"] is not None else "#"
        skor = r["skor_total"] if r["skor_total"] is not None else "—"
        lihat = f'<a href="{link}">Lihat</a>' if r["skor_total"] is not None else "—"
        tr += f"""
        <tr>
          <td class="checkbox-cell"><input type="checkbox" name="ids" value="{r['id']}" class="row-check"></td>
          <td>{r['kode']}</td>
          <td>{r['nama']}</td>
          <td>{r['selesai_at'] or '—'}</td>
          <td>{skor}</td>
          <td>{lihat}</td>
        </tr>"""
    body = f"""
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
        <h2 style="margin:0">Riwayat Peserta</h2>
        <a class="btn" href="{url_for('mulai')}"><i class="fas fa-plus"></i> Tes Baru</a>
      </div>
      <form method="post" id="formRiwayat" onsubmit="return confirm('Hapus data terpilih? Tindakan ini tidak bisa dibatalkan.');">
        <input type="hidden" name="aksi" value="hapus">
        <div style="margin:12px 0;display:flex;gap:10px;align-items:center;flex-wrap:wrap">
          <label style="display:flex;align-items:center;gap:8px;margin:0;color:#e2e8f0;cursor:pointer">
            <input type="checkbox" id="checkAll" style="width:auto;margin:0"> Pilih semua
          </label>
          <button type="submit" class="btn danger"><i class="fas fa-trash"></i> Hapus terpilih</button>
        </div>
        <table>
          <thead>
            <tr>
              <th style="width:36px"></th>
              <th>Kode</th><th>Nama</th><th>Selesai</th><th>Skor</th><th></th>
            </tr>
          </thead>
          <tbody>{tr or '<tr><td colspan="6" class="muted">Belum ada data</td></tr>'}</tbody>
        </table>
      </form>
    </div>
    <script>
    (function() {{
      var all = document.getElementById('checkAll');
      if (!all) return;
      all.addEventListener('change', function() {{
        document.querySelectorAll('.row-check').forEach(function(cb) {{ cb.checked = all.checked; }});
      }});
    }})();
    </script>
    """
    return page("Riwayat Peserta", body, active="riwayat", subtitle="Daftar hasil tes")




@app.route("/aktivasi", methods=["GET", "POST"])
def aktivasi():
    """Halaman aktivasi serial number."""
    lic = _lic()
    # Kuota permanen dari sipsi.lic (bukan COUNT database)
    used = int(lic.get("used_peserta") or 0) if lic.get("ok") else get_used_peserta(BASE_DIR)
    err = ""

    if request.method == "POST":
        serial = (request.form.get("serial") or "").strip()
        chk = validate_serial(serial)
        if not chk.get("ok"):
            err = chk.get("error") or "Serial tidak valid"
        else:
            try:
                save_license(BASE_DIR, serial, chk)
                flash(
                    "Aktivasi berhasil. Kuota peserta: %s." % chk["max_peserta"],
                    "success",
                )
                return redirect(url_for("index"))
            except Exception as e:
                err = "Gagal menyimpan lisensi: %s" % e

    if lic.get("ok"):
        status_html = (
            '<div class="infobox" style="margin-bottom:14px">'
            "<strong>Status:</strong> AKTIF<br>"
            "Serial: <code>%s</code><br>"
            "Kuota terpakai: <strong>%s</strong> / <strong>%s</strong> peserta<br>"
            "<span style='font-size:0.8rem;opacity:.9'>Pemakaian tidak berkurang saat hapus riwayat.</span><br>"
            "Aktivasi: %s"
            "</div>"
        ) % (
            mask_serial(lic.get("serial") or ""),
            used,
            lic.get("max_peserta"),
            lic.get("activated_at") or "—",
        )
    else:
        status_html = (
            '<div class="flash error" style="margin-bottom:14px">'
            "Belum aktif / tidak valid: %s<br>"
            "Data peserta di database: <strong>%s</strong>"
            "</div>"
        ) % (lic.get("error") or "—", _count_peserta())

    err_html = ('<div class="flash error">%s</div>' % err) if err else ""

    body = (
        '<div class="card" style="max-width:520px;margin:0 auto">'
        '<h2 style="margin-top:0"><i class="fas fa-key"></i> Aktivasi SIPSI</h2>'
        '<p class="muted" style="font-size:0.88rem">'
        "Masukkan <strong>serial number</strong> dari penyedia (BK Tech / Adha H.Y). "
        "Tanpa serial valid, aplikasi tidak dapat dipakai."
        "</p>"
        + status_html
        + err_html
        + '<form method="post" autocomplete="off">'
        "<label>Serial Number</label>"
        '<input type="text" name="serial" placeholder="SIPSI-XXXX-XXXX-XXXX-XXXX" '
        'style="text-transform:uppercase;letter-spacing:0.06em;font-weight:700" required>'
        '<button class="btn" type="submit"><i class="fas fa-check"></i> Aktivasi</button> '
        '<a class="btn secondary" href="%s">Kembali</a>'
        "</form>"
        '<p class="muted" style="font-size:0.75rem;margin-top:14px">'
        "File lisensi disimpan di folder aplikasi (<code>sipsi.lic</code>)."
        "</p></div>"
    ) % url_for("index")
    return page("Aktivasi", body, active="", subtitle="Serial number SIPSI")


if __name__ == "__main__":
    import threading
    import socket
    import time

    def _free_port(preferred=5055):
        """Ambil port bebas, utamakan preferred."""
        for port in range(preferred, preferred + 30):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.bind(("127.0.0.1", port))
                s.close()
                return port
            except OSError:
                try:
                    s.close()
                except Exception:
                    pass
        return preferred

    HOST = "127.0.0.1"
    PORT = int(os.environ.get("SIPSI_PORT", str(_free_port(5055))))
    # SIPSI_MODE=web  → buka browser (lama)
    # default         → jendela desktop seperti PIK 33
    MODE = (os.environ.get("SIPSI_MODE") or "desktop").strip().lower()

    def _run_server():
        # threaded=True agar UI webview tidak freeze
        app.run(host=HOST, port=PORT, debug=False, use_reloader=False, threaded=True)

    server = threading.Thread(target=_run_server, daemon=True)
    server.start()

    # Tunggu server siap
    for _ in range(50):
        try:
            s = socket.create_connection((HOST, PORT), timeout=0.2)
            s.close()
            break
        except OSError:
            time.sleep(0.1)

    url = f"http://{HOST}:{PORT}/"
    print("=" * 50)
    print("  SIPSI — Sistem Skrining Psikometri")
    print(f"  Mode : {MODE}")
    print(f"  URL  : {url}")
    print(f"  Data : {DB_PATH}")
    print("=" * 50)

    if MODE in ("web", "browser"):
        import webbrowser
        webbrowser.open(url)
        server.join()
    else:
        # Jendela desktop native (mirip PIK 33) — bukan tab browser
        try:
            import webview
        except ImportError:
            print("[!] pywebview belum terpasang. Fallback ke browser.")
            print("    Install: pip install pywebview")
            import webbrowser
            webbrowser.open(url)
            server.join()
        else:
            icon = os.path.join(STATIC_DIR, "logo.png")
            window = webview.create_window(
                title="SIPSI — Sistem Skrining Psikometri",
                url=url,
                width=1100,
                height=720,
                min_size=(800, 560),
                confirm_close=True,
                text_select=True,
            )
            # gui=None → auto pilih Edge Chromium / WebView2 / MSHTML di Windows
            webview.start(gui=None)
            # saat jendela ditutup, proses keluar (daemon server ikut mati)
