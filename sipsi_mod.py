# -*- coding: utf-8 -*-
"""
sipsi_mod.py - SIPSI (Sistem Skrining Psikometri) sebagai modul SIMPATIK.

Integrasi:
  - Login & permission SIMPATIK (has_perm('sipsi'))
  - DB terpisah: sipsida.db (sejajar app.py)
  - Route prefix: /sipsi/...
  - Logo: static/sipsi/logo.png

Disclaimer: versi demo/edukasi, bukan instrumen klinis resmi.
"""
from __future__ import annotations

import os
import sqlite3
import json
import random
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    Blueprint,
    flash,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
    send_from_directory,
)

# Diisi oleh init_sipsi()
_BASE_DIR = None
_DB_PATH = None
_STATIC_DIR = None
_login_required = None
_has_perm = None
_audit_log = None
_get_sidebar = None
_COMMON_STYLE = None

sipsi_bp = Blueprint("sipsi", __name__, url_prefix="/sipsi")


def _db():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    conn = _db()
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
    cols = {r[1] for r in conn.execute("PRAGMA table_info(peserta)").fetchall()}
    if "suku_bangsa" not in cols:
        conn.execute("ALTER TABLE peserta ADD COLUMN suku_bangsa TEXT")
    if "status_perkawinan" not in cols:
        conn.execute("ALTER TABLE peserta ADD COLUMN status_perkawinan TEXT")
    conn.commit()
    conn.close()


def _require_sipsi(f):
    """Cek login + permission sipsi saat request (bukan saat import)."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        # Cek login SIMPATIK
        if not session.get("logged_in"):
            try:
                return redirect(url_for("login"))
            except Exception:
                return redirect("/login")
        if _has_perm is not None and not _has_perm("sipsi"):
            flash("Anda tidak memiliki izin menu SIPSI.", "error")
            try:
                return redirect(url_for("dashboard"))
            except Exception:
                return redirect("/dashboard")
        return f(*args, **kwargs)
    return wrapped


SOAL = [
    # Domain diselaraskan dengan label chart asli SIPSIDA
    # reverse=True -&gt; Ya = sehat (skor 0)
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

    # Semua domain 0 (semua jawaban Tidak) - teks sehat seperti app asli
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
/* Sembunyikan overlay/loading dari app induk SIMPATIK */
.loading-overlay, .page-loader, .global-loader, #loading, #loader,
[class*="memproses"], [id*="memproses"], [class*="processing"], #simpatik-app-footer {
  display: none !important;
}

@media print {
  .sidebar, .topbar, .no-print, .btn, .menu-btn, .sidebar-overlay, .app-footer, nav,
  .loading-overlay, .page-loader, .global-loader, #loading, #loader, #simpatik-app-footer { display: none !important; }
  body, html { background: #fff !important; color: #000 !important; margin: 0 !important; padding: 0 !important; }
  .layout { display: block !important; }
  .main { padding: 0 !important; margin: 0 !important; width: 100% !important; max-width: 100% !important; }
  .card { border: none !important; background: #fff !important; box-shadow: none !important; }
  @page { size: A4; margin: 12mm 14mm; }
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

/* ========== MOBILE ONLY - desktop tidak berubah ========== */
@media (max-width: 900px) {
  html { -webkit-text-size-adjust: 100%; }
  body {
    overflow-x: hidden;
    /* safe area untuk notch / home indicator */
    padding-left: env(safe-area-inset-left);
    padding-right: env(safe-area-inset-right);
  }
  .main {
    padding: 56px 12px 28px !important;
    width: 100%;
    max-width: 100vw;
  }
  .topbar {
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 12px;
  }
  .topbar h1 { font-size: 1.1rem; line-height: 1.25; }
  .topbar .sub { font-size: 0.78rem; }
  .card {
    padding: 14px 12px;
    border-radius: 12px;
    margin-bottom: 12px;
  }
  .card h2, .card h3 { font-size: 1rem; }
  /* Grid 2 kolom seperti kartu Jaminan SIMPATIK - hanya HP */
  .stat-grid {
    grid-template-columns: 1fr 1fr !important;
    gap: 10px;
  }
  .stat {
    padding: 14px 12px;
    border-radius: 14px;
  }
  .stat .value { font-size: 1.45rem; }
  .stat .label { font-size: 0.72rem; }
  .action-grid {
    grid-template-columns: 1fr 1fr !important;
    gap: 10px;
  }
  .action-card {
    padding: 14px 12px;
    border-radius: 14px;
    min-height: 110px;
  }
  .action-card .t { font-size: 0.92rem; }
  .action-card .d { font-size: 0.75rem; line-height: 1.3; }
  .action-card .ico {
    width: 38px; height: 38px; font-size: 1rem; margin-bottom: 8px;
  }
  /* Jika jumlah kartu ganjil, kartu terakhir full width opsional - biarkan 2-kolom */
  .stats {
    grid-template-columns: 1fr 1fr !important;
    gap: 10px;
  }
  .form-grid, .form-grid-3, .grid2, .bio-grid {
    grid-template-columns: 1fr !important;
    gap: 0 0;
  }
  input, select, textarea {
    font-size: 16px !important; /* cegah zoom iOS */
    padding: 12px 12px;
    min-height: 44px;
  }
  .btn {
    min-height: 44px;
    padding: 12px 16px;
    font-size: 0.95rem;
    width: 100%;
    text-align: center;
    margin: 6px 0;
  }
  .btn.secondary { width: 100%; }
  /* form mulai: tombol side-by-side jadi stack */
  .card form > div[style*="display:flex"] {
    flex-direction: column !important;
    align-items: stretch !important;
  }
  table { font-size: 0.8rem; display: block; overflow-x: auto; -webkit-overflow-scrolling: touch; }
  th, td { padding: 8px 6px; white-space: nowrap; }
  .infobox { font-size: 0.8rem; padding: 10px 12px; }
  .app-footer { font-size: 0.72rem; padding: 12px 8px 20px; }
  .menu-btn {
    top: max(10px, env(safe-area-inset-top));
    left: max(10px, env(safe-area-inset-left));
  }
  .sidebar {
    width: min(280px, 86vw) !important;
    padding-top: env(safe-area-inset-top);
    padding-bottom: env(safe-area-inset-bottom);
  }
  /* hasil / print sheet di HP */
  .print-sheet {
    padding: 12px 10px !important;
    border-radius: 6px;
  }
  .print-sheet h1 { font-size: 0.95rem !important; }
  .print-sheet .kode-big { font-size: 0.9rem !important; }
  .bio-grid {
    grid-template-columns: 1fr !important;
    font-size: 0.78rem !important;
  }
  .chart-v {
    gap: 0 !important;
    padding: 6px 2px !important;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
  .cbar { min-width: 40px !important; }
  .cbar-label { font-size: 0.52rem !important; max-width: 44px !important; }
  .section-title { font-size: 0.85rem !important; }
  .deskripsi-box, .saran-box { font-size: 0.8rem !important; }
}

@media (max-width: 560px) {
  .main { padding: 52px 10px 24px !important; }
  /* tetap 2 kolom di HP kecil - mirip dashboard Jaminan */
  .stat-grid,
  .action-grid,
  .stats {
    grid-template-columns: 1fr 1fr !important;
    gap: 8px;
  }
  .stat-grid .stat { padding: 12px 10px; }
  .stat .value { font-size: 1.3rem; }
  .action-card { padding: 12px 10px; min-height: 100px; }
  .action-card .t { font-size: 0.88rem; }
  .action-card .d { font-size: 0.7rem; }
  .badge { font-size: 0.68rem; }
  /* tombol aksi di riwayat */
  #formRiwayat > div { flex-direction: column !important; align-items: stretch !important; }
}

/* Halaman ujian - mobile only (class di-inline di route ujian) */
@media (max-width: 900px) {
  .exam-wrap { max-width: 100% !important; margin: 0 !important; }
  .exam-head {
    border-radius: 12px 12px 0 0 !important;
    padding: 10px 10px 8px !important;
  }
  .exam-head img { width: 44px !important; height: 44px !important; }
  .exam-head .exam-title { font-size: 1.05rem !important; }
  .exam-head .exam-sub { font-size: 0.7rem !important; }
  .exam-meta {
    grid-template-columns: 1fr 1fr !important;
    gap: 6px 8px !important;
    padding: 8px 10px !important;
    font-size: 0.7rem !important;
  }
  .exam-meta .k { font-size: 0.6rem !important; }
  .exam-body {
    padding: 16px 10px 18px !important;
    min-height: auto !important;
    border-radius: 0 0 12px 12px !important;
  }
  .exam-nav {
    flex-direction: column !important;
    gap: 10px !important;
  }
  .exam-nav .arrow {
    width: 100%;
    max-width: 120px;
    margin: 0 auto;
    padding: 10px 14px !important;
  }
  /* panah di atas & bawah soal: susun ulang visual */
  .exam-nav {
    display: grid !important;
    grid-template-columns: 48px 1fr 48px;
    align-items: center;
    gap: 6px !important;
  }
  .exam-nav .arrow {
    width: 48px;
    max-width: 48px;
    padding: 10px 0 !important;
    border-radius: 12px !important;
  }
  .exam-q {
    font-size: 1.05rem !important;
    padding: 12px 4px !important;
    max-width: 100% !important;
    line-height: 1.45 !important;
  }
  .ans-row {
    max-width: 100% !important;
    margin: 14px 0 0 !important;
    width: 100% !important;
  }
  .ans-row button {
    padding: 16px 8px !important;
    font-size: 1rem !important;
    min-height: 52px;
  }
  .ans-mid { width: 40px !important; font-size: 0.85rem; }
  .locked-note {
    max-width: 100% !important;
    font-size: 0.8rem !important;
    margin-top: 10px !important;
  }
  .panel-num {
    margin-top: 12px !important;
    padding: 12px 8px !important;
  }
  .panel-num .title { font-size: 0.85rem; }
  /* tombol SELESAI full width di HP */
  .exam-wrap + div,
  .exam-wrap ~ div {
    padding: 0 4px;
  }
}

@media (max-width: 400px) {
  .exam-meta { grid-template-columns: 1fr 1fr !important; }
  .exam-q { font-size: 0.98rem !important; }
  .cbar { min-width: 36px !important; }
}

@media print {
  .sidebar, .topbar, .no-print, .btn, .menu-btn, .sidebar-overlay, .app-footer, nav,
  .loading-overlay, .page-loader, .global-loader, #loading, #loader, #simpatik-app-footer { display: none !important; }
  body, html { background: #fff !important; color: #000 !important; margin: 0 !important; padding: 0 !important; }
  .layout { display: block !important; }
  .main { padding: 0 !important; margin: 0 !important; width: 100% !important; max-width: 100% !important; }
  .card { border: none !important; background: #fff !important; box-shadow: none !important; }
  @page { size: A4; margin: 12mm 14mm; }
}

"""


