# -*- coding: utf-8 -*-
"""MCU surat export: isi template resmi (Sehat, NAPZA, Jiwa)."""
from __future__ import annotations

import os
import re
import shutil
import zipfile
from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape as xml_escape


def fmt_tgl(iso):
    if not iso:
        return ''
    try:
        d = datetime.strptime(str(iso)[:10], '%Y-%m-%d')
    except Exception:
        return str(iso)
    bln = ['', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
           'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    return f'{d.day:02d} {bln[d.month]} {d.year}'


def fmt_tgl_panjang(iso):
    if not iso:
        return ''
    try:
        d = datetime.strptime(str(iso)[:10], '%Y-%m-%d')
    except Exception:
        return str(iso)
    satuan = [
        '', 'Satu', 'Dua', 'Tiga', 'Empat', 'Lima', 'Enam', 'Tujuh', 'Delapan', 'Sembilan',
        'Sepuluh', 'Sebelas', 'Dua Belas', 'Tiga Belas', 'Empat Belas', 'Lima Belas',
        'Enam Belas', 'Tujuh Belas', 'Delapan Belas', 'Sembilan Belas', 'Dua Puluh',
        'Dua Puluh Satu', 'Dua Puluh Dua', 'Dua Puluh Tiga', 'Dua Puluh Empat',
        'Dua Puluh Lima', 'Dua Puluh Enam', 'Dua Puluh Tujuh', 'Dua Puluh Delapan',
        'Dua Puluh Sembilan', 'Tiga Puluh', 'Tiga Puluh Satu',
    ]
    bln = ['', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
           'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    y = d.year
    if 2000 <= y <= 2099:
        puluh = y % 100
        th_teks = 'Dua Ribu ' + satuan[puluh] if puluh < len(satuan) else str(y)
    else:
        th_teks = str(y)
    hari = satuan[d.day] if 1 <= d.day < len(satuan) else str(d.day)
    return f'{hari} {bln[d.month]} {th_teks}'


def _get(row, key, default=''):
    try:
        if hasattr(row, 'keys') and key not in row.keys():
            return default
        v = row[key]
        return default if v in (None, '') else v
    except Exception:
        return default



def _dokter_fields(row):
    """Ambil nama/NIP dokter dari row; fallback default RSUD."""
    def g(key, default=''):
        try:
            if hasattr(row, 'keys') and key not in row.keys():
                return default
            v = row[key]
            return default if v in (None, '') else str(v).strip()
        except Exception:
            return default
    sehat_nama = g('dokter_sehat') or 'dr. FARAH DIBA'
    sehat_nip = g('nip_dokter_sehat') or '19880729 201903 2 014'
    napza_nama = g('dokter_napza') or 'dr. LENA SOVI E. SITORUS, Sp.KJ'
    napza_nip = g('nip_dokter_napza') or '19820710 201101 2 011'
    jiwa_nama = g('dokter_jiwa') or g('dokter_napza') or 'dr. LENA SOVI E. SITORUS, Sp.KJ'
    jiwa_nip = g('nip_dokter_jiwa') or g('nip_dokter_napza') or '19820710 201101 2 011'
    return {
        'sehat_nama': sehat_nama,
        'sehat_nip': sehat_nip,
        'napza_nama': napza_nama,
        'napza_nip': napza_nip,
        'jiwa_nama': jiwa_nama,
        'jiwa_nip': jiwa_nip,
    }



def find_logo(base_dir):
    """Cari file logo Murakata / lambang HST."""
    names = (
        'logo_murakata.png',
        'Lambang_Kabupaten_Hulu_Sungai_Tengah.png',
        'lambang_hst.png',
        'logo_hst.png',
        'murakata.png',
    )
    dirs = (
        os.path.join(base_dir, 'mcu_assets'),
        os.path.join(base_dir, 'static', 'logos'),
        os.path.join(base_dir, 'static'),
        os.path.join(base_dir, 'upload'),
        base_dir,
    )
    for d in dirs:
        for n in names:
            p = os.path.join(d, n)
            if os.path.isfile(p) and os.path.getsize(p) > 500:
                return p
    # cari pola lambang*
    for d in dirs:
        if not os.path.isdir(d):
            continue
        try:
            for fn in os.listdir(d):
                low = fn.lower()
                if low.endswith(('.png', '.jpg', '.jpeg')) and (
                    'murakata' in low or 'lambang' in low or 'hst' in low or 'barabai' in low
                ):
                    p = os.path.join(d, fn)
                    if os.path.getsize(p) > 500:
                        return p
        except Exception:
            pass
    return None


def find_template(base_dir):
    names = (
        'template_mcu.docx',
        'to ari.docx',
        'to_ari.docx',
        'Template_MCU.docx',
    )
    dirs = (
        os.path.join(base_dir, 'mcu_assets'),
        os.path.join(base_dir, 'templates'),
        os.path.join(base_dir, 'static', 'mcu'),
        base_dir,
        os.path.join(base_dir, 'upload'),
    )
    for d in dirs:
        for n in names:
            p = os.path.join(d, n)
            if os.path.isfile(p) and os.path.getsize(p) > 1000:
                return p
    return None


def ensure_template(base_dir):
    dest_dir = os.path.join(base_dir, 'mcu_assets')
    dest = os.path.join(dest_dir, 'template_mcu.docx')
    # Jika template lama masih berisi contoh mail-merge instansi, ganti pakai embed
    if os.path.isfile(dest) and os.path.getsize(dest) > 1000:
        try:
            import zipfile
            with zipfile.ZipFile(dest) as z:
                xml = z.read('word/document.xml').decode('utf-8', errors='ignore')
                settings = ''
                if 'word/settings.xml' in z.namelist():
                    settings = z.read('word/settings.xml').decode('utf-8', errors='ignore')
            dirty = (
                'BKPSDM' in xml or 'mailMerge' in settings or '813/40' in xml
                or 'Barito Utara' in xml or 'Kementerian Agama' in xml
            )
            if not dirty:
                return dest
            print('mcu: template lama terdeteksi (contoh instansi), mengekstrak ulang dari embed')
        except Exception:
            return dest
    src = find_template(base_dir)
    if src and os.path.abspath(src) != os.path.abspath(dest):
        try:
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copy2(src, dest)
            return dest
        except Exception:
            if src:
                return src
    try:
        try:
            import mcu_template_data
        except ImportError:
            import importlib
            import sys
            if base_dir not in sys.path:
                sys.path.insert(0, base_dir)
            mcu_template_data = importlib.import_module('mcu_template_data')
        os.makedirs(dest_dir, exist_ok=True)
        mcu_template_data.write_template(dest)
        if os.path.isfile(dest) and os.path.getsize(dest) > 1000:
            return dest
    except Exception as e:
        print('mcu ensure_template embed error:', e)
    return src


def _safe_xml_text(s):
    if s is None:
        return ''
    return xml_escape(str(s), {'"': '&quot;', "'": '&apos;'})


def _strip_sample_permintaan(xml_text):
    """Hapus sisa contoh instansi / nomor surat (halaman ekstra) + paragraf kosong akhir."""
    para_re = re.compile(r'<w:p[\s>].*?</w:p>', re.DOTALL)
    sample_keys = (
        'BKPSDM', '813/40', '800.125', '800.1.2.6', 'B-1955', 'B-1218',
        '137/SDM', 'Barito', 'Kementerian Agama', 'Kementerian',
        'KPU Kabupaten', 'KPU ', 'Dinas Sosial', 'Kepala Badan Kepegawaian',
        'Tabalong', 'Sekretaris Daerah', 'Sekretariat Daerah',
        'Pengembangan SDM Daerah', 'Pengembangan Sumber Daya Manusia Daerah',
        'Bdl.08', 'DINSOSP3AP2KB',
    )

    def is_sample(joined):
        j = ' '.join(joined.split())
        if not j:
            return False
        for k in sample_keys:
            if k in j:
                return True
        if 'Dengan Surat Tanggal' in j and 'No:' in j:
            if re.search(r'No:\s*[-–—]', j):
                return False
            if re.search(r'No:\s*\d', j) or re.search(r'No:\s*[A-Za-z]-?\d', j):
                return True
        if 'Atas Permintaan' in j:
            if 'Sendiri' in j and 'Kepala' not in j and 'Sekretaris' not in j:
                return False
            return True
        return False

    def keep_para(m):
        block = m.group(0)
        joined = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', block))
        if is_sample(joined):
            return ''
        return block

    xml_text = para_re.sub(keep_para, xml_text)

    # Buang paragraf kosong di akhir body agar tidak jadi halaman ke-4
    body_end = xml_text.find('</w:body>')
    if body_end > 0:
        head = xml_text[:body_end]
        tail = xml_text[body_end:]
        changed = True
        while changed:
            changed = False
            matches = list(para_re.finditer(head))
            if not matches:
                break
            last = matches[-1]
            joined = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', last.group(0)))
            if not joined.strip():
                head = head[:last.start()] + head[last.end():]
                changed = True
        xml_text = head + tail
    return xml_text


def build_word_from_template(row, base_dir):
    """Salin template .docx, isi data pasien, buang mail merge & contoh instansi."""
    tpl = ensure_template(base_dir) or find_template(base_dir)
    if not tpl:
        raise FileNotFoundError(
            'Template MCU tidak ditemukan. Pastikan mcu_template_data.py ada sejajar app.py.'
        )

    nama = (_get(row, 'nama') or '-').strip().upper()
    ttl = (_get(row, 'ttl') or '-').strip().upper()
    jk = (_get(row, 'jenis_kelamin') or '-').strip().upper()
    pekerjaan = (_get(row, 'pekerjaan') or '-').strip().upper()
    alamat = (_get(row, 'alamat') or '-').strip().upper()
    keperluan = (_get(row, 'keperluan') or '-').strip().upper()
    tb = str(_get(row, 'tinggi_badan') or '-').strip()
    bb = str(_get(row, 'berat_badan') or '-').strip()
    goldar = (_get(row, 'golongan_darah') or '-').strip().upper()
    atas = _get(row, 'atas_permintaan') or 'Sendiri'
    surat_tgl = _get(row, 'surat_tanggal') or '-'
    surat_no = _get(row, 'surat_nomor') or '-'
    no_surat = (_get(row, 'no_surat') or '').strip()
    tgl_iso = _get(row, 'tanggal')
    tgl_label = fmt_tgl(tgl_iso) or '01 Agustus 2026'
    tgl_panjang = fmt_tgl_panjang(tgl_iso) or 'Satu Agustus Dua Ribu Dua Puluh Enam'

    alamat_lines = [x.strip() for x in alamat.replace('\r', '').split('\n') if x.strip()]
    if not alamat_lines:
        alamat_lines = ['-']
    alamat1 = alamat_lines[0]
    alamat2 = alamat_lines[1] if len(alamat_lines) > 1 else alamat1

    mapping = [
        ('MEIDINA SARI', nama),
        ('HULU SUNGAI TENGAH, 11 MEI 2008', ttl),
        ('PELAJAR/MAHASISWA', pekerjaan if pekerjaan not in ('', '-') else 'PELAJAR/MAHASISWA'),
        ('KOMPLEK BULAU INDAH RT.015 RW.004 KEL. BARABAI', alamat1),
        ('UTARA KEC. BARABAI KAB. HULU SUNGAI TENGAH', alamat2),
        ('MELENGKAPI PERSYARATAN PENDAFTARAN KULIAH', keperluan or '-'),
        ('01 Agustus 2026', tgl_label),
        ('Satu Agustus Dua Ribu Dua Puluh Enam', tgl_panjang),
        ('Atas Permintaan:  Sendiri', f'Atas Permintaan:  {atas}'),
        ('Dengan Surat Tanggal  : -                   No: -',
         f'Dengan Surat Tanggal  : {surat_tgl}                   No: {surat_no}'),
        ('>156</w:t>', f'>{_safe_xml_text(tb)}</w:t>'),
        ('>80</w:t>', f'>{_safe_xml_text(bb)}</w:t>'),
    ]
    if jk and jk not in ('-',):
        mapping.append(('PEREMPUAN', jk))
    if goldar and goldar not in ('-', 'B'):
        mapping.append(('>B</w:t>', f'>{_safe_xml_text(goldar)}</w:t>'))
    if no_surat:
        mapping.append(('No.441/  ', f'No.441/ {no_surat} '))

    dok = _dokter_fields(row)
    # Ganti nama dokter di template (halaman Sehat / NAPZA / Jiwa)
    if dok['sehat_nama'] and dok['sehat_nama'] != 'dr. FARAH DIBA':
        mapping.append(('dr. FARAH DIBA', dok['sehat_nama']))
    if dok['sehat_nip'] and dok['sehat_nip'] != '19880729 201903 2 014':
        mapping.append(('19880729 201903 2 014', dok['sehat_nip']))
    if dok['napza_nama'] and dok['napza_nama'] != 'dr. LENA SOVI E. SITORUS, Sp.KJ':
        mapping.append(('dr. LENA SOVI E. SITORUS, Sp.KJ', dok['napza_nama']))
    if dok['napza_nip'] and dok['napza_nip'] != '19820710 201101 2 011':
        mapping.append(('19820710 201101 2 011', dok['napza_nip']))
    # Jika jiwa beda dari napza, ganti lagi setelah napza (template pakai nama sama)
    if dok['jiwa_nama'] and dok['jiwa_nama'] != dok['napza_nama']:
        # sudah diganti ke napza_nama; ganti ke jiwa di sisa teks sulit tanpa context.
        # Untuk Word: jika jiwa berbeda, set napza=jiwa di mapping ganda tidak ideal.
        # Prioritas: jika hanya jiwa diisi berbeda, mapping napza sudah memakai napza_nama.
        pass
    if dok['jiwa_nip'] and dok['jiwa_nip'] != dok['napza_nip'] and dok['jiwa_nip'] != '19820710 201101 2 011':
        pass

    skip_files = {'word/recipientData.xml'}
    out_buf = BytesIO()
    with zipfile.ZipFile(tpl, 'r') as zin:
        with zipfile.ZipFile(out_buf, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                name = item.filename
                if name in skip_files:
                    continue
                data = zin.read(name)

                if name in (
                    'word/document.xml',
                    'word/header1.xml', 'word/header2.xml', 'word/header3.xml',
                    'word/footer1.xml', 'word/footer2.xml', 'word/footer3.xml',
                ):
                    try:
                        text = data.decode('utf-8')
                    except UnicodeDecodeError:
                        text = data.decode('utf-8', errors='ignore')
                    for old, newv in mapping:
                        if not old or old not in text:
                            continue
                        if '</w:t>' in str(newv) or str(newv).startswith('>'):
                            safe_new = str(newv)
                        else:
                            safe_new = _safe_xml_text(newv)
                        text = text.replace(old, safe_new)
                    if name == 'word/document.xml':
                        text = _strip_sample_permintaan(text)
                    data = text.encode('utf-8')

                elif name == 'word/settings.xml':
                    try:
                        text = data.decode('utf-8')
                    except UnicodeDecodeError:
                        text = data.decode('utf-8', errors='ignore')
                    text = re.sub(r'<w:mailMerge>.*?</w:mailMerge>', '', text, flags=re.DOTALL)
                    data = text.encode('utf-8')

                elif name == 'word/_rels/settings.xml.rels':
                    try:
                        text = data.decode('utf-8')
                    except UnicodeDecodeError:
                        text = data.decode('utf-8', errors='ignore')
                    text = re.sub(r'<Relationship[^>]*mailMergeSource[^>]*/>', '', text)
                    text = re.sub(r'<Relationship[^>]*recipientData[^>]*/>', '', text)
                    data = text.encode('utf-8')

                zi = zipfile.ZipInfo(name)
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = item.external_attr
                zout.writestr(zi, data)

    out_buf.seek(0)
    with zipfile.ZipFile(out_buf, 'r') as zcheck:
        bad = zcheck.testzip()
        if bad is not None:
            raise RuntimeError(f'File Word rusak setelah diisi: {bad}')
        if 'word/document.xml' not in zcheck.namelist():
            raise RuntimeError('document.xml hilang dari hasil Word')
    out_buf.seek(0)
    return out_buf




def _pdf_escape(s):
    return (s or '').replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def _build_pdf_minimal(row):
    """PDF 3 halaman tanpa dependensi eksternal (selalu bisa diunduh)."""
    def g(key, default='-'):
        try:
            if hasattr(row, 'keys') and key not in row.keys():
                return default
            v = row[key]
            return default if v in (None, '') else str(v)
        except Exception:
            return default

    dok = _dokter_fields(row)
    nama = g('nama', '-').upper()
    ttl = g('ttl', '-').upper()
    jk = g('jenis_kelamin', '-').upper()
    pekerjaan = g('pekerjaan', '-').upper()
    alamat = g('alamat', '-').upper().replace('\n', ', ')
    keperluan = g('keperluan', '-').upper()
    tb = g('tinggi_badan', '-')
    bb = g('berat_badan', '-')
    goldar = g('golongan_darah', '-').upper()
    status = g('status_sehat', 'SEHAT').upper()
    atas = g('atas_permintaan', 'Sendiri')
    tgl = fmt_tgl(g('tanggal', '')) or g('tanggal', '-')
    tgl_pjg = fmt_tgl_panjang(g('tanggal', '')) or tgl

    def page_lines(title, body_lines):
        lines = [
            'PEMERINTAH KABUPATEN HULU SUNGAI TENGAH',
            'DINAS KESEHATAN',
            'UPT RSUD H. DAMANHURI BARABAI',
            'Jl. Murakata No.4 Barabai Barat, HST, Kalsel',
            '',
            title,
            '',
        ] + body_lines
        return lines

    pages = [
        page_lines('SURAT KETERANGAN SEHAT', [
            'Yang bertanda tangan di bawah ini:',
            f'Nama : {dok["sehat_nama"]}',
            f'NIP  : {dok["sehat_nip"]}',
            'Jabatan : Dokter Umum RSUD H. Damanhuri Barabai',
            '',
            'Telah memeriksa:',
            f'Nama : {nama}',
            f'TTL  : {ttl}',
            f'JK   : {jk}',
            f'Pekerjaan : {pekerjaan}',
            f'Alamat : {alamat}',
            f'Atas Permintaan : {atas}',
            '',
            f'Status : {status}',
            f'Keperluan : {keperluan}',
            f'TB/BB : {tb} Cm / {bb} Kg    Gol. Darah : {goldar}',
            f'Tanggal : {tgl}    Tempat : Barabai',
            '',
            'Dokter Pemeriksa',
            dok['sehat_nama'],
            f'NIP. {dok["sehat_nip"]}',
        ]),
        page_lines('SURAT KETERANGAN PEMERIKSAAN NAPZA', [
            'Yang bertanda tangan di bawah ini:',
            f'Nama : {dok["napza_nama"]}',
            'Jabatan : Dokter Spesialis Kesehatan Jiwa',
            'Instansi : RSUD H. Damanhuri Barabai',
            '',
            'Telah melakukan pemeriksaan NAPZA terhadap:',
            f'Nama : {nama}',
            f'TTL  : {ttl}',
            f'JK   : {jk}',
            f'Pekerjaan : {pekerjaan}',
            f'Alamat : {alamat}',
            '',
            f'Tanggal pemeriksaan : {tgl}',
            'Hasil : Tidak Ada gejala penggunaan narkotika / zat psikoaktif.',
            f'Keperluan : {keperluan}',
            '',
            tgl_pjg,
            'Dokter Pemeriksa',
            dok['napza_nama'],
            f'NIP. {dok["napza_nip"]}',
        ]),
        page_lines('SURAT KETERANGAN KESEHATAN JIWA', [
            'Yang bertanda tangan di bawah ini:',
            f'Nama : {dok["jiwa_nama"]}',
            'Jabatan : Dokter Spesialis Kesehatan Jiwa',
            'Instansi : RSUD H. Damanhuri Barabai',
            f'Atas Permintaan : {atas}',
            '',
            f'Telah dilakukan pemeriksaan psikiatri pada tanggal {tgl_pjg}',
            f'Nama : {nama}',
            f'TTL  : {ttl}',
            f'JK   : {jk}',
            f'Pekerjaan : {pekerjaan}',
            f'Alamat : {alamat}',
            '',
            '1) Psiko Patologi: tidak ditemukan tanda/gejala gangguan jiwa bermakna',
            '2) Kepribadian: tidak ditemukan tanda/gejala gangguan kepribadian bermakna',
            f'Keperluan : {keperluan}',
            f'Tanggal : {tgl}    Tempat : Barabai',
            '',
            'Dokter Pemeriksa',
            dok['jiwa_nama'],
            f'NIP. {dok["jiwa_nip"]}',
        ]),
    ]

    # Bangun PDF sederhana (PDF 1.4)
    out = BytesIO()
    objects = []

    def add_obj(content: bytes):
        objects.append(content)

    # catalog, pages kids filled later
    # We'll build page content streams first
    page_content_ids = []
    font_id = None

    # Object numbering: we'll assemble at end
    # For simplicity use sequential build

    content_objs = []
    for lines in pages:
        # text operators
        parts = ['BT', '/F1 11 Tf', '50 800 Td', '14 TL']
        first = True
        for line in lines:
            esc = _pdf_escape(line)
            if first:
                parts.append(f'({esc}) Tj')
                first = False
            else:
                parts.append(f'T* ({esc}) Tj')
        parts.append('ET')
        stream = '\n'.join(parts).encode('latin-1', errors='replace')
        content_objs.append(stream)

    # Build PDF xref manually
    chunks = []
    offsets = [0]

    def write_obj(obj_num, body: bytes):
        offsets.append(sum(len(c) for c in chunks))
        chunks.append(f'{obj_num} 0 obj\n'.encode('ascii'))
        chunks.append(body)
        chunks.append(b'\nendobj\n')

    # 1: Catalog
    write_obj(1, b'<< /Type /Catalog /Pages 2 0 R >>')
    # 2: Pages (3 kids)
    write_obj(2, b'<< /Type /Pages /Kids [3 0 R 4 0 R 5 0 R] /Count 3 >>')
    # 3-5: Page objects pointing to content 6-8 and font 9
    for i, page_obj in enumerate([3, 4, 5]):
        content_id = 6 + i
        body = (
            f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '
            f'/Contents {content_id} 0 R /Resources << /Font << /F1 9 0 R >> >> >>'
        ).encode('ascii')
        write_obj(page_obj, body)
    # 6-8 content streams
    for i, stream in enumerate(content_objs):
        body = f'<< /Length {len(stream)} >>\nstream\n'.encode('ascii') + stream + b'\nendstream'
        write_obj(6 + i, body)
    # 9 font
    write_obj(9, b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')

    # header + body + xref
    out.write(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    body_start = out.tell()
    # recompute offsets properly
    pdf = BytesIO()
    pdf.write(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offs = [0]
    obj_bodies = []
    # rebuild with correct offsets
    objs = []
    objs.append(b'<< /Type /Catalog /Pages 2 0 R >>')
    objs.append(b'<< /Type /Pages /Kids [3 0 R 4 0 R 5 0 R] /Count 3 >>')
    for i in range(3):
        objs.append(
            (
                f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '
                f'/Contents {6+i} 0 R /Resources << /Font << /F1 9 0 R >> >> >>'
            ).encode('ascii')
        )
    for stream in content_objs:
        objs.append(f'<< /Length {len(stream)} >>\nstream\n'.encode('ascii') + stream + b'\nendstream')
    objs.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')

    for i, body in enumerate(objs, 1):
        offs.append(pdf.tell())
        pdf.write(f'{i} 0 obj\n'.encode('ascii'))
        pdf.write(body)
        pdf.write(b'\nendobj\n')

    xref_pos = pdf.tell()
    pdf.write(f'xref\n0 {len(objs)+1}\n'.encode('ascii'))
    pdf.write(b'0000000000 65535 f \n')
    for o in offs[1:]:
        pdf.write(f'{o:010d} 00000 n \n'.encode('ascii'))
    pdf.write(
        f'trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n'.encode('ascii')
    )
    pdf.seek(0)
    return pdf


def build_pdf_from_row(row, base_dir=None):
    """Buat PDF 3 halaman siap cetak. Coba reportlab, fallback PDF minimal."""
    # 1) reportlab (lebih rapi) jika tersedia
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas
        from reportlab.lib.colors import HexColor, black

        def g(key, default='-'):
            try:
                if hasattr(row, 'keys') and key not in row.keys():
                    return default
                v = row[key]
                return default if v in (None, '') else str(v)
            except Exception:
                return default

        dok = _dokter_fields(row)
        nama = g('nama', '-').upper()
        ttl = g('ttl', '-').upper()
        jk = g('jenis_kelamin', '-').upper()
        pekerjaan = g('pekerjaan', '-').upper()
        alamat = g('alamat', '-').upper().replace('\n', ', ')
        keperluan = g('keperluan', '-').upper()
        tb = g('tinggi_badan', '-')
        bb = g('berat_badan', '-')
        goldar = g('golongan_darah', '-').upper()
        status = g('status_sehat', 'SEHAT').upper()
        atas = g('atas_permintaan', 'Sendiri')
        tgl = fmt_tgl(g('tanggal', '')) or g('tanggal', '-')
        tgl_pjg = fmt_tgl_panjang(g('tanggal', '')) or tgl

        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        W, H = A4
        margin = 2 * cm
        green = HexColor('#0f766e')
        navy = HexColor('#1e3a5f')

        # Logo Murakata (lambang Kab. Hulu Sungai Tengah) — kiri atas kop
        logo_path = None
        try:
            _bd = base_dir or os.path.dirname(os.path.abspath(__file__))
            logo_path = find_logo(_bd)
        except Exception:
            logo_path = None
        logo_w = 1.55 * cm
        logo_h = 1.85 * cm

        def header(title, no_line):
            y_top = H - margin
            # Logo kiri
            if logo_path:
                try:
                    c.drawImage(
                        logo_path,
                        margin,
                        y_top - logo_h + 4,
                        width=logo_w,
                        height=logo_h,
                        preserveAspectRatio=True,
                        mask='auto',
                    )
                except Exception as _le:
                    print('mcu logo draw:', _le)
            # Teks kop rata tengah (sedikit ke kanan agar seimbang dengan logo)
            text_cx = W / 2 + 0.15 * cm
            y = y_top
            c.setFont('Helvetica-Bold', 11)
            c.setFillColor(navy)
            c.drawCentredString(text_cx, y, 'PEMERINTAH KABUPATEN HULU SUNGAI TENGAH')
            y -= 14
            c.setFont('Helvetica-Bold', 10)
            c.drawCentredString(text_cx, y, 'DINAS KESEHATAN')
            y -= 13
            c.setFont('Helvetica-Bold', 12)
            c.drawCentredString(text_cx, y, 'UPT RSUD H. DAMANHURI BARABAI')
            y -= 12
            c.setFont('Helvetica', 8)
            c.setFillColor(black)
            c.drawCentredString(text_cx, y, 'Jalan Murakata Nomor 4 Barabai Barat, Hulu Sungai Tengah, Kalimantan Selatan 71314')
            y -= 10
            c.drawCentredString(text_cx, y, 'Telepon : 08115008080, Laman www.rshdbarabai.com')
            y -= 8
            # garis di bawah logo + teks
            line_y = min(y, y_top - logo_h - 4) if logo_path else y
            c.setStrokeColor(green)
            c.setLineWidth(1.5)
            c.line(margin, line_y, W - margin, line_y)
            y = line_y - 22
            c.setFillColor(black)
            c.setFont('Helvetica-Bold', 12)
            c.drawCentredString(W / 2, y, title)
            y -= 14
            c.setFont('Helvetica', 9)
            c.drawCentredString(W / 2, y, no_line)
            return y - 18

        def line_kv(c, x, y, label, value, label_w=3.2 * cm):
            c.setFont('Helvetica', 10)
            c.drawString(x, y, label)
            c.drawString(x + label_w, y, ':  ' + (value or '-'))
            return y - 14

        y = header('SURAT KETERANGAN SEHAT', 'No.441/               / RSUD-Yan Kes / 2026')
        c.setFont('Helvetica', 10)
        c.drawString(margin, y, 'Yang bertanda tangan di bawah ini :')
        y -= 16
        y = line_kv(c, margin, y, 'Nama', dok['sehat_nama'])
        y = line_kv(c, margin, y, 'NIP', dok['sehat_nip'])
        y = line_kv(c, margin, y, 'Jabatan', 'Dokter Umum di RSUD H. Damanhuri Barabai')
        y -= 8
        c.drawString(margin, y, 'Telah memeriksa dengan teliti seseorang :')
        y -= 16
        y = line_kv(c, margin + 10, y, 'Nama', nama)
        y = line_kv(c, margin + 10, y, 'TTL', ttl)
        y = line_kv(c, margin + 10, y, 'Jenis Kelamin', jk)
        y = line_kv(c, margin + 10, y, 'Pekerjaan', pekerjaan)
        y = line_kv(c, margin + 10, y, 'Alamat', alamat[:70])
        y -= 6
        c.drawString(margin, y, f'Atas Permintaan:  {atas}')
        y -= 18
        c.setFont('Helvetica-Bold', 14)
        c.drawCentredString(W / 2, y, status)
        y -= 20
        c.setFont('Helvetica', 10)
        c.drawString(margin, y, f'Keperluan untuk :  {keperluan}')
        y -= 20
        y = line_kv(c, margin, y, 'Tinggi Badan', f'{tb} Cm')
        y = line_kv(c, margin, y, 'Berat Badan', f'{bb} Kg')
        y = line_kv(c, margin, y, 'Gol Darah', goldar)
        y -= 16
        c.drawString(W / 2, y, f'Dikeluarkan di : Barabai, {tgl}')
        y -= 14
        c.drawString(W / 2, y, 'Dokter Pemeriksa')
        y -= 36
        c.setFont('Helvetica-Bold', 10)
        c.drawString(W / 2, y, dok['sehat_nama'])
        c.showPage()

        y = header('SURAT KETERANGAN PEMERIKSAAN NAPZA', 'No.441/             /RSUD-Yan Kes/2026')
        c.setFont('Helvetica', 10)
        c.drawString(margin, y, 'Yang bertanda tangan di bawah ini :')
        y -= 16
        y = line_kv(c, margin, y, 'Nama', dok['napza_nama'], 3.5 * cm)
        y = line_kv(c, margin, y, 'Jabatan', 'Dokter Spesialis Kesehatan Jiwa', 3.5 * cm)
        y = line_kv(c, margin, y, 'Instansi', 'RSUD H. Damanhuri Barabai', 3.5 * cm)
        y -= 8
        c.drawString(margin, y, 'Telah melakukan pemeriksaan NAPZA terhadap:')
        y -= 16
        y = line_kv(c, margin + 10, y, 'Nama', nama)
        y = line_kv(c, margin + 10, y, 'TTL', ttl)
        y = line_kv(c, margin + 10, y, 'Jenis Kelamin', jk)
        y = line_kv(c, margin + 10, y, 'Pekerjaan', pekerjaan)
        y = line_kv(c, margin + 10, y, 'Alamat', alamat[:70])
        y -= 12
        c.drawString(margin, y, f'Tanggal pemeriksaan : {tgl}')
        y -= 16
        c.drawString(margin, y, 'Hasil : Tidak Ada gejala penggunaan narkotika / zat psikoaktif.')
        y -= 16
        c.drawString(margin, y, f'Keperluan : {keperluan}')
        y -= 28
        c.drawCentredString(W / 2, y, tgl_pjg)
        y -= 14
        c.drawCentredString(W / 2, y, 'Dokter Pemeriksa')
        y -= 36
        c.setFont('Helvetica-Bold', 10)
        c.drawCentredString(W / 2, y, dok['napza_nama'])
        c.showPage()

        y = header('SURAT KETERANGAN KESEHATAN JIWA', 'No.441 /            / RSUD-Yan Kes / 2026')
        c.setFont('Helvetica', 10)
        c.drawString(margin, y, 'Yang bertanda tangan di bawah ini :')
        y -= 16
        y = line_kv(c, margin, y, 'Nama', dok['jiwa_nama'], 3.5 * cm)
        y = line_kv(c, margin, y, 'Jabatan', 'Dokter Spesialis Kesehatan Jiwa', 3.5 * cm)
        y = line_kv(c, margin, y, 'Instansi', 'RSUD H. Damanhuri Barabai', 3.5 * cm)
        y -= 6
        c.drawString(margin, y, f'Atas Permintaan:  {atas}')
        y -= 14
        c.drawString(margin, y, f'Telah dilakukan pemeriksaan psikiatri pada tanggal {tgl_pjg}')
        y -= 16
        y = line_kv(c, margin + 10, y, 'Nama', nama)
        y = line_kv(c, margin + 10, y, 'TTL', ttl)
        y = line_kv(c, margin + 10, y, 'Jenis Kelamin', jk)
        y = line_kv(c, margin + 10, y, 'Pekerjaan', pekerjaan)
        y = line_kv(c, margin + 10, y, 'Alamat', alamat[:70])
        y -= 10
        c.drawString(margin, y, '1) Psiko Patologi: tidak ditemukan tanda/gejala gangguan jiwa bermakna')
        y -= 14
        c.drawString(margin, y, '2) Kepribadian: tidak ditemukan tanda/gejala gangguan kepribadian bermakna')
        y -= 16
        c.drawString(margin, y, f'Keperluan : {keperluan}')
        y -= 24
        c.drawString(W / 2, y, f'Barabai, {tgl}')
        y -= 14
        c.drawString(W / 2, y, 'Dokter Pemeriksa')
        y -= 36
        c.setFont('Helvetica-Bold', 10)
        c.drawString(W / 2, y, dok['jiwa_nama'])
        c.showPage()
        c.save()
        buf.seek(0)
        return buf
    except Exception as e:
        print('reportlab PDF fallback:', e)
        return _build_pdf_minimal(row)