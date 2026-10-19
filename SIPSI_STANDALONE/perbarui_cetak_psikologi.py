from pathlib import Path
import re

path = Path("sipsi_mod.py")
source = path.read_text(encoding="utf-8")

start_marker = '@sipsi_bp.route("/psikologi/hasil/<int:pid>", methods=["GET"], strict_slashes=False)'
end_marker = '@sipsi_bp.route("/psikologi/riwayat", methods=["GET"], strict_slashes=False)'

start = source.find(start_marker)
end = source.find(end_marker, start + 1)

if start < 0 or end < 0 or end <= start:
    raise SystemExit("GAGAL: batas fungsi hasil psikologi tidak ditemukan. File tidak diubah.")

replacement = '''@sipsi_bp.route("/psikologi/hasil/<int:pid>", methods=["GET"], strict_slashes=False)
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


'''

updated = source[:start] + replacement + source[end:]
path.write_text(updated, encoding="utf-8")
print("Berhasil mengganti fungsi psikologi_hasil(pid) saja.")