LAYOUT = """
<!doctype html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover, maximum-scale=1">
  <title>{{ title }} - SIPSI</title>
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
        <img src="{{ url_for('sipsi.static_logo') }}" alt="SIPSI"
             style="width:72px;height:72px;object-fit:contain;display:block;margin:0 auto 6px">
        <div class="brand">SIP<span>SI</span></div>
        <div class="brand-sub">Sistem Skrining Psikometri</div>
      </div>
      <a class="nav-item {{ 'active' if active=='dashboard' else '' }}" href="{{ url_for('sipsi.index') }}">
        <i class="fas fa-home" style="width:18px"></i> Dashboard
      </a>
      <a class="nav-item {{ 'active' if active=='mulai' else '' }}" href="{{ url_for('sipsi.mulai') }}">
        <i class="fas fa-play" style="width:18px"></i> Mulai Tes
      </a>
      <a class="nav-item {{ 'active' if active=='riwayat' else '' }}" href="{{ url_for('sipsi.riwayat') }}">
        <i class="fas fa-history" style="width:18px"></i> Riwayat
      </a>
      <a class="nav-item" href="/dashboard">
        <i class="fas fa-arrow-left" style="width:18px"></i> Kembali SIMPATIK
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
        <strong>BK Tech</strong> - Support: Adha H.Y
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


def page(title: str, body: str, active: str = "", subtitle: str = ""):
    logo_url = url_for("sipsi.static_logo")
    # inject logo into layout via replace of url_for static
    return render_template_string(
        LAYOUT.replace("{{ url_for('sipsi.static_logo') }}", logo_url)
              .replace('{{ url_for("static", filename="logo.png") }}', logo_url),
        title=title,
        subtitle=subtitle,
        active=active,
        css=BASE_CSS,
        body=body.replace("{{ url_for('sipsi.static_logo') }}", logo_url)
                 .replace('{{ url_for("static", filename="logo.png") }}', logo_url)
                 .replace("{url_for('static', filename='logo.png')}", f'"{logo_url}"')
                 .replace('{url_for("static", filename="logo.png")}', f'"{logo_url}"'),
        get_flashed_messages=__import__("flask").get_flashed_messages,
        url_for=url_for,
    )


def _login_gate(f):
    """Permission + login dicek di request time lewat _require_sipsi."""
    return _require_sipsi(f)


@sipsi_bp.route("/static/logo.png")
def static_logo():
    """Serve logo SIPSI dari folder static/sipsi."""
    d = _STATIC_DIR or os.path.join(_BASE_DIR or ".", "static", "sipsi")
    return send_from_directory(d, "logo.png")


@sipsi_bp.route("/", strict_slashes=False)
@_login_gate
def index():
    conn = _db()
    total_peserta = conn.execute("SELECT COUNT(*) FROM peserta").fetchone()[0]
    total_selesai = conn.execute(
        "SELECT COUNT(*) FROM peserta WHERE selesai_at IS NOT NULL AND selesai_at != ''"
    ).fetchone()[0]
    total_hasil = conn.execute("SELECT COUNT(*) FROM hasil").fetchone()[0]
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
        skor = r["skor_total"] if r["skor_total"] is not None else "-"
        rows += f"""
        <tr>
          <td class="muted">{r['kode']}</td>
          <td>{r['nama']}</td>
          <td>{r['selesai_at'] or '-'}</td>
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
    </div>

    <div class="action-grid">
      <a class="action-card" href="{url_for('sipsi.psikologi_index')}">
        <div class="ico" style="background:linear-gradient(135deg,#ea580c,#f59e0b)"><i class="fas fa-brain"></i></div>
        <div class="t">Tes Psikologi</div>
        <div class="d">Kuesioner refleksi 100 soal pilihan A–E</div>
      </a>
      
      <a class="action-card" href="{url_for('sipsi.mulai')}">
        <div class="ico" style="background:linear-gradient(135deg,#2563eb,#06b6d4)"><i class="fas fa-play"></i></div>
        <div class="t">Mulai Tes Baru</div>
        <div class="d">Isi data peserta &amp; kerjakan 33 soal</div>
      </a>
      <a class="action-card" href="{url_for('sipsi.riwayat')}">
        <div class="ico" style="background:linear-gradient(135deg,#059669,#10b981)"><i class="fas fa-history"></i></div>
        <div class="t">Riwayat Peserta</div>
        <div class="d">Lihat hasil &amp; cetak laporan + grafik</div>
      </a>
      <a class="action-card" href="{url_for('sipsi.riwayat')}">
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


@sipsi_bp.route("/mulai", methods=["GET", "POST"], strict_slashes=False)
@_login_gate
def mulai():
    if request.method == "POST":
        nama = (request.form.get("nama") or "").strip()
        if not nama:
            flash("Nama wajib diisi.", "error")
            return redirect(url_for("sipsi.mulai"))
        kode = datetime.now().strftime("BKTech-%Y%m%d%H%M%S")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = _db()
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
        session["peserta_id"] = pid
        session["soal_index"] = 0
        import random
        order = [s[0] for s in SOAL]
        random.shuffle(order)
        session["soal_order"] = order
        session["ujian_mulai_ts"] = datetime.now().timestamp()
        session["ujian_detik"] = UJIAN_DETIK
        return redirect(url_for("sipsi.ujian"))

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
          #formPeserta textarea {
            text-transform: uppercase;
          }
          #formPeserta select {
            text-transform: none;
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
              <option value="">- Pilih -</option>
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
              <option value="">- Pilih -</option>
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
              <option value="">- Pilih -</option>
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


