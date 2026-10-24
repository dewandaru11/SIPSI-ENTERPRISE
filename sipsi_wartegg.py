# -*- coding: utf-8 -*-
"""
SIPSI - Tes Gambar Wartegg (Latihan Digital)
Delapan kotak gambar, form peserta, penyimpanan SQLite,
dan laporan yang dapat dicetak.
"""

import os
import json
import sqlite3
from datetime import datetime

from flask import Blueprint, request, render_template_string

wartegg_bp = Blueprint(
    "wartegg",
    __name__,
    url_prefix="/sipsi/wartegg",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "wartegg_sipsi.db")


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wartegg_hasil (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode TEXT NOT NULL,
            nama TEXT NOT NULL,
            jabatan TEXT,
            instansi TEXT,
            tanggal TEXT NOT NULL,
            gambar_json TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


init_db()


FORM_HTML = r"""
<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tes Wartegg SIPSI</title>

<style>
*{box-sizing:border-box}
body{
    margin:0;
    background:#f3f6fb;
    color:#1d2939;
    font-family:Arial,sans-serif
}
.wrap{max-width:1150px;margin:22px auto;padding:0 14px}
.card{
    background:#fff;
    border-radius:15px;
    padding:20px;
    margin-bottom:16px;
    box-shadow:0 4px 18px rgba(18,59,112,.07)
}
h1,h2{color:#123b70}
.notice{
    background:#eff6ff;
    padding:13px;
    border-left:4px solid #0860d8;
    border-radius:8px;
    line-height:1.6
}
.grid{
    display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:14px
}
.field label{font-size:14px;font-weight:700}
.field input{
    display:block;
    width:100%;
    padding:11px;
    border:1px solid #d0d5dd;
    border-radius:9px;
    margin-top:6px
}
.boards{
    display:grid;
    grid-template-columns:repeat(4,minmax(0,1fr));
    gap:13px
}
.board{
    border:1px solid #d0d5dd;
    border-radius:11px;
    padding:10px;
    min-width:0
}
.board h3{margin:0 0 9px;color:#123b70}
canvas{
    display:block;
    width:100%;
    height:auto;
    aspect-ratio:480/300;
    border:2px solid #333;
    border-radius:3px;
    background:#fff;
    touch-action:none;
    cursor:crosshair
}
.board label{display:block;margin-top:10px;font-size:13px;font-weight:700}
.board input,.board select{
    width:100%;
    padding:9px;
    margin-top:5px;
    border:1px solid #d0d5dd;
    border-radius:7px;
    background:#fff
}
.smallbtn{
    margin-top:8px;
    border:1px solid #d0d5dd;
    padding:7px 10px;
    background:#f8fafc;
    border-radius:7px;
    cursor:pointer
}
.btn{
    border:0;
    border-radius:9px;
    padding:12px 18px;
    background:#0860d8;
    color:#fff;
    font-weight:700;
    cursor:pointer
}
.progress{
    position:sticky;
    top:5px;
    background:white;
    border:1px solid #d0d5dd;
    border-radius:9px;
    padding:10px;
    margin-bottom:12px;
    z-index:3
}
@media(max-width:850px){
    .boards{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media(max-width:500px){
    .grid,.boards{grid-template-columns:1fr}
    .wrap{padding:0 8px;margin:10px auto}
    .card{padding:13px}
}
</style>
</head>

<body>
<div class="wrap">

<div class="card">
    <h1>Tes Gambar Wartegg SIPSI</h1>
    <p>Latihan melengkapi gambar dalam delapan bidang.</p>

    <div class="notice">
        <b>Petunjuk pengerjaan</b><br>
        1. Isi identitas peserta terlebih dahulu.<br>
        2. Kembangkan tanda awal menjadi gambar sesuai imajinasi Anda.<br>
        3. Gunakan mouse, touchpad, atau jari pada layar sentuh.<br>
        4. Isi judul gambar dan urutan pengerjaan jika diperlukan.<br>
        5. Lengkapi semua delapan bidang, kemudian simpan hasil.<br><br>
        Tidak ada jawaban gambar yang dinyatakan benar atau salah.
    </div>
</div>

{% if error %}
<div class="card">
    <p style="color:#b42318">{{ error }}</p>
</div>
{% endif %}

<form id="warteggForm" method="post"
      action="{{ url_for('wartegg.index') }}"
      onsubmit="return simpanGambar()">

<div class="card">
    <h2>Form Identitas Peserta</h2>

    <div class="grid">
        <div class="field">
            <label>Kode Peserta
                <input type="text" name="kode" required maxlength="80">
            </label>
        </div>

        <div class="field">
            <label>Nama Lengkap
                <input type="text" name="nama" required maxlength="150">
            </label>
        </div>

        <div class="field">
            <label>Jabatan / Posisi
                <input type="text" name="jabatan" maxlength="150">
            </label>
        </div>

        <div class="field">
            <label>Instansi / Unit Kerja
                <input type="text" name="instansi" maxlength="150">
            </label>
        </div>
    </div>
</div>

<div class="progress">
    Bidang selesai digambar:
    <b id="progress">0</b> / 8
</div>

<div class="card">
    <h2>Delapan Bidang Gambar</h2>

    <div class="boards">
    {% for n in range(1,9) %}
        <div class="board">
            <h3>Bidang {{ n }}</h3>

            <canvas id="canvas{{ n }}"
                    width="480" height="300"
                    aria-label="Bidang gambar {{ n }}"></canvas>

            <input type="hidden"
                   id="gambar{{ n }}"
                   name="gambar_{{ n }}">

            <button type="button"
                    class="smallbtn"
                    onclick="hapusGambar({{ n }})">
                Hapus gambar
            </button>

            <label>Judul gambar (opsional)
                <input name="judul_{{ n }}"
                       maxlength="120"
                       placeholder="Contoh: Rumah">
            </label>

            <label>Urutan menggambar (opsional)
                <select name="urutan_{{ n }}">
                    <option value="">Belum dipilih</option>
                    {% for urutan in range(1,9) %}
                    <option value="{{ urutan }}">{{ urutan }}</option>
                    {% endfor %}
                </select>
            </label>
        </div>
    {% endfor %}
    </div>
</div>

<div class="card">
    <button class="btn" type="submit">
        Simpan dan Lihat Hasil
    </button>
</div>

</form>
</div>

<script>
const selesai = {};
const sedang = {};
const contexts = {};

/*
  Stimulus sederhana untuk latihan melengkapi gambar.
  Ini bukan reproduksi lembar Wartegg resmi.
*/
function stimulus(ctx, n) {
    const w = 480;
    const h = 300;

    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = "#222222";
    ctx.fillStyle = "#222222";
    ctx.lineWidth = 4;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    if (n === 1) {
        ctx.beginPath();
        ctx.arc(240, 150, 5, 0, Math.PI * 2);
        ctx.fill();
    }

    if (n === 2) {
        ctx.beginPath();
        ctx.moveTo(75, 75);
        ctx.quadraticCurveTo(105, 45, 140, 78);
        ctx.stroke();
    }

    if (n === 3) {
        ctx.beginPath();
        ctx.moveTo(160, 155); ctx.lineTo(160, 120);
        ctx.moveTo(205, 155); ctx.lineTo(205, 100);
        ctx.moveTo(250, 155); ctx.lineTo(250, 80);
        ctx.stroke();
    }

    if (n === 4) {
        ctx.fillRect(335, 45, 22, 22);
    }

    if (n === 5) {
        ctx.beginPath();
        ctx.moveTo(65, 225); ctx.lineTo(125, 185);
        ctx.moveTo(65, 185); ctx.lineTo(125, 225);
        ctx.stroke();
    }

    if (n === 6) {
        ctx.beginPath();
        ctx.moveTo(100, 80); ctx.lineTo(175, 80);
        ctx.moveTo(300, 120); ctx.lineTo(300, 190);
        ctx.stroke();
    }

    if (n === 7) {
        ctx.beginPath();
        for (let i = 0; i < 7; i++) {
            const angle = Math.PI + (Math.PI * i / 6);
            const x = 345 + Math.cos(angle) * 48;
            const y = 225 + Math.sin(angle) * 35;
            ctx.moveTo(x, y);
            ctx.arc(x, y, 3, 0, Math.PI * 2);
        }
        ctx.fill();
    }

    if (n === 8) {
        ctx.beginPath();
        ctx.arc(240, 175, 55, Math.PI, Math.PI * 2);
        ctx.stroke();
    }
}

function mulai(n) {
    const canvas = document.getElementById("canvas" + n);
    const ctx = canvas.getContext("2d");
    contexts[n] = ctx;

    stimulus(ctx, n);
    selesai[n] = false;
    sedang[n] = false;

    canvas.addEventListener("pointerdown", function(e) {
        e.preventDefault();
        sedang[n] = true;
        selesai[n] = true;
        canvas.setPointerCapture(e.pointerId);

        const p = posisi(canvas, e);
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(p.x + 0.1, p.y + 0.1);
        ctx.stroke();

        updateProgress();
    });

    canvas.addEventListener("pointermove", function(e) {
        if (!sedang[n]) return;
        e.preventDefault();

        const p = posisi(canvas, e);
        ctx.lineTo(p.x, p.y);
        ctx.stroke();
    });

    function stop() {
        sedang[n] = false;
        ctx.closePath();
    }

    canvas.addEventListener("pointerup", stop);
    canvas.addEventListener("pointercancel", stop);
    canvas.addEventListener("lostpointercapture", stop);
}

function posisi(canvas, e) {
    const rect = canvas.getBoundingClientRect();
    return {
        x: (e.clientX - rect.left) * canvas.width / rect.width,
        y: (e.clientY - rect.top) * canvas.height / rect.height
    };
}

function hapusGambar(n) {
    stimulus(contexts[n], n);
    selesai[n] = false;
    updateProgress();
}

function updateProgress() {
    let total = 0;
    for (let n = 1; n <= 8; n++) {
        if (selesai[n]) total++;
    }
    document.getElementById("progress").textContent = total;
}

function simpanGambar() {
    for (let n = 1; n <= 8; n++) {
        if (!selesai[n]) {
            alert("Silakan lengkapi gambar pada Bidang " + n + ".");
            return false;
        }

        const canvas = document.getElementById("canvas" + n);
        document.getElementById("gambar" + n).value =
            canvas.toDataURL("image/jpeg", 0.75);
    }

    const pilihan = [];
    for (let n = 1; n <= 8; n++) {
        const v = document.querySelector(
            '[name="urutan_' + n + '"]'
        ).value;
        if (v) pilihan.push(v);
    }

    if (new Set(pilihan).size !== pilihan.length) {
        alert("Urutan gambar yang dipilih tidak boleh sama.");
        return false;
    }

    return confirm("Simpan delapan gambar dan tampilkan laporan?");
}

for (let n = 1; n <= 8; n++) mulai(n);
</script>
</body>
</html>
"""


RESULT_HTML = r"""
<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Laporan Wartegg SIPSI</title>

<style>
body{
    margin:0;background:#f3f6fb;color:#1d2939;
    font-family:Arial,sans-serif
}
.wrap{max-width:1100px;margin:24px auto;padding:0 14px}
.card{
    background:white;border-radius:12px;padding:20px;
    margin-bottom:15px;box-shadow:0 3px 14px #0000000d
}
h1,h2{color:#123b70}
.info{
    display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
    gap:10px
}
.item{padding:12px;background:#f8fafc;border-radius:8px}
.drawings{
    display:grid;grid-template-columns:repeat(4,minmax(0,1fr));
    gap:12px
}
.drawing{border:1px solid #d0d5dd;padding:8px;border-radius:9px}
.drawing img{display:block;width:100%;height:auto;border:1px solid #333}
button,a{
    display:inline-block;padding:12px 17px;border-radius:8px;
    border:0;background:#0860d8;color:white;
    text-decoration:none;font-weight:bold;cursor:pointer
}
.note{color:#667085;font-size:13px;line-height:1.6}
@media(max-width:700px){
    .drawings{grid-template-columns:repeat(2,minmax(0,1fr))}
    .info{grid-template-columns:1fr}
}
@media print{
    body{background:white}
    .wrap{max-width:none;margin:0;padding:0}
    .card{box-shadow:none;border:1px solid #ddd;break-inside:avoid}
    .actions{display:none}
}
</style>
</head>

<body>
<div class="wrap">
    <div class="card">
        <h1>LAPORAN TES GAMBAR WARTEGG</h1>
        <div class="info">
            <div class="item"><b>Kode peserta</b><br>{{ data.kode }}</div>
            <div class="item"><b>Nama peserta</b><br>{{ data.nama }}</div>
            <div class="item"><b>Jabatan</b><br>{{ data.jabatan or "-" }}</div>
            <div class="item"><b>Instansi</b><br>{{ data.instansi or "-" }}</div>
            <div class="item"><b>Tanggal tes</b><br>{{ data.tanggal }}</div>
            <div class="item"><b>Bidang tersimpan</b><br>8 dari 8</div>
        </div>
    </div>

    <div class="card">
        <h2>Dokumentasi Gambar Peserta</h2>
        <div class="drawings">
        {% for d in gambar %}
            <div class="drawing">
                <b>Bidang {{ d.nomor }}</b>
                <img src="{{ d.image }}" alt="Gambar bidang {{ d.nomor }}">
                <p><b>Judul:</b> {{ d.judul or "-" }}</p>
                <p><b>Urutan:</b> {{ d.urutan or "-" }}</p>
            </div>
        {% endfor %}
        </div>
    </div>

    <div class="card">
        <h2>Catatan Evaluasi</h2>
        <p>
            Delapan bidang gambar telah disimpan sebagai dokumentasi peserta.
            Laporan ini tidak menetapkan skor kepribadian secara otomatis.
        </p>
        <p class="note">
            Penafsiran psikologis memerlukan metode penilaian yang sesuai
            dan profesional yang kompeten. Gambar tidak boleh digunakan
            sendirian untuk membuat diagnosis ataupun keputusan kepegawaian.
        </p>
    </div>

    <div class="card actions">
        <button onclick="window.print()">Cetak Laporan</button>
        <a href="{{ url_for('wartegg.index') }}">Tes Baru</a>
    </div>
</div>
</body>
</html>
"""


@wartegg_bp.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template_string(FORM_HTML, error=None)

    kode = request.form.get("kode", "").strip()
    nama = request.form.get("nama", "").strip()
    jabatan = request.form.get("jabatan", "").strip()
    instansi = request.form.get("instansi", "").strip()

    if not kode or not nama:
        return render_template_string(
            FORM_HTML,
            error="Kode peserta dan nama wajib diisi.",
        ), 400

    gambar = []

    for n in range(1, 9):
        image = request.form.get(f"gambar_{n}", "")

        if (
            not image.startswith("data:image/jpeg;base64,")
            or len(image) > 1_000_000
        ):
            return (
                f"Gambar bidang {n} tidak valid. Silakan ulangi tes.",
                400,
            )

        gambar.append({
            "nomor": n,
            "image": image,
            "judul": request.form.get(f"judul_{n}", "").strip(),
            "urutan": request.form.get(f"urutan_{n}", "").strip(),
        })

    urutan = [g["urutan"] for g in gambar if g["urutan"]]

    if len(urutan) != len(set(urutan)):
        return "Urutan menggambar tidak boleh duplikat.", 400

    tanggal = datetime.now().strftime("%d-%m-%Y %H:%M")

    data = {
        "kode": kode,
        "nama": nama,
        "jabatan": jabatan,
        "instansi": instansi,
        "tanggal": tanggal,
    }

    conn = get_db()

    try:
        conn.execute(
            """
            INSERT INTO wartegg_hasil
            (kode, nama, jabatan, instansi, tanggal, gambar_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                kode,
                nama,
                jabatan,
                instansi,
                tanggal,
                json.dumps(gambar, ensure_ascii=False),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return render_template_string(
        RESULT_HTML,
        data=data,
        gambar=gambar,
    )