from pathlib import Path
import py_compile
import shutil
import re

path = Path("sipsi_mod.py")
if not path.exists():
    raise SystemExit("GAGAL: sipsi_mod.py tidak ditemukan.")

source = path.read_text(encoding="utf-8")

start_marker = '@sipsi_bp.route("/psikologi/riwayat", methods=["GET"], strict_slashes=False)'
end_marker = "# ================= AKHIR TES PSIKOLOGI 100 ITEM ================="

start = source.find(start_marker)
end = source.find(end_marker, start + 1)

if start < 0 or end < 0 or end <= start:
    raise SystemExit("GAGAL: batas bagian riwayat tidak ditemukan. File tidak diubah.")

backup = Path("sipsi_mod.py.backup-sebelum-hapus-riwayat")
if not backup.exists():
    shutil.copy2(path, backup)

replacement = '''@sipsi_bp.route("/psikologi/hapus/<int:pid>", methods=["POST"], strict_slashes=False)
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


'''

updated = source[:start] + replacement + source[end:]

# Tulis sementara lalu periksa sintaks sebelum mengganti file utama.
temp = Path("sipsi_mod.py.tmp")
temp.write_text(updated, encoding="utf-8")
try:
    py_compile.compile(str(temp), doraise=True)
except Exception:
    temp.unlink(missing_ok=True)
    raise SystemExit("GAGAL: pemeriksaan sintaks tidak lolos. File utama tidak diubah.")

shutil.copy2(temp, path)
temp.unlink(missing_ok=True)

# Periksa kembali file yang sudah dipasang.
py_compile.compile(str(path), doraise=True)
print("BERHASIL: fitur hapus riwayat psikologi terpasang.")
print("Cadangan: " + str(backup))
print("Pemeriksaan sintaks Python: LULUS")