@sipsi_bp.route("/ujian", methods=["GET", "POST"], strict_slashes=False)
@_login_gate
def ujian():
    pid = session.get("peserta_id")
    if not pid:
        flash("Silakan isi data peserta dulu.", "error")
        return redirect(url_for("sipsi.mulai"))

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
            return redirect(url_for("sipsi.ujian"))
        if aksi == "prev":
            if idx > 0:
                session["soal_index"] = idx - 1
            return redirect(url_for("sipsi.ujian"))
        if aksi == "next":
            if idx < len(order) - 1:
                session["soal_index"] = idx + 1
            return redirect(url_for("sipsi.ujian"))
        if aksi == "selesai":
            return redirect(url_for("sipsi.selesai"))

        no = int(request.form.get("no_soal") or 0)
        jaw = (request.form.get("jawaban") or "").strip()
        if jaw not in ("Ya", "Tidak"):
            flash("Pilih Ya atau Tidak.", "error")
            return redirect(url_for("sipsi.ujian"))
        item = soal_by_id.get(no)
        if not item:
            flash("Soal tidak valid.", "error")
            return redirect(url_for("sipsi.ujian"))
        # Jawaban terkunci: tidak bisa diubah jika sudah pernah dijawab
        conn = _db()
        existing = conn.execute(
            "SELECT id FROM jawaban WHERE peserta_id=? AND no_soal=?", (pid, no)
        ).fetchone()
        if existing:
            conn.close()
            flash("Soal ini sudah dijawab dan tidak dapat diubah.", "error")
            # pindah ke soal berikutnya yang belum dijawab
            answered = {
                r["no_soal"]
                for r in _db().execute(
                    "SELECT no_soal FROM jawaban WHERE peserta_id=?", (pid,)
                ).fetchall()
            }
            for i, n in enumerate(order):
                if n not in answered:
                    session["soal_index"] = i
                    return redirect(url_for("sipsi.ujian"))
            return redirect(url_for("sipsi.selesai"))
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
        conn2 = _db()
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
            return redirect(url_for("sipsi.selesai"))
        session["soal_index"] = next_idx
        return redirect(url_for("sipsi.ujian"))

    if idx >= len(order):
        return redirect(url_for("sipsi.selesai"))

    no = order[idx]
    item = soal_by_id[no]
    domain, teks = item[1], item[2]
    progress = int((idx / len(order)) * 100)
    menit, detik = divmod(sisa, 60)
    jam, menit = divmod(menit, 60)
    sisa_str = f"{jam:02d}:{menit:02d}:{detik:02d}"

    conn = _db()
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
        <img src="{url_for('sipsi.static_logo')}" alt="SIPSI">
        <div class="exam-title">SIPSI</div>
        <div class="exam-sub">Sistem Skrining Psikometri Kesehatan Jiwa</div>
      </div>
      <div class="exam-meta">
        <div><div class="k">SOAL NO.</div><strong>{idx + 1} / {len(order)}</strong></div>
        <div><div class="k">ID PESERTA</div><strong>{p['kode'] if p else '-'}</strong></div>
        <div><div class="k">Nama Peserta</div><strong>{p['nama'] if p else '-'}</strong></div>
        <div><div class="k">JENIS KELAMIN</div><strong>{(p['jk'] if p else '') or '-'}</strong></div>
        <div><div class="k">TANGGAL UJIAN</div><strong>{(p['mulai_at'] or '')[:10] if p else '-'}</strong></div>
        <div><div class="k">SISA WAKTU</div><strong id="sisaWaktu">{sisa_str}</strong></div>
      </div>
      <div class="exam-body">
        <div class="exam-nav">
          <form method="post" style="margin:0">
            <input type="hidden" name="aksi" value="prev">
            <button class="arrow" type="submit" {"disabled" if idx==0 else ""}>&#9664;</button>
          </form>
          <div class="exam-q">{teks}</div>
          <form method="post" style="margin:0">
            <input type="hidden" name="aksi" value="next">
            <button class="arrow" type="submit" {"disabled" if idx>=len(order)-1 else ""}>&#9654;</button>
          </form>
        </div>
        {('<form method="post" class="ans-row">' if not jaw_prev else '<div class="ans-row">')}
          <input type="hidden" name="no_soal" value="{no}">
          <button class="ans-ya {'on' if jaw_prev=='Ya' else ''}" name="jawaban" value="Ya" type="submit" {'disabled' if jaw_prev else ''}>YA</button>
          <div class="ans-mid">---</div>
          <button class="ans-tidak {'on' if jaw_prev=='Tidak' else ''}" name="jawaban" value="Tidak" type="submit" {'disabled' if jaw_prev else ''}>TIDAK</button>
        {('</form>' if not jaw_prev else '</div>')}
        {('<div class="locked-note">&#128274; Soal ini sudah dijawab (<b>' + jaw_prev + '</b>) dan tidak dapat diubah. Gunakan tombol &#9664; &#9654; untuk pindah soal.</div>') if jaw_prev else ''}
        <div style="height:8px;background:#1e293b;border-radius:99px;overflow:hidden;max-width:480px;margin:16px auto 0;width:100%;border:1px solid #334155">
          <div style="height:100%;width:{progress}%;background:#38bdf8"></div>
        </div>
        <p style="margin:10px 0 0;color:#64748b;font-size:0.8rem">Domain: {domain} - Urutan diacak - Jawaban terkunci setelah dipilih</p>
      </div>

      <div style="margin-top:16px;text-align:center">
        <form method="post" style="display:inline">
          <input type="hidden" name="aksi" value="selesai">
          <button type="submit" style="background:#dc2626;color:#fff;border:none;border-radius:10px;padding:12px 28px;font-weight:800;cursor:pointer">
            SELESAI
          </button>
        </form>
        <div class="panel-hint exam-footer" style="text-align:center;margin-top:10px">BK Tech - Support: Adha H.Y</div>
      </div>
    </div>

    <script>
    (function() {{
      var sisa = {sisa};
      var el = document.getElementById('sisaWaktu');
      function tick() {{
        if (sisa <= 0) {{
          el.textContent = '00:00:00';
          window.location.href = '{url_for("sipsi.selesai")}';
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


@sipsi_bp.route("/selesai", strict_slashes=False)
@_login_gate
def selesai():
    pid = session.get("peserta_id")
    if not pid:
        return redirect(url_for("sipsi.mulai"))

    conn = _db()
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
        return redirect(url_for("sipsi.ujian"))

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
    return redirect(url_for("sipsi.hasil", pid=pid))


@sipsi_bp.route("/hasil/<int:pid>", strict_slashes=False)
@_login_gate
def hasil(pid):
    import json

    conn = _db()
    p = conn.execute("SELECT * FROM peserta WHERE id=?", (pid,)).fetchone()
    h = conn.execute("SELECT * FROM hasil WHERE peserta_id=?", (pid,)).fetchone()
    jaw = conn.execute(
        "SELECT * FROM jawaban WHERE peserta_id=? ORDER BY no_soal",
        (pid,),
    ).fetchall()
    conn.close()
    if not p or not h:
        flash("Data tidak ditemukan.", "error")
        return redirect(url_for("sipsi.riwayat"))

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

    mulai_jam = (p["mulai_at"] or "")[-8:] if p["mulai_at"] else "-"
    selesai_jam = (p["selesai_at"] or "")[-8:] if p["selesai_at"] else "-"
    tgl_tes = (p["mulai_at"] or "")[:10] if p["mulai_at"] else "-"

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
        html, body {{
          background: #fff !important;
          color: #000 !important;
          margin: 0 !important;
          padding: 0 !important;
          -webkit-print-color-adjust: exact !important;
          print-color-adjust: exact !important;
        }}
        .sidebar, .topbar, .no-print, nav, .btn, .menu-btn, .sidebar-overlay, .app-footer,
        .loading-overlay, .page-loader, .global-loader, #loading, #loader, #simpatik-app-footer {{
          display: none !important;
        }}
        .layout {{ display: block !important; }}
        .main {{
          margin: 0 !important;
          padding: 0 !important;
          width: 100% !important;
          max-width: 100% !important;
          background: #fff !important;
        }}
        .print-sheet {{
          border: none !important;
          padding: 0 !important;
          max-width: 100% !important;
          margin: 0 !important;
          border-radius: 0 !important;
          background: #fff !important;
          color: #111 !important;
          box-shadow: none !important;
        }}
        .chart-v {{
          -webkit-print-color-adjust: exact !important;
          print-color-adjust: exact !important;
          page-break-inside: avoid;
          overflow: visible !important;
        }}
        .cbar svg, .cbar rect, .cbar text {{
          -webkit-print-color-adjust: exact !important;
          print-color-adjust: exact !important;
        }}
        .bio-grid, .section-title, .deskripsi-box, .saran-box {{
          page-break-inside: avoid;
        }}
        img {{ max-width: 64px !important; }}
        @page {{
          size: A4;
          margin: 12mm 14mm;
        }}
      }}
    </style>

    <div class="print-sheet">
      <div style="text-align:center;margin-bottom:6px">
        <img src="{url_for('sipsi.static_logo')}" alt="SIPSI"
             style="width:64px;height:64px;object-fit:contain;margin:0 auto 4px;display:block">
      </div>
      <h1>LEMBAR JAWABAN PSIKOMETRI KESEHATAN JIWA</h1>
      <div class="kode-big">{p['kode']}</div>

      <div class="bio-grid">
        <div><span class="lab">TANGGAL TES</span> : {tgl_tes}</div>
        <div><span class="lab">JENIS KELAMIN</span> : {p['jk'] or '-'}</div>
        <div><span class="lab">PENDIDIKAN TERAKHIR</span> : {p['pendidikan'] or '-'}</div>
        <div><span class="lab">NAMA LENGKAP</span> : {p['nama']}</div>
        <div><span class="lab">TGL. LAHIR</span> : {p['tgl_lahir'] or '-'}</div>
        <div><span class="lab">STATUS PERKAWINAN</span> : {(p['status_perkawinan'] if 'status_perkawinan' in p.keys() else None) or '-'}</div>
        <div><span class="lab">NO. HP/WA</span> : {p['no_telp'] or '-'}</div>
        <div><span class="lab">TES DI MULAI PUKUL</span> : {mulai_jam}</div>
        <div><span class="lab">PEKERJAAN</span> : {p['pekerjaan'] or '-'}</div>
        <div><span class="lab">SUKU BANGSA</span> : {(p['suku_bangsa'] if 'suku_bangsa' in p.keys() else None) or '-'}</div>
        <div><span class="lab">SELESAI PUKUL</span> : {selesai_jam}</div>
        <div></div>
      </div>

      {warn}

      <div class="chart-v">
        {chart_bars}
      </div>
      <div class="legend-note">&#9632; SIPSI</div>

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
      <button class="btn" onclick="window.print()">&#128424; Cetak Laporan</button>
      <a class="btn secondary" href="{url_for('sipsi.riwayat')}">Riwayat</a>
      <a class="btn secondary" href="{url_for('sipsi.mulai')}">Tes Baru</a>
    </div>
    """
    return page("Hasil Skrining", body, active="riwayat", subtitle="Lembar jawaban psikometri")


@sipsi_bp.route("/riwayat", methods=["GET", "POST"], strict_slashes=False)
@_login_gate
def riwayat():
    if request.method == "POST":
        aksi = (request.form.get("aksi") or "").strip()
        if aksi == "hapus":
            ids = request.form.getlist("ids")
            ids = [int(x) for x in ids if str(x).isdigit()]
            if not ids:
                flash("Pilih minimal satu data untuk dihapus.", "error")
            else:
                conn = _db()
                for pid in ids:
                    conn.execute("DELETE FROM jawaban WHERE peserta_id=?", (pid,))
                    conn.execute("DELETE FROM hasil WHERE peserta_id=?", (pid,))
                    conn.execute("DELETE FROM peserta WHERE id=?", (pid,))
                conn.commit()
                conn.close()
                flash(f"{len(ids)} data riwayat berhasil dihapus.", "success")
            return redirect(url_for("sipsi.riwayat"))

    conn = _db()
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
        link = url_for("sipsi.hasil", pid=r["id"]) if r["skor_total"] is not None else "#"
        skor = r["skor_total"] if r["skor_total"] is not None else "-"
        lihat = f'<a href="{link}">Lihat</a>' if r["skor_total"] is not None else "-"
        tr += f"""
        <tr>
          <td class="checkbox-cell"><input type="checkbox" name="ids" value="{r['id']}" class="row-check"></td>
          <td>{r['kode']}</td>
          <td>{r['nama']}</td>
          <td>{r['selesai_at'] or '-'}</td>
          <td>{skor}</td>
          <td>{lihat}</td>
        </tr>"""
    body = f"""
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
        <h2 style="margin:0">Riwayat Peserta</h2>
        <a class="btn" href="{url_for('sipsi.mulai')}"><i class="fas fa-plus"></i> Tes Baru</a>
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


# ================= TES PSIKOLOGI 100 ITEM (tambahan terpisah) =================
# Kuesioner refleksi non-klinis; bukan EPPS resmi atau instrumen tervalidasi.
import html as _sipsi_psych_html
PSIKOLOGI_100_ITEMS = [('ach', 'Achievement (Pencapaian)', 'Saya menetapkan target yang jelas untuk pekerjaan saya.'), ('ach', 'Achievement (Pencapaian)', 'Saya berusaha menghasilkan pekerjaan dengan kualitas terbaik.'), ('ach', 'Achievement (Pencapaian)', 'Saya mengevaluasi hasil kerja untuk menemukan hal yang perlu diperbaiki.'), ('ach', 'Achievement (Pencapaian)', 'Saya terus mencoba saat menghadapi tugas yang sulit.'), ('ach', 'Achievement (Pencapaian)', 'Saya membuat prioritas agar target dapat tercapai.'), ('ach', 'Achievement (Pencapaian)', 'Saya merasa puas ketika berhasil mencapai sasaran.'), ('ach', 'Achievement (Pencapaian)', 'Saya mempelajari keterampilan baru untuk meningkatkan hasil kerja.'), ('def', 'Deference (Menghargai Arahan)', 'Saya mempertimbangkan arahan atasan sebelum mengambil keputusan penting.'), ('def', 'Deference (Menghargai Arahan)', 'Saya menghargai pengalaman orang yang lebih menguasai suatu bidang.'), ('def', 'Deference (Menghargai Arahan)', 'Saya meminta penjelasan ketika instruksi belum jelas.'), ('def', 'Deference (Menghargai Arahan)', 'Saya mengikuti prosedur yang telah disepakati bersama.'), ('def', 'Deference (Menghargai Arahan)', 'Saya menerima masukan dari pihak yang bertanggung jawab.'), ('def', 'Deference (Menghargai Arahan)', 'Saya memastikan keputusan saya sesuai aturan yang berlaku.'), ('def', 'Deference (Menghargai Arahan)', 'Saya mengakui ketika orang lain memiliki pengetahuan lebih baik.'), ('ord', 'Order (Keteraturan)', 'Saya menyusun langkah kerja sebelum memulai tugas.'), ('ord', 'Order (Keteraturan)', 'Saya menyimpan dokumen agar mudah ditemukan kembali.'), ('ord', 'Order (Keteraturan)', 'Saya memeriksa detail untuk mengurangi kesalahan.'), ('ord', 'Order (Keteraturan)', 'Saya menjaga ruang kerja tetap tertata.'), ('ord', 'Order (Keteraturan)', 'Saya menggunakan daftar tugas untuk memantau pekerjaan.'), ('ord', 'Order (Keteraturan)', 'Saya mengikuti langkah kerja yang sistematis.'), ('ord', 'Order (Keteraturan)', 'Saya mencatat informasi penting agar tidak terlupakan.'), ('exh', 'Exhibition (Menyampaikan Diri)', 'Saya nyaman menjelaskan hasil kerja di depan kelompok.'), ('exh', 'Exhibition (Menyampaikan Diri)', 'Saya bersedia mempresentasikan gagasan yang saya anggap bermanfaat.'), ('exh', 'Exhibition (Menyampaikan Diri)', 'Saya dapat menjelaskan kemampuan saya tanpa merendahkan orang lain.'), ('exh', 'Exhibition (Menyampaikan Diri)', 'Saya menyampaikan pendapat ketika diskusi membutuhkan kontribusi saya.'), ('exh', 'Exhibition (Menyampaikan Diri)', 'Saya bersedia menjadi juru bicara tim bila diperlukan.'), ('exh', 'Exhibition (Menyampaikan Diri)', 'Saya dapat menceritakan pencapaian kerja secara faktual.'), ('exh', 'Exhibition (Menyampaikan Diri)', 'Saya menyesuaikan cara presentasi dengan audiens.'), ('aut', 'Autonomy (Kemandirian)', 'Saya dapat memulai tugas tanpa harus selalu diingatkan.'), ('aut', 'Autonomy (Kemandirian)', 'Saya mampu menentukan langkah kerja ketika tujuannya jelas.'), ('aut', 'Autonomy (Kemandirian)', 'Saya berani menyampaikan pendapat berbeda dengan sopan.'), ('aut', 'Autonomy (Kemandirian)', 'Saya bertanggung jawab atas keputusan yang saya ambil.'), ('aut', 'Autonomy (Kemandirian)', 'Saya mencari solusi awal sebelum meminta bantuan.'), ('aut', 'Autonomy (Kemandirian)', 'Saya dapat bekerja mandiri sambil tetap berkoordinasi.'), ('aut', 'Autonomy (Kemandirian)', 'Saya mampu mengatur waktu kerja sendiri.'), ('aff', 'Affiliation (Kerja Sama)', 'Saya berusaha membangun hubungan kerja yang saling menghormati.'), ('aff', 'Affiliation (Kerja Sama)', 'Saya menikmati kerja sama untuk mencapai tujuan bersama.'), ('aff', 'Affiliation (Kerja Sama)', 'Saya meluangkan waktu untuk mendengarkan rekan kerja.'), ('aff', 'Affiliation (Kerja Sama)', 'Saya menjaga komunikasi baik meski berbeda pendapat.'), ('aff', 'Affiliation (Kerja Sama)', 'Saya menawarkan bantuan ketika rekan kerja membutuhkannya.'), ('aff', 'Affiliation (Kerja Sama)', 'Saya berusaha membuat anggota tim merasa dilibatkan.'), ('aff', 'Affiliation (Kerja Sama)', 'Saya menjaga hubungan profesional setelah terjadi kesalahpahaman.'), ('int', 'Intraception (Memahami Orang)', 'Saya mencoba memahami alasan di balik perilaku orang lain.'), ('int', 'Intraception (Memahami Orang)', 'Saya memperhatikan perasaan orang lain saat berkomunikasi.'), ('int', 'Intraception (Memahami Orang)', 'Saya mempertimbangkan konteks sebelum menilai tindakan seseorang.'), ('int', 'Intraception (Memahami Orang)', 'Saya berusaha melihat masalah dari lebih dari satu sudut pandang.'), ('int', 'Intraception (Memahami Orang)', 'Saya bertanya untuk memahami kebutuhan orang yang saya layani.'), ('int', 'Intraception (Memahami Orang)', 'Saya dapat membedakan fakta yang terlihat dan dugaan pribadi.'), ('int', 'Intraception (Memahami Orang)', 'Saya memperhatikan perubahan suasana dalam percakapan.'), ('suc', 'Succorance (Mencari Dukungan)', 'Saya bersedia meminta bantuan ketika menghadapi kendala yang tidak dapat saya atasi sendiri.'), ('suc', 'Succorance (Mencari Dukungan)', 'Saya berkonsultasi ketika keputusan memiliki risiko besar.'), ('suc', 'Succorance (Mencari Dukungan)', 'Saya memberi tahu pihak terkait ketika membutuhkan dukungan.'), ('suc', 'Succorance (Mencari Dukungan)', 'Saya dapat mengakui bahwa saya belum mengetahui sesuatu.'), ('suc', 'Succorance (Mencari Dukungan)', 'Saya mencari bimbingan untuk meningkatkan kemampuan.'), ('suc', 'Succorance (Mencari Dukungan)', 'Saya menerima bantuan dengan terbuka dan berterima kasih.'), ('suc', 'Succorance (Mencari Dukungan)', 'Saya berdiskusi dengan orang tepercaya saat mempertimbangkan pilihan sulit.'), ('dom', 'Dominance (Koordinasi dan Pengaruh)', 'Saya bersedia mengoordinasikan tugas ketika dibutuhkan.'), ('dom', 'Dominance (Koordinasi dan Pengaruh)', 'Saya menjelaskan tujuan agar anggota tim memahami arah pekerjaan.'), ('dom', 'Dominance (Koordinasi dan Pengaruh)', 'Saya membantu menentukan prioritas saat pekerjaan menumpuk.'), ('dom', 'Dominance (Koordinasi dan Pengaruh)', 'Saya menyampaikan keputusan beserta alasan yang jelas.'), ('dom', 'Dominance (Koordinasi dan Pengaruh)', 'Saya memberi kesempatan orang lain menyampaikan pendapat.'), ('dom', 'Dominance (Koordinasi dan Pengaruh)', 'Saya berusaha menyelesaikan konflik secara adil.'), ('dom', 'Dominance (Koordinasi dan Pengaruh)', 'Saya memantau kemajuan tanpa mengabaikan kepercayaan pada tim.'), ('aba', 'Abasement (Menerima Kekurangan)', 'Saya dapat mengakui kesalahan tanpa mencari kambing hitam.'), ('aba', 'Abasement (Menerima Kekurangan)', 'Saya menerima kritik yang disertai alasan dan bukti.'), ('aba', 'Abasement (Menerima Kekurangan)', 'Saya dapat meminta maaf ketika tindakan saya merugikan orang lain.'), ('aba', 'Abasement (Menerima Kekurangan)', 'Saya menilai kemampuan diri secara realistis.'), ('aba', 'Abasement (Menerima Kekurangan)', 'Saya bersedia belajar dari orang yang lebih berpengalaman.'), ('aba', 'Abasement (Menerima Kekurangan)', 'Saya mengakui kontribusi orang lain dalam keberhasilan bersama.'), ('aba', 'Abasement (Menerima Kekurangan)', 'Saya memperbaiki kesalahan setelah menyadarinya.'), ('nur', 'Nurturance (Kepedulian)', 'Saya memperhatikan ketika rekan kerja terlihat membutuhkan bantuan.'), ('nur', 'Nurturance (Kepedulian)', 'Saya bersedia berbagi pengetahuan dengan anggota tim.'), ('nur', 'Nurturance (Kepedulian)', 'Saya memberikan bantuan tanpa mengambil alih tanggung jawab orang lain.'), ('nur', 'Nurturance (Kepedulian)', 'Saya menanggapi pertanyaan orang lain dengan sabar.'), ('nur', 'Nurturance (Kepedulian)', 'Saya berusaha mendukung rekan yang sedang belajar.'), ('nur', 'Nurturance (Kepedulian)', 'Saya mempertimbangkan kebutuhan orang yang terdampak oleh pekerjaan saya.'), ('chg', 'Change (Adaptasi terhadap Perubahan)', 'Saya dapat menyesuaikan diri ketika prioritas berubah.'), ('chg', 'Change (Adaptasi terhadap Perubahan)', 'Saya bersedia mempelajari cara kerja baru.'), ('chg', 'Change (Adaptasi terhadap Perubahan)', 'Saya tetap tenang ketika rencana perlu diubah.'), ('chg', 'Change (Adaptasi terhadap Perubahan)', 'Saya mencari informasi sebelum menghadapi situasi baru.'), ('chg', 'Change (Adaptasi terhadap Perubahan)', 'Saya menerima perubahan yang memiliki alasan jelas.'), ('chg', 'Change (Adaptasi terhadap Perubahan)', 'Saya menyesuaikan komunikasi dengan orang dan situasi berbeda.'), ('end', 'Endurance (Ketekunan)', 'Saya melanjutkan tugas meskipun kemajuannya terasa lambat.'), ('end', 'Endurance (Ketekunan)', 'Saya berusaha menyelesaikan pekerjaan sebelum beralih ke hal lain.'), ('end', 'Endurance (Ketekunan)', 'Saya mencoba pendekatan berbeda ketika cara pertama tidak berhasil.'), ('end', 'Endurance (Ketekunan)', 'Saya tetap fokus pada tugas penting saat muncul gangguan.'), ('end', 'Endurance (Ketekunan)', 'Saya menindaklanjuti pekerjaan yang belum tuntas.'), ('end', 'Endurance (Ketekunan)', 'Saya tekun mengerjakan tugas rutin yang membutuhkan ketelitian.'), ('soc', 'Social Confidence (Kepercayaan Diri Sosial)', 'Saya dapat memulai percakapan profesional dengan orang yang baru dikenal.'), ('soc', 'Social Confidence (Kepercayaan Diri Sosial)', 'Saya nyaman bertanya ketika perlu memperjelas informasi.'), ('soc', 'Social Confidence (Kepercayaan Diri Sosial)', 'Saya dapat menyampaikan kebutuhan secara langsung dan santun.'), ('soc', 'Social Confidence (Kepercayaan Diri Sosial)', 'Saya tetap terlibat dalam diskusi meski belum mengenal semua peserta.'), ('soc', 'Social Confidence (Kepercayaan Diri Sosial)', 'Saya dapat menerima perbedaan gaya komunikasi antarorang.'), ('soc', 'Social Confidence (Kepercayaan Diri Sosial)', 'Saya bersedia membangun jaringan kerja untuk tujuan profesional.'), ('agg', 'Assertiveness (Ketegasan yang Terkendali)', 'Saya menyampaikan ketidaksetujuan tanpa menyerang pribadi orang lain.'), ('agg', 'Assertiveness (Ketegasan yang Terkendali)', 'Saya membahas masalah secara langsung dengan pihak yang terkait.'), ('agg', 'Assertiveness (Ketegasan yang Terkendali)', 'Saya dapat mengatakan tidak ketika permintaan bertentangan dengan aturan atau kapasitas.'), ('agg', 'Assertiveness (Ketegasan yang Terkendali)', 'Saya menyampaikan batasan dengan bahasa yang jelas dan sopan.'), ('agg', 'Assertiveness (Ketegasan yang Terkendali)', 'Saya berusaha menyelesaikan perbedaan berdasarkan fakta.'), ('agg', 'Assertiveness (Ketegasan yang Terkendali)', 'Saya dapat mempertahankan pendapat sambil tetap mendengarkan alasan orang lain.')]
PSIKOLOGI_SKALA = {
    "A": (1, "Sangat tidak sesuai"),
    "B": (2, "Tidak sesuai"),
    "C": (3, "Netral"),
    "D": (4, "Sesuai"),
    "E": (5, "Sangat sesuai"),
}

def _psikologi_init_db():
    conn = _db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS psikologi_peserta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode TEXT UNIQUE, nama TEXT NOT NULL,
            pendidikan TEXT, pekerjaan TEXT,
            created_at TEXT NOT NULL, selesai_at TEXT
        );
        CREATE TABLE IF NOT EXISTS psikologi_jawaban (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            peserta_id INTEGER NOT NULL, no_soal INTEGER NOT NULL,
            indikator TEXT NOT NULL, pilihan TEXT NOT NULL, skor INTEGER NOT NULL,
            UNIQUE(peserta_id, no_soal),
            FOREIGN KEY(peserta_id) REFERENCES psikologi_peserta(id)
        );
        CREATE TABLE IF NOT EXISTS psikologi_hasil (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            peserta_id INTEGER NOT NULL UNIQUE, skor_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(peserta_id) REFERENCES psikologi_peserta(id)
        );
    """)
    conn.commit()
    conn.close()

@sipsi_bp.route("/psikologi", methods=["GET"], strict_slashes=False)
@_login_gate
def psikologi_index():
    _psikologi_init_db()
    conn = _db()
    total = conn.execute("SELECT COUNT(*) FROM psikologi_peserta").fetchone()[0]
    selesai = conn.execute("SELECT COUNT(*) FROM psikologi_peserta WHERE selesai_at IS NOT NULL").fetchone()[0]
    recent = conn.execute("SELECT id,kode,nama,selesai_at FROM psikologi_peserta ORDER BY id DESC LIMIT 8").fetchall()
    conn.close()
    row_html = []
    for r in recent:
        nama = _sipsi_psych_html.escape(r["nama"] or "")
        status = _sipsi_psych_html.escape(r["selesai_at"] or "Belum selesai")
        link = url_for("sipsi.psikologi_hasil", pid=r["id"])
        row_html.append(f'<tr><td>{r["kode"]}</td><td>{nama}</td><td>{status}</td><td><a class="btn" href="{link}">Lihat hasil</a></td></tr>')
    rows = "".join(row_html) or '<tr><td colspan="4" class="muted">Belum ada peserta.</td></tr>'
    body = f"""
    <div class="stat-grid">
      <div class="stat"><div class="label">Peserta psikologi</div><div class="value">{total}</div></div>
      <div class="stat"><div class="label">Tes selesai</div><div class="value">{selesai}</div></div>
    </div>
    <div class="card"><h2>Tes Psikologi — 100 Pernyataan</h2>
      <p class="muted">Pilih jawaban yang paling menggambarkan kebiasaan Anda. Tidak ada jawaban benar atau salah.</p>
      <p><b>Skala:</b> A Sangat tidak sesuai · B Tidak sesuai · C Netral · D Sesuai · E Sangat sesuai.</p>
      <p class="muted">Kuesioner refleksi ini bukan alat diagnosis atau tes psikologi terstandar.</p>
      <a class="btn" href="{url_for('sipsi.psikologi_mulai')}">Mulai Tes Psikologi</a>
    </div>
    <div class="card"><h3>Peserta terbaru</h3><div style="overflow-x:auto"><table>
      <thead><tr><th>Kode</th><th>Nama</th><th>Status</th><th>Hasil</th></tr></thead><tbody>{rows}</tbody>
    </table></div><p><a href="{url_for('sipsi.psikologi_riwayat')}">Lihat seluruh riwayat</a></p></div>
    """
    return page("Tes Psikologi", body, active="psikologi", subtitle="Kuesioner refleksi 100 item")

@sipsi_bp.route("/psikologi/mulai", methods=["GET", "POST"], strict_slashes=False)
@_login_gate
def psikologi_mulai():
    _psikologi_init_db()
    if request.method == "POST":
        nama = (request.form.get("nama") or "").strip()
        pendidikan = (request.form.get("pendidikan") or "").strip()
        pekerjaan = (request.form.get("pekerjaan") or "").strip()
        if not nama:
            flash("Nama peserta wajib diisi.", "error")
            return redirect(url_for("sipsi.psikologi_mulai"))
        kode = "PSI-" + datetime.now().strftime("%y%m%d%H%M%S") + "-" + str(random.randint(100, 999))
        conn = _db()
        cur = conn.execute("INSERT INTO psikologi_peserta(kode,nama,pendidikan,pekerjaan,created_at) VALUES(?,?,?,?,?)",
                           (kode, nama, pendidikan, pekerjaan, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        pid = cur.lastrowid
        conn.commit()
        conn.close()
        session["sipsi_psikologi_pid"] = pid
        return redirect(url_for("sipsi.psikologi_ujian"))
    body = f"""
    <div class="card"><h2>Data Peserta</h2>
    <form method="post">
      <label>Nama lengkap *</label><input name="nama" required maxlength="150" style="width:100%;padding:10px;margin:6px 0 14px">
      <label>Pendidikan</label><input name="pendidikan" maxlength="100" style="width:100%;padding:10px;margin:6px 0 14px">
      <label>Pekerjaan/Jabatan</label><input name="pekerjaan" maxlength="150" style="width:100%;padding:10px;margin:6px 0 14px">
      <button class="btn" type="submit">Lanjut ke 100 Soal</button>
      <a class="btn secondary" href="{url_for('sipsi.psikologi_index')}">Batal</a>
    </form></div>
    """
    return page("Peserta Tes Psikologi", body, active="psikologi", subtitle="Isi data peserta")

@sipsi_bp.route("/psikologi/ujian", methods=["GET", "POST"], strict_slashes=False)
@_login_gate
def psikologi_ujian():
    _psikologi_init_db()
    pid = session.get("sipsi_psikologi_pid")
    if not pid:
        flash("Silakan isi data peserta terlebih dahulu.", "error")
        return redirect(url_for("sipsi.psikologi_mulai"))
    conn = _db()
    peserta = conn.execute("SELECT * FROM psikologi_peserta WHERE id=?", (pid,)).fetchone()
    if not peserta or peserta["selesai_at"]:
        conn.close()
        session.pop("sipsi_psikologi_pid", None)
        return redirect(url_for("sipsi.psikologi_index"))
    if request.method == "POST":
        answers = {}
        for no in range(1, 101):
            value = (request.form.get(f"q{no}") or "").upper()
            if value not in PSIKOLOGI_SKALA:
                conn.close()
                flash(f"Jawaban nomor {no} belum dipilih. Semua 100 soal wajib dijawab.", "error")
                return redirect(url_for("sipsi.psikologi_ujian"))
            answers[no] = value
        scores = {}
        conn.execute("DELETE FROM psikologi_jawaban WHERE peserta_id=?", (pid,))
        for no, (code, label, question) in enumerate(PSIKOLOGI_100_ITEMS, start=1):
            choice = answers[no]
            score = PSIKOLOGI_SKALA[choice][0]
            scores.setdefault((code, label), []).append(score)
            conn.execute("INSERT INTO psikologi_jawaban(peserta_id,no_soal,indikator,pilihan,skor) VALUES(?,?,?,?,?)",
                         (pid, no, label, choice, score))
        detail = {}
        for (code, label), vals in scores.items():
            avg = sum(vals) / len(vals)
            detail[code] = {"indikator": label, "jumlah_item": len(vals), "rerata": round(avg, 2), "skala_0_100": round((avg - 1) * 25, 1)}
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("INSERT OR REPLACE INTO psikologi_hasil(peserta_id,skor_json,created_at) VALUES(?,?,?)",
                     (pid, json.dumps(detail, ensure_ascii=False), now))
        conn.execute("UPDATE psikologi_peserta SET selesai_at=? WHERE id=?", (now, pid))
        conn.commit()
        conn.close()
        session.pop("sipsi_psikologi_pid", None)
        return redirect(url_for("sipsi.psikologi_hasil", pid=pid))
    conn.close()
    cards = []
    for no, (code, label, question) in enumerate(PSIKOLOGI_100_ITEMS, start=1):
        options = []
        for letter, (score, caption) in PSIKOLOGI_SKALA.items():
            options.append(f'<label class="psy-option"><input type="radio" name="q{no}" value="{letter}" required> <b>{letter}</b> — {caption}</label>')
        safe_question = _sipsi_psych_html.escape(question)
        safe_label = _sipsi_psych_html.escape(label)
        cards.append(f'<fieldset class="psy-question"><legend>{no}. {safe_question}</legend><div class="muted" style="font-size:12px;margin-bottom:8px">Indikator: {safe_label}</div><div class="psy-options">{"".join(options)}</div></fieldset>')
    body = """
    <style>
      .psy-question{border:1px solid #dbe3ee;border-radius:12px;padding:14px;margin:12px 0;background:rgba(148,163,184,.06);min-width:0}
      .psy-question legend{font-weight:700;padding:0 5px}
      .psy-options{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:8px}
      .psy-option{display:flex;align-items:flex-start;gap:7px;border:1px solid #dbe3ee;border-radius:8px;padding:9px;cursor:pointer}
      .psy-option input{width:auto;margin-top:3px}
      @media(max-width:600px){.psy-options{grid-template-columns:1fr}.psy-question{padding:10px}}
      .psy-sticky{position:sticky;bottom:8px;padding:12px;background:#fff;border:1px solid #cbd5e1;border-radius:12px;z-index:2}
    </style>
    """
    safe_name = _sipsi_psych_html.escape(peserta["nama"] or "")
    body += f'<div class="card"><h2>Tes Psikologi — 100 Soal</h2><p>Peserta: <b>{safe_name}</b></p><p class="muted">Pilih satu jawaban untuk setiap pernyataan. Semua soal wajib dijawab.</p><form method="post" id="psy-form">'
    body += "".join(cards)
    body += '<div class="psy-sticky"><button class="btn" type="submit" onclick="return confirm(\'Kirim jawaban dan selesaikan tes?\')">Kirim Jawaban &amp; Lihat Hasil</button></div></form></div>'
    return page("Pengerjaan Tes Psikologi", body, active="psikologi", subtitle="100 pernyataan pilihan A–E")

@sipsi_bp.route("/psikologi/hasil/<int:pid>", methods=["GET"], strict_slashes=False)
@_login_gate
def psikologi_hasil(pid):
    _psikologi_init_db()
    conn = _db()
    peserta = conn.execute(
        "SELECT * FROM psikologi_peserta WHERE id=?", (pid,)
    ).fetchone()
    hasil = conn.execute(
        "SELECT * FROM psikologi_hasil WHERE peserta_id=?", (pid,)
    ).fetchone()
    conn.close()

    if not peserta:
        flash("Data peserta tidak ditemukan.", "error")
        return redirect(url_for("sipsi.psikologi_index"))
    if not hasil:
        flash("Tes peserta ini belum selesai.", "info")
        return redirect(url_for("sipsi.psikologi_riwayat"))

    try:
        detail = json.loads(hasil["skor_json"] or "{}")
    except (TypeError, ValueError):
        detail = {}

    esc = _sipsi_psych_html.escape
    nama = esc(peserta["nama"] or "-")
    kode = esc(peserta["kode"] or "-")
    dibuat = esc(peserta["created_at"] or "-")
    selesai = esc(peserta["selesai_at"] or "-")
    tanggal_laporan = datetime.now().strftime("%d-%m-%Y")

    # Skor ditampilkan sesuai hasil tersimpan, tanpa membuat diagnosis.
    indikator = []
    for code, value in detail.items():
        try:
            score = max(0.0, min(100.0, float(value.get("skala_0_100", 0))))
            average = float(value.get("rerata", 0))
            count = int(value.get("jumlah_item", 0))
        except (TypeError, ValueError):
            continue
        label = esc(str(value.get("indikator", code)))
        indikator.append({
            "code": esc(str(code).upper()),
            "label": label,
            "score": score,
            "average": average,
            "count": count,
        })
    indikator.sort(key=lambda x: x["score"], reverse=True)

    rows = []
    bars = []
    for item in indikator:
        score = item["score"]
        width = f"{score:.1f}"
        rows.append(
            f'<tr><td>{item["code"]}</td><td>{item["label"]}</td>'
            f'<td class="num">{item["count"]}</td>'
            f'<td class="num">{item["average"]:.2f}/5</td>'
            f'<td class="num"><b>{score:.1f}</b></td></tr>'
        )
        bars.append(
            '<div class="bar-row">'
            f'<div class="bar-label">{item["label"]}</div>'
            '<div class="bar-track"><div class="bar-fill" '
            f'style="width:{width}%"></div></div>'
            f'<div class="bar-value">{score:.1f}</div></div>'
        )

    if indikator:
        top = indikator[0]
        ringkasan = (
            f'Pada ringkasan skor ini, indikator dengan nilai relatif tertinggi '
            f'adalah <b>{top["label"]}</b> ({top["score"]:.1f} dari 100). '
            'Nilai ini menggambarkan jawaban peserta pada kuesioner refleksi, '
            'bukan perbandingan dengan norma populasi.'
        )
    else:
        ringkasan = "Data skor indikator belum tersedia untuk ditampilkan."

    logo_url = url_for("sipsi.static_logo")
    body = f"""
    <style>
      .psych-report {{
        max-width:900px;margin:0 auto;background:#fff;color:#172033;
        border:1px solid #d7dee8;border-radius:10px;padding:24px;
        box-shadow:0 4px 18px rgba(15,23,42,.06);font-size:13px;
      }}
      .psych-head {{text-align:center;border-bottom:3px double #1e3a5f;padding-bottom:14px;margin-bottom:16px}}
      .psych-head img {{width:62px;height:62px;object-fit:contain;margin-bottom:6px}}
      .psych-head h1 {{font-size:19px;margin:3px 0;color:#123b70;letter-spacing:.4px}}
      .psych-head p {{margin:3px 0;color:#475569}}
      .psych-code {{font-size:15px;font-weight:800;letter-spacing:1px;margin-top:8px}}
      .psych-meta {{display:grid;grid-template-columns:1fr 1fr;gap:7px 24px;margin:14px 0 18px}}
      .psych-meta div {{padding:6px 0;border-bottom:1px solid #e2e8f0;overflow-wrap:anywhere}}
      .psych-meta b {{display:inline-block;min-width:125px;color:#475569}}
      .psych-section {{font-size:14px;color:#123b70;font-weight:800;border-bottom:1px solid #94a3b8;padding-bottom:5px;margin:18px 0 10px}}
      .psych-bars {{display:grid;gap:9px;margin:12px 0}}
      .bar-row {{display:grid;grid-template-columns:minmax(155px,220px) minmax(80px,1fr) 48px;gap:10px;align-items:center}}
      .bar-label {{font-size:12px;overflow-wrap:anywhere}}
      .bar-track {{height:12px;background:#e8edf4;border-radius:3px;overflow:hidden}}
      .bar-fill {{height:100%;background:#1764b0;border-radius:3px}}
      .bar-value {{text-align:right;font-weight:800;font-variant-numeric:tabular-nums}}
      .psych-table {{width:100%;border-collapse:collapse;font-size:12px}}
      .psych-table th,.psych-table td {{border:1px solid #cbd5e1;padding:7px;text-align:left}}
      .psych-table th {{background:#eaf0f7;color:#123b70}}
      .psych-table .num {{text-align:center;white-space:nowrap}}
      .psych-note {{font-size:11px;line-height:1.6;color:#475569}}
      .psych-sign {{margin:36px 0 0 auto;width:245px;text-align:center;line-height:1.6}}
      .psych-sign .space {{height:58px}}
      .psych-sign .line {{border-top:1px solid #334155;width:180px;margin:0 auto 4px}}
      @media(max-width:600px) {{
        .psych-report {{padding:14px}}
        .psych-meta {{grid-template-columns:1fr}}
        .bar-row {{grid-template-columns:1fr 48px;gap:5px}}
        .bar-label {{grid-column:1 / -1}}
        .psych-table {{font-size:11px}}
        .psych-table th,.psych-table td {{padding:5px}}
      }}
      @media print {{
        @page {{size:A4 portrait;margin:12mm}}
        html,body {{background:#fff!important;color:#000!important;margin:0!important;padding:0!important}}
        .sidebar,.topbar,.no-print,nav,.btn,.menu-btn,.sidebar-overlay,.app-footer,
        .loading-overlay,.page-loader,.global-loader,#loading,#loader,#simpatik-app-footer {{
          display:none!important
        }}
        .layout {{display:block!important}}
        .main {{margin:0!important;padding:0!important;width:100%!important;max-width:100%!important;background:#fff!important}}
        .psych-report {{max-width:none;border:0;border-radius:0;box-shadow:none;padding:0;margin:0}}
        .psych-head,.psych-section,.psych-meta,.psych-bars,.psych-table,.psych-sign {{
          break-inside:avoid;page-break-inside:avoid
        }}
        .bar-fill {{background:#1764b0!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
        .bar-track {{background:#e8edf4!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
        .psych-table th {{background:#eaf0f7!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
      }}
    </style>

    <div class="psych-report">
      <header class="psych-head">
        <img src="{logo_url}" alt="Logo SIPSI">
        <h1>LAPORAN HASIL TES PSIKOLOGI</h1>
        <p>SIPSI — Ringkasan Kuesioner Refleksi 100 Pernyataan</p>
        <div class="psych-code">KODE PESERTA: {kode}</div>
      </header>

      <div class="psych-section">IDENTITAS PESERTA</div>
      <div class="psych-meta">
        <div><b>Nama lengkap</b> : {nama}</div>
        <div><b>Kode peserta</b> : {kode}</div>
        <div><b>Tanggal pendaftaran</b> : {dibuat}</div>
        <div><b>Tanggal selesai</b> : {selesai}</div>
        <div><b>Tanggal laporan</b> : {tanggal_laporan}</div>
      </div>

      <div class="psych-section">GRAFIK RINGKASAN INDIKATOR</div>
      <p class="psych-note">Skala 0–100 merupakan transformasi skor rerata jawaban 1–5. Grafik diurutkan dari skor tertinggi ke terendah untuk memudahkan pembacaan, bukan sebagai peringkat kelayakan peserta.</p>
      <div class="psych-bars">{''.join(bars) if bars else '<p>Belum ada skor indikator.</p>'}</div>

      <div class="psych-section">RINCIAN SKOR</div>
      <div style="overflow-x:auto">
        <table class="psych-table">
          <thead><tr><th>Kode</th><th>Indikator</th><th>Jumlah item</th><th>Rerata</th><th>Skala 0–100</th></tr></thead>
          <tbody>{''.join(rows) if rows else '<tr><td colspan="5">Data skor tidak tersedia.</td></tr>'}</tbody>
        </table>
      </div>

      <div class="psych-section">RINGKASAN</div>
      <p style="line-height:1.7">{ringkasan}</p>

      <div class="psych-section">CATATAN DAN BATASAN</div>
      <p class="psych-note">
        Laporan ini merupakan ringkasan jawaban pada kuesioner refleksi yang digunakan dalam aplikasi.
        Instrumen ini belum divalidasi sebagai alat psikometri terstandar, bukan diagnosis klinis,
        tidak dibandingkan dengan norma populasi, dan tidak dapat digunakan sendirian untuk menetapkan
        kelayakan kerja atau keputusan penting tentang seseorang. Interpretasi lebih lanjut perlu
        dilakukan oleh tenaga profesional yang kompeten dengan mempertimbangkan konteks dan informasi lain.
      </p>

      <div class="psych-sign">
        <div>................................, {tanggal_laporan}</div>
        <div>Tempat, tanggal / bulan / tahun</div>
        <div class="space"></div>
        <div class="line"></div>
        <b>{nama}</b>
      </div>
    </div>

    <div class="no-print" style="max-width:900px;margin:16px auto;text-align:center">
      <button class="btn" onclick="window.print()">&#128424; Cetak Laporan</button>
      <a class="btn secondary" href="{url_for('sipsi.psikologi_index')}">Kembali</a>
      <a class="btn secondary" href="{url_for('sipsi.psikologi_riwayat')}">Riwayat</a>
    </div>
    """
    return page("Hasil Tes Psikologi", body, active="psikologi", subtitle="Laporan hasil tes psikologi")


@sipsi_bp.route("/psikologi/hapus/<int:pid>", methods=["POST"], strict_slashes=False)
@_login_gate
def psikologi_hapus(pid):
    """Hapus satu riwayat tes psikologi beserta jawaban dan hasilnya."""
    _psikologi_init_db()
    conn = _db()
    try:
        peserta = conn.execute(
            "SELECT id, nama FROM psikologi_peserta WHERE id=?", (pid,)
        ).fetchone()

        if not peserta:
            flash("Riwayat tes psikologi tidak ditemukan.", "error")
            return redirect(url_for("sipsi.psikologi_riwayat"))

        # Hanya menghapus data dari tabel khusus tes psikologi.
        with conn:
            conn.execute(
                "DELETE FROM psikologi_jawaban WHERE peserta_id=?", (pid,)
            )
            conn.execute(
                "DELETE FROM psikologi_hasil WHERE peserta_id=?", (pid,)
            )
            conn.execute(
                "DELETE FROM psikologi_peserta WHERE id=?", (pid,)
            )

        flash("Riwayat tes psikologi berhasil dihapus.", "success")

    except Exception:
        conn.rollback()
        flash("Riwayat gagal dihapus. Periksa log aplikasi.", "error")
    finally:
        conn.close()

    return redirect(url_for("sipsi.psikologi_riwayat"))


@sipsi_bp.route("/psikologi/riwayat", methods=["GET"], strict_slashes=False)
@_login_gate
def psikologi_riwayat():
    _psikologi_init_db()
    conn = _db()
    try:
        data = conn.execute(
            "SELECT p.id, p.kode, p.nama, p.created_at, p.selesai_at, "
            "h.skor_json FROM psikologi_peserta p "
            "LEFT JOIN psikologi_hasil h ON h.peserta_id=p.id "
            "ORDER BY p.id DESC LIMIT 500"
        ).fetchall()
    finally:
        conn.close()

    table_rows = []
    for row in data:
        pid = int(row["id"])
        code = _sipsi_psych_html.escape(row["kode"] or "")
        name = _sipsi_psych_html.escape(row["nama"] or "")
        created = _sipsi_psych_html.escape(row["created_at"] or "-")
        status = _sipsi_psych_html.escape(row["selesai_at"] or "Belum selesai")

        if row["skor_json"]:
            action = (
                f'<a class="btn" href="{url_for("sipsi.psikologi_hasil", pid=pid)}">'
                'Lihat</a> '
            )
        else:
            action = ""

        action += f"""
        <form method="post"
              action="{url_for('sipsi.psikologi_hapus', pid=pid)}"
              style="display:inline"
              onsubmit="return confirm('Yakin menghapus riwayat tes psikologi milik {name}? Data jawaban dan hasilnya juga akan dihapus permanen.');">
          <button class="btn" type="submit"
                  style="background:#b91c1c;color:#fff;border:0">
            Hapus
          </button>
        </form>
        """
        table_rows.append(
            f"<tr><td>{code}</td><td>{name}</td><td>{created}</td>"
            f"<td>{status}</td><td>{action}</td></tr>"
        )

    trs = "".join(table_rows) or (
        '<tr><td colspan="5" class="muted">Belum ada riwayat.</td></tr>'
    )

    body = f"""
    <div class="card">
      <h2>Riwayat Tes Psikologi</h2>
      <p class="muted">Penghapusan bersifat permanen untuk peserta yang dipilih.</p>
      <div style="overflow-x:auto">
        <table>
          <thead>
            <tr><th>Kode</th><th>Nama</th><th>Dibuat</th>
                <th>Selesai</th><th>Aksi</th></tr>
          </thead>
          <tbody>{trs}</tbody>
        </table>
      </div>
      <p>
        <a class="btn" href="{url_for('sipsi.psikologi_mulai')}">Tes Baru</a>
        <a class="btn secondary" href="{url_for('sipsi.psikologi_index')}">Kembali</a>
      </p>
    </div>
    """
    return page(
        "Riwayat Tes Psikologi", body,
        active="psikologi", subtitle="Riwayat kuesioner"
    )


# ================= AKHIR TES PSIKOLOGI 100 ITEM =================


def init_sipsi(app, login_required, has_perm, audit_log=None, get_sidebar=None, COMMON_STYLE=None, BASE_DIR=None):
    """Daftarkan blueprint SIPSI ke aplikasi SIMPATIK."""
    global _BASE_DIR, _DB_PATH, _STATIC_DIR, _login_required, _has_perm, _audit_log, _get_sidebar, _COMMON_STYLE
    _BASE_DIR = BASE_DIR or os.path.dirname(os.path.abspath(__file__))
    _DB_PATH = os.path.join(_BASE_DIR, "sipsida.db")
    _STATIC_DIR = os.path.join(_BASE_DIR, "static", "sipsi")
    os.makedirs(_STATIC_DIR, exist_ok=True)
    # salin logo bawaan modul jika belum ada di static/sipsi
    bundled = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sipsi_assets", "logo.png")
    dest = os.path.join(_STATIC_DIR, "logo.png")
    if not os.path.exists(dest) and os.path.exists(bundled):
        try:
            import shutil
            shutil.copy2(bundled, dest)
        except Exception as e:
            print("sipsi logo copy:", e)
    _login_required = login_required
    _has_perm = has_perm
    _audit_log = audit_log
    _get_sidebar = get_sidebar
    _COMMON_STYLE = COMMON_STYLE
    _init_db()
    # Hindari register ganda jika reloader/double-import
    if "sipsi.index" not in app.view_functions:
        app.register_blueprint(sipsi_bp)
    else:
        print("SIPSI blueprint already registered")

    # Fallback eksplisit di app (jaga-jaga blueprint prefix bermasalah)
    if "sipsi_entry_fallback" not in app.view_functions:
        @app.route("/sipsi", strict_slashes=False)
        @app.route("/sipsi/")
        def sipsi_entry_fallback():
            """Entry point cadangan -&gt; dashboard SIPSI."""
            if not session.get("logged_in"):
                try:
                    return redirect(url_for("login"))
                except Exception:
                    return redirect("/login")
            if _has_perm is not None and not _has_perm("sipsi"):
                flash("Anda tidak memiliki izin menu SIPSI.", "error")
                try:
                    return redirect(url_for("dashboard"))
                except Exception:
                    return redirect("/dashboard")
            # panggil handler index langsung
            return index()

    rules = sorted({r.rule for r in app.url_map.iter_rules() if "sipsi" in r.rule})
    print("SIPSI module registered at /sipsi")
    print("SIPSI routes:", ", ".join(rules))