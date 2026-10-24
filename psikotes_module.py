# -*- coding: utf-8 -*-
"""psikotes_module.py — Modul Tes Psikotes 100 Soal + Pola Gambar untuk SIPSI."""
from datetime import datetime
import random
import json as _json
from flask import flash, redirect, request, session, url_for

# ============================================================
# SVG WARTEGG STIMULUS (8 kotak klasik) — versi diperbesar
# ============================================================
def _svg_wartegg(n, size=150):
    """Kotak Wartegg stimulus klasik — ditampilkan sebagai gambar yang jelas."""
    stim = {
        1: '<circle cx="50" cy="50" r="4" fill="#000"/>',
        2: '<path d="M 20,50 Q 35,35 50,50 T 80,50" fill="none" stroke="#000" stroke-width="3"/>',
        3: '<line x1="30" y1="25" x2="30" y2="75" stroke="#000" stroke-width="2.5"/>'
           '<line x1="42" y1="25" x2="42" y2="75" stroke="#000" stroke-width="2.5"/>'
           '<line x1="54" y1="25" x2="54" y2="75" stroke="#000" stroke-width="2.5"/>',
        4: '<rect x="38" y="38" width="24" height="24" fill="#000"/>',
        5: '<line x1="25" y1="70" x2="70" y2="25" stroke="#000" stroke-width="3"/>'
           '<line x1="35" y1="80" x2="80" y2="35" stroke="#000" stroke-width="3"/>',
        6: '<line x1="50" y1="20" x2="50" y2="50" stroke="#000" stroke-width="3"/>'
           '<line x1="50" y1="50" x2="80" y2="50" stroke="#000" stroke-width="3"/>',
        7: '<path d="M 25,75 Q 25,25 50,25 Q 75,25 75,75" fill="none" stroke="#000" stroke-width="3"/>',
        8: '<path d="M 25,70 Q 25,30 75,30" fill="none" stroke="#000" stroke-width="3"/>',
    }
    return (
        '<div style="display:block;text-align:center;margin:14px auto;'
        'padding:10px;background:#f8fafc;border-radius:10px;max-width:220px">'
        f'<svg width="{size}" height="{size}" viewBox="0 0 100 100" '
        'xmlns="http://www.w3.org/2000/svg" '
        'style="background:#fff;border:2px solid #475569;border-radius:4px;'
        'box-shadow:0 3px 10px rgba(0,0,0,0.25)">'
        f'{stim.get(n, "")}'
        '</svg>'
        f'<div style="font-size:0.7rem;color:#64748b;margin-top:6px;'
        f'font-weight:600;letter-spacing:.04em">STIMULUS WARTEGG {n} / 8</div>'
        '</div>'
    )


PSIKOTES_KATEGORI = [
    ("V", "Sinonim & Antonim", "verbal"),
    ("A", "Analogi & Pengelompokkan Kata", "verbal"),
    ("AR", "Aritmatika", "numerik"),
    ("NUM", "Matematika Dasar", "numerik"),
    ("KRA", "Kraepelin", "ketelitian"),
    ("PAU", "Pauli", "ketahanan"),
    ("WAR", "Wartegg", "kepribadian"),
    ("DER", "Deret Angka", "numerik"),
    ("LOG", "Logika Penalaran", "logika"),
    ("SPA", "Spasial", "spasial"),
    ("POLA", "Pola Gambar", "spasial"),
    ("HTP", "HTP (House-Tree-Person)", "kepribadian"),
    ("ANA", "Penalaran Analitik", "analitik"),
    ("MBTI", "MBTI", "kepribadian"),
    ("DISC", "DISC", "kepribadian"),
]
PSIKOTES_KAT_MAP = {k: {"nama": n, "indikator": i} for k, n, i in PSIKOTES_KATEGORI}

# Fungsi bantuan untuk membuat tag gambar dengan fallback
def _img_pola(n):
    return (
        f'<div style="margin-top:15px;text-align:center;">'
        f'<img src="/static/pola/{n}.png" alt="Soal Pola Gambar {n}" '
        f'onerror="this.outerHTML=\'<div style=\\\'color:#ef4444;font-size:0.85rem;'
        f'font-weight:700;padding:10px;background:rgba(239,68,68,0.1);'
        f'border-radius:8px;display:inline-block\\\'>⚠️ [Gambar {n} belum dimasukkan ke folder static/pola/]</div>\'" '
        f'style="max-width:100%;max-height:450px;height:auto;border-radius:8px;background:#fff;padding:10px;border:2px solid #475569;">'
        f'</div>'
    )


PSIKOTES_SOAL = [
    # V: 10
    ("V", "Sinonim dari kata AKURAT adalah ...", ["Lambat","Tepat","Berubah","Rumit","Jauh"], "B"),
    ("V", "Antonim dari kata OPTIMIS adalah ...", ["Aktif","Pesimis","Percaya","Yakin","Tegas"], "B"),
    ("V", "Sinonim dari kata KONSISTEN adalah ...", ["Berubah-ubah","Tetap","Ragu","Cepat","Lambat"], "B"),
    ("V", "Antonim dari kata EFISIEN adalah ...", ["Cepat","Boros","Tepat","Hemat","Cermat"], "B"),
    ("V", "Sinonim dari kata KREDIBEL adalah ...", ["Dipercaya","Diragukan","Ditolak","Dihindari","Dilupakan"], "A"),
    ("V", "Antonim dari kata ABADI adalah ...", ["Kekal","Sementara","Selamanya","Tetap","Lestari"], "B"),
    ("V", "Sinonim dari kata KOMPLEKS adalah ...", ["Sederhana","Rumit","Mudah","Ringan","Jelas"], "B"),
    ("V", "Antonim dari kata MODERN adalah ...", ["Baru","Kuno","Canggih","Maju","Terbaru"], "B"),
    ("V", "Sinonim dari kata PROSPEK adalah ...", ["Harapan","Kegagalan","Kerugian","Bahaya","Ancaman"], "A"),
    ("V", "Antonim dari kata SPORADIS adalah ...", ["Jarang","Sering","Kadang","Acak","Tidak tentu"], "B"),
    # A: 8
    ("A", "DOKTER : PASIEN = GURU : ...", ["Sekolah","Buku","Murid","Kelas","Pelajaran"], "C"),
    ("A", "PADI : BERAS = GANDUM : ...", ["Tepung","Sawah","Roti","Jagung","Tanaman"], "A"),
    ("A", "KAPAL : LAUT = PESAWAT : ...", ["Bandara","Udara","Pilot","Mesin","Penumpang"], "B"),
    ("A", "MATA : MELIHAT = TELINGA : ...", ["Meraba","Mendengar","Mencium","Berbicara","Berjalan"], "B"),
    ("A", "Manakah kata yang TIDAK sekelompok?", ["Merah","Biru","Hijau","Mobil","Kuning"], "D"),
    ("A", "Manakah yang termasuk alat musik?", ["Gitar","Meja","Kursi","Lemari","Pintu"], "A"),
    ("A", "HIU : SIRIP = BURUNG : ...", ["Terbang","Sayap","Bulu","Paruh","Sarang"], "B"),
    ("A", "PENA : MENULIS = SAPU : ...", ["Pisau","Membersihkan","Buku","Meja","Lampu"], "B"),
    # AR: 8
    ("AR", "125 + 75 = ...", ["150","175","200","225","250"], "C"),
    ("AR", "20% dari 200.000 adalah ...", ["20.000","30.000","40.000","50.000","60.000"], "C"),
    ("AR", "15 x 12 = ...", ["160","170","180","190","200"], "C"),
    ("AR", "Jika 3x = 27, maka x = ...", ["6","7","8","9","10"], "D"),
    ("AR", "Harga Rp200.000 diskon 20%. Harga akhir = ...", ["Rp140.000","Rp150.000","Rp160.000","Rp170.000","Rp180.000"], "C"),
    ("AR", "45 : 9 + 3 = ...", ["6","7","8","9","10"], "C"),
    ("AR", "75% dari 400 = ...", ["250","275","300","325","350"], "C"),
    ("AR", "(25 + 75)^2 = ...", ["5.000","7.500","10.000","12.500","15.000"], "C"),
    # NUM: 8
    ("NUM", "Perbandingan pegawai L:P = 3:2. Total 50, jumlah perempuan = ...", ["15","20","25","30","35"], "B"),
    ("NUM", "Kendaraan menempuh 240 km dalam 4 jam. Kecepatan = ...", ["40 km/jam","50 km/jam","60 km/jam","70 km/jam","80 km/jam"], "C"),
    ("NUM", "5 pekerja selesai 12 hari, 10 pekerja selesai dalam ...", ["4 hari","5 hari","6 hari","7 hari","8 hari"], "C"),
    ("NUM", "Harga 3 buku Rp45.000. Harga 7 buku = ...", ["Rp95.000","Rp100.000","Rp105.000","Rp110.000","Rp115.000"], "C"),
    ("NUM", "Rata-rata dari 4,6,8,10,12 = ...", ["7","8","9","10","11"], "B"),
    ("NUM", "Tabung berisi 2/5, diisi 28 L jadi 3/4. Kapasitas = ...", ["60 L","70 L","80 L","90 L","100 L"], "C"),
    ("NUM", "Diskon 15% dari Rp80.000 = ...", ["Rp10.000","Rp11.000","Rp12.000","Rp13.000","Rp14.000"], "C"),
    ("NUM", "Jika 2/3 dari suatu angka adalah 18, angka tersebut = ...", ["24","25","26","27","28"], "D"),
    # KRA: 6
    ("KRA", "[Kraepelin] 7 + 5 = ...", ["10","11","12","13","14"], "C"),
    ("KRA", "[Kraepelin] 8 + 6 = ...", ["12","13","14","15","16"], "C"),
    ("KRA", "[Kraepelin] 9 + 4 = ...", ["11","12","13","14","15"], "C"),
    ("KRA", "[Kraepelin] 6 + 7 = ...", ["11","12","13","14","15"], "C"),
    ("KRA", "[Kraepelin] 5 + 9 = ...", ["12","13","14","15","16"], "C"),
    ("KRA", "[Kraepelin] 8 + 8 = ...", ["14","15","16","17","18"], "C"),
    # PAU: 6
    ("PAU", "[Pauli] 7 + 5 = ...", ["10","11","12","13","14"], "C"),
    ("PAU", "[Pauli] 8 + 6 = ...", ["12","13","14","15","16"], "C"),
    ("PAU", "[Pauli] 9 + 4 = ...", ["11","12","13","14","15"], "C"),
    ("PAU", "[Pauli] 6 + 7 = ...", ["11","12","13","14","15"], "C"),
    ("PAU", "[Pauli] 5 + 9 = ...", ["12","13","14","15","16"], "C"),
    ("PAU", "[Pauli] 8 + 8 = ...", ["14","15","16","17","18"], "C"),
    # WAR: 8 (Wartegg)
    ("WAR", "Kotak 1: stimulus titik di tengah. Apa yang akan Anda lakukan? " + _svg_wartegg(1),
     ["Melengkapi jadi gambar konkret (misal matahari, wajah)","Membuat pola geometris","Membiarkan kosong","Menambah elemen baru","Membuat simetris"], None),
    ("WAR", "Kotak 2: stimulus garis melengkung. Apa yang akan Anda lakukan? " + _svg_wartegg(2),
     ["Melengkapi jadi gambar konkret (misal ombak, burung)","Membuat pola berulang","Membiarkan kosong","Menambah elemen baru","Membuat simetris"], None),
    ("WAR", "Kotak 3: stimulus tiga garis vertikal. Apa yang akan Anda lakukan? " + _svg_wartegg(3),
     ["Melengkapi jadi gambar konkret (misal pagar, hujan)","Membuat pola abstrak","Membiarkan kosong","Menambah elemen baru","Membuat simetris"], None),
    ("WAR", "Kotak 4: stimulus kotak hitam kecil. Apa yang akan Anda lakukan? " + _svg_wartegg(4),
     ["Melengkapi jadi gambar konkret (misal jendela, kubus)","Membuat pola geometris","Membiarkan kosong","Menambah elemen baru","Membuat simetris"], None),
    ("WAR", "Kotak 5: stimulus dua garis diagonal sejajar. Apa yang akan Anda lakukan? " + _svg_wartegg(5),
     ["Melengkapi jadi gambar konkret (misal jalan, rel)","Membuat pola abstrak","Membiarkan kosong","Menambah elemen baru","Membuat simetris"], None),
    ("WAR", "Kotak 6: stimulus garis sudut. Apa yang akan Anda lakukan? " + _svg_wartegg(6),
     ["Melengkapi jadi gambar konkret (misal kursi, tangga)","Membuat pola geometris","Membiarkan kosong","Menambah elemen baru","Membuat simetris"], None),
    ("WAR", "Kotak 7: stimulus kurva lengkung. Apa yang akan Anda lakukan? " + _svg_wartegg(7),
     ["Melengkapi jadi gambar konkret (misal pelangi, jembatan)","Membuat pola berulang","Membiarkan kosong","Menambah elemen baru","Membuat simetris"], None),
    ("WAR", "Kotak 8: stimulus garis setengah lingkaran. Apa yang akan Anda lakukan? " + _svg_wartegg(8),
     ["Melengkapi jadi gambar konkret (misal bulan, mangkuk)","Membuat pola abstrak","Membiarkan kosong","Menambah elemen baru","Membuat simetris"], None),
    # POLA: 10 (Pola Gambar)
    ("POLA", "Gambar yang cocok untuk melanjutkan gambar di bawah ini adalah ..." + _img_pola(1), ["A", "B", "C", "D"], "C"),
    ("POLA", "Gambar yang serupa dengan gambar di bawah ini adalah ..." + _img_pola(2), ["A", "B", "C", "D"], "B"),
    ("POLA", "Gambar yang cocok untuk melanjutkan gambar di bawah ini adalah ..." + _img_pola(3), ["A", "B", "C", "D"], "D"),
    ("POLA", "Gambar yang cocok untuk melengkapi gambar di bawah ini adalah ..." + _img_pola(4), ["A", "B", "C", "D"], "C"),
    ("POLA", "Gambar yang cocok untuk melengkapi gambar di bawah ini adalah ..." + _img_pola(5), ["A", "B", "C", "D"], "D"),
    ("POLA", "Gambar yang cocok untuk melanjutkan gambar di bawah ini adalah ..." + _img_pola(6), ["A", "B", "C", "D"], "B"),
    ("POLA", "Gambar yang cocok untuk melanjutkan gambar di bawah ini adalah ..." + _img_pola(7), ["A", "B", "C", "D"], "C"),
    ("POLA", "Gambar yang cocok untuk melanjutkan gambar di bawah ini adalah ..." + _img_pola(8), ["A", "B", "C", "D"], "B"),
    ("POLA", "Gambar yang cocok untuk melanjutkan gambar di bawah ini adalah ..." + _img_pola(9), ["A", "B", "C", "D"], "A"),
    ("POLA", "Gambar yang cocok untuk melanjutkan gambar di bawah ini adalah ..." + _img_pola(10), ["A", "B", "C", "D"], "B"),
    # DER: 10
    ("DER", "4, 8, 12, 16, 20, ...", ["21","22","23","24","25"], "D"),
    ("DER", "2, 6, 18, 54, ...", ["108","124","144","162","180"], "D"),
    ("DER", "1, 3, 6, 10, 15, ...", ["18","19","20","21","22"], "D"),
    ("DER", "2, 4, 8, 16, ...", ["24","28","32","36","40"], "C"),
    ("DER", "5, 10, 8, 16, 14, ...", ["20","22","24","26","28"], "D"),
    ("DER", "100, 90, 81, 73, ...", ["64","65","66","67","68"], "C"),
    ("DER", "1, 1, 2, 3, 5, 8, ...", ["11","12","13","14","15"], "C"),
    ("DER", "3, 5, 7, 9, 11, ...", ["12","13","14","15","16"], "B"),
    ("DER", "50, 45, 40, 35, ...", ["25","28","30","32","34"], "C"),
    ("DER", "2, 3, 5, 7, 11, ...", ["12","13","14","15","16"], "B"),
    # LOG: 10
    ("LOG", "Semua supervisor pegawai. Budi supervisor. Kesimpulan?", ["Budi bukan pegawai","Budi pegawai","Semua pegawai supervisor","Budi direktur","Tidak dapat disimpulkan"], "B"),
    ("LOG", "Semua A adalah B. Semua B bukan C. Kesimpulan?", ["Semua A adalah C","Semua A bukan C","Sebagian A adalah C","Tidak ada A","Semua C adalah A"], "B"),
    ("LOG", "Jika hujan, jalan basah. Jalan tidak basah. Kesimpulan?", ["Hujan","Tidak hujan","Jalan rusak","Hujan deras","Tidak dapat disimpulkan"], "B"),
    ("LOG", "Jika A > B dan B > C, maka ...", ["A < C","A = C","A > C","A <= C","Tidak dapat ditentukan"], "C"),
    ("LOG", "Jika P maka Q. P benar. Maka ...", ["Q benar","Q salah","Q mungkin","P salah","Tidak dapat disimpulkan"], "A"),
    ("LOG", "Semua mahasiswa membaca buku. Sebagian membaca novel. Kesimpulan?", ["Semua mahasiswa membaca novel","Sebagian mahasiswa membaca novel","Tidak ada yang membaca novel","Semua novel dibaca mahasiswa","Tidak dapat disimpulkan"], "B"),
    ("LOG", "Semua logam padat. Tidak semua hipotesis terbukti. Kesimpulan?", ["Semua logam terbukti","Tidak ada logam padat","Semua hipotesis logam","Tidak dapat disimpulkan langsung","Semua benda padat logam"], "D"),
    ("LOG", "Semua wisatawan memiliki kamera. Sebagian kamera hitam. Kesimpulan?", ["Semua kamera hitam","Tidak semua kamera wisatawan hitam","Semua wisatawan kamera hitam","Tidak ada kamera hitam","Semua hitam"], "B"),
    ("LOG", "Semua burung bertelur. Beberapa hewan bersayap adalah burung. Kesimpulan?", ["Semua hewan bersayap bertelur","Beberapa hewan bersayap bertelur","Tidak ada hewan bersayap bertelur","Semua bertelur bersayap","Tidak dapat disimpulkan"], "B"),
    ("LOG", "Jika A atau B. Bukan A. Maka ...", ["A benar","B benar","A salah dan B salah","Tidak dapat disimpulkan","A dan B benar"], "B"),
    # SPA: 6
    ("SPA", "Kubus diputar 90 derajat ke kanan, sisi atas menjadi ...", ["Sisi depan","Sisi belakang","Sisi kanan","Sisi kiri","Tetap atas"], "C"),
    ("SPA", "Bayangan cermin dari huruf 'b' adalah ...", ["b","d","p","q","a"], "B"),
    ("SPA", "Pola: segitiga (3 sisi) -> segiempat (4) -> segilima (5) -> ...", ["Segienam","Segidelapan","Lingkaran","Segitiga","Persegi"], "A"),
    ("SPA", "Kertas dilipat 2 kali lalu dilubangi, berapa lubang saat dibuka?", ["1","2","4","6","8"], "C"),
    ("SPA", "Rotasi 180 derajat dari panah ke kanan adalah ...", ["Kiri","Atas","Bawah","Kanan","Diagonal"], "A"),
    ("SPA", "Jaring-jaring kubus terdiri dari ... persegi.", ["4","5","6","7","8"], "C"),
    # HTP: 5
    ("HTP", "[HTP] Saat menggambar rumah, bagian mana yang Anda gambar pertama?", ["Atap","Pintu","Jendela","Dinding","Halaman"], None),
    ("HTP", "[HTP] Saat menggambar pohon, Anda cenderung ...", ["Menggambar akar","Menggambar batang","Menggambar daun","Menggambar buah","Menggambar keseluruhan"], None),
    ("HTP", "[HTP] Saat menggambar orang, Anda mulai dari ...", ["Kepala","Badan","Tangan","Kaki","Wajah"], None),
    ("HTP", "[HTP] Ukuran gambar rumah Anda cenderung ...", ["Sangat kecil","Kecil","Sedang","Besar","Sangat besar"], None),
    ("HTP", "[HTP] Detail paling Anda perhatikan saat menggambar?", ["Proporsi","Garis","Warna","Detail kecil","Keseluruhan"], None),
    # ANA: 6
    ("ANA", "Rika lebih tinggi dari Sari. Sari lebih tinggi dari Dewi. Siapa paling tinggi?", ["Rika","Sari","Dewi","Sama","Tidak dapat ditentukan"], "A"),
    ("ANA", "A duduk di kiri B, B di kiri C, maka ...", ["A di kiri C","C di kiri A","A di kanan C","B paling kanan","Tidak dapat ditentukan"], "A"),
    ("ANA", "Antrean: Andi di depan Budi, Budi di depan Cici. Siapa paling belakang?", ["Andi","Budi","Cici","Dedi","Tidak dapat ditentukan"], "C"),
    ("ANA", "Jika P > Q dan Q < R, maka ...", ["P > R","P < R","P = R","Tidak dapat ditentukan","R > P"], "D"),
    ("ANA", "4 orang duduk melingkar. A berhadapan B. C di samping A. Siapa berhadapan C?", ["A","B","D","Tidak ada","Tidak dapat ditentukan"], "C"),
    ("ANA", "Semua A adalah B. Beberapa B adalah C. Kesimpulan?", ["Semua A adalah C","Beberapa A adalah C","Tidak ada A adalah C","Semua C adalah A","Tidak dapat disimpulkan"], "E"),
    # MBTI: 6
    ("MBTI", "Saya lebih suka menghabiskan waktu dengan ...", ["Banyak orang (E)","Sendiri (I)"], None),
    ("MBTI", "Saya lebih percaya pada ...", ["Fakta konkret (S)","Intuisi dan pola (N)"], None),
    ("MBTI", "Dalam mengambil keputusan, saya lebih mengutamakan ...", ["Logika (T)","Perasaan (F)"], None),
    ("MBTI", "Saya lebih nyaman dengan ...", ["Rencana terstruktur (J)","Fleksibilitas (P)"], None),
    ("MBTI", "Saya merasa energik setelah ...", ["Berinteraksi sosial (E)","Menyendiri (I)"], None),
    ("MBTI", "Saya lebih tertarik pada ...", ["Detail praktis (S)","Gagasan besar (N)"], None),
    # DISC: 6
    ("DISC", "Saya cenderung ...", ["Tegas dan kompetitif (D)","Antusias dan persuasif (I)","Tenang dan sabar (S)","Teliti dan hati-hati (C)"], None),
    ("DISC", "Dalam tim, saya lebih suka ...", ["Memimpin (D)","Mempengaruhi (I)","Mendukung (S)","Menganalisis (C)"], None),
    ("DISC", "Saya merasa terganggu oleh ...", ["Ketidakpastian (C)","Rutinitas (I)","Konflik (S)","Kontrol berlebihan (D)"], None),
    ("DISC", "Orang lain menggambarkan saya sebagai ...", ["Berani (D)","Menyenangkan (I)","Stabil (S)","Akurat (C)"], None),
    ("DISC", "Saya lebih suka pekerjaan yang ...", ["Menantang (D)","Banyak interaksi (I)","Teratur (S)","Detail (C)"], None),
    ("DISC", "Saat stres, saya cenderung ...", ["Mengambil alih (D)","Mencari dukungan (I)","Mendiamkan (S)","Menarik diri dan menganalisis (C)"], None),
]


def _init_db(get_db):
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS psikotes_peserta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode TEXT UNIQUE, nama TEXT NOT NULL,
            jk TEXT, tgl_lahir TEXT, pendidikan TEXT, pekerjaan TEXT,
            alamat TEXT, email TEXT, no_telp TEXT,
            suku_bangsa TEXT, status_perkawinan TEXT,
            mulai_at TEXT NOT NULL, selesai_at TEXT
        );
        CREATE TABLE IF NOT EXISTS psikotes_jawaban (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            peserta_id INTEGER NOT NULL, no_soal INTEGER NOT NULL,
            kategori TEXT NOT NULL, jawaban TEXT, skor INTEGER DEFAULT 0,
            UNIQUE(peserta_id, no_soal),
            FOREIGN KEY(peserta_id) REFERENCES psikotes_peserta(id)
        );
        CREATE TABLE IF NOT EXISTS psikotes_hasil (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            peserta_id INTEGER NOT NULL UNIQUE,
            skor_json TEXT NOT NULL, ringkasan TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(peserta_id) REFERENCES psikotes_peserta(id)
        );
    """)
    conn.commit()
    conn.close()


def _hitung_skor(jawaban_map):
    per_indikator = {}
    kepribadian = []
    for no, (kat, soal, opsi, kunci) in enumerate(PSIKOTES_SOAL, start=1):
        ind = PSIKOTES_KAT_MAP[kat]["indikator"]
        jaw = jawaban_map.get(no)
        if kunci is not None:
            per_indikator.setdefault(ind, {"total": 0, "benar": 0})
            per_indikator[ind]["total"] += 1
            if jaw == kunci:
                per_indikator[ind]["benar"] += 1
        else:
            kepribadian.append({
                "no": no, "kategori": kat,
                "nama_kategori": PSIKOTES_KAT_MAP[kat]["nama"],
                "soal": soal, "opsi": opsi, "jawaban": jaw,
            })
    for k, v in per_indikator.items():
        v["persen"] = round(v["benar"] / v["total"] * 100, 1) if v["total"] else 0
        v["level"] = ("Sangat Baik" if v["persen"] >= 80
                      else "Baik" if v["persen"] >= 60
                      else "Cukup" if v["persen"] >= 40
                      else "Perlu Ditingkatkan")
    return {"indikator": per_indikator, "kepribadian": kepribadian}


def register_psikotes(app, deps):
    get_db = deps["get_db"]
    page = deps["page"]
    license_gate = deps["license_gate"]
    consume_peserta = deps["consume_peserta"]
    BASE_DIR = deps["base_dir"]

    _init_db(get_db)

    # ===== AUTO-INJECT nav Riwayat Psikotes via after_request =====
    def inject_riwayat_nav(response):
        try:
            ct = response.content_type or ""
            if "text/html" not in ct:
                return response
            html = response.get_data(as_text=True)
            if 'href="/psikotes/riwayat"' in html:
                return response
            marker = "Tes Psikotes 100"
            if marker not in html:
                return response
            idx = html.find(marker)
            end = html.find("</a>", idx)
            if end < 0:
                return response
            end += len("</a>")
            nav = (chr(10) +
                '      <a class="nav-item" '
                'href="/psikotes/riwayat" '
                'style="display:block;padding:10px 12px;'
                'border-radius:10px;color:#e2e8f0;'
                'margin-bottom:4px;font-size:0.92rem;'
                'text-decoration:none">'
                '<i class="fas fa-clipboard-list" '
                'style="width:18px"></i> Riwayat Psikotes</a>')
            html = html[:end] + nav + html[end:]
            response.set_data(html)
        except Exception as e:
            print("[WARN] inject_riwayat_nav:", e)
        return response

    if not getattr(app, "_sipsi_nav_injected", False):
        app.after_request(inject_riwayat_nav)
        app._sipsi_nav_injected = True
        print("[OK] after_request nav Riwayat Psikotes terdaftar")

    @app.route("/psikotes", methods=["GET", "POST"])
    def psikotes():
        gate = license_gate(for_new_peserta=(request.method == "POST"))
        if gate is not None:
            return gate

        if request.method == "POST":
            nama = (request.form.get("nama") or "").strip()
            if not nama:
                flash("Nama wajib diisi.", "error")
                return redirect(url_for("psikotes"))
            kode = "PST-" + datetime.now().strftime("%Y%m%d%H%M%S")
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = get_db()
            cur = conn.execute(
                """INSERT INTO psikotes_peserta
                   (kode, nama, jk, tgl_lahir, pendidikan, pekerjaan, alamat,
                    email, no_telp, suku_bangsa, status_perkawinan, mulai_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    kode, nama.upper(),
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
                ),
            )
            conn.commit()
            pid = cur.lastrowid
            conn.close()

            cns = consume_peserta(BASE_DIR)
            if not cns.get("ok"):
                try:
                    c2 = get_db()
                    c2.execute("DELETE FROM psikotes_peserta WHERE id=?", (pid,))
                    c2.commit(); c2.close()
                except Exception:
                    pass
                flash(cns.get("error") or "Kuota peserta habis.", "error")
                return redirect(url_for("index"))

            session["psikotes_pid"] = pid
            session["psikotes_index"] = 0
            order = list(range(1, len(PSIKOTES_SOAL) + 1))
            random.shuffle(order)
            session["psikotes_order"] = order
            return redirect(url_for("psikotes_ujian"))

        body = """
        <div class="card" style="max-width:820px;margin:0 auto">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
            <div style="width:48px;height:48px;border-radius:14px;
              background:linear-gradient(135deg,#7c3aed,#a78bfa);
              display:flex;align-items:center;justify-content:center;color:#fff;font-size:1.3rem">
              <i class="fas fa-clipboard-check"></i>
            </div>
            <div>
              <h2 style="margin:0">Tes Psikotes</h2>
              <div class="muted" style="font-size:0.85rem">
                15 kategori · 121 soal acak
              </div>
            </div>
          </div>
          <form method="post">
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
              <div><label>Tanggal lahir</label><input type="date" name="tgl_lahir"></div>
              <div>
                <label>Status pernikahan</label>
                <select name="status_perkawinan">
                  <option value="">— Pilih —</option>
                  <option>Belum Menikah</option><option>Menikah</option>
                  <option>Cerai Hidup</option><option>Cerai Mati</option>
                </select>
              </div>
              <div><label>Suku bangsa</label><input name="suku_bangsa"></div>
            </div>
            <div class="grid2">
              <div>
                <label>Pendidikan</label>
                <select name="pendidikan">
                  <option value="">— Pilih —</option>
                  <option>SD</option><option>SMP</option>
                  <option>SMA / SMK</option><option>D3</option>
                  <option>S1</option><option>S2</option><option>S3</option>
                </select>
              </div>
              <div><label>Pekerjaan</label><input name="pekerjaan"></div>
            </div>
            <div class="grid2">
              <div><label>No. HP / WA</label><input name="no_telp"></div>
              <div><label>Email</label><input type="email" name="email"></div>
            </div>
            <label>Alamat</label>
            <textarea name="alamat" rows="2"></textarea>
            <div style="display:flex;gap:10px;margin-top:8px;flex-wrap:wrap">
              <button class="btn" type="submit"><i class="fas fa-play"></i> Mulai Tes Psikotes</button>
              <a class="btn secondary" href="/">Batal</a>
            </div>
          </form>
        </div>
        """
        return page("Tes Psikotes", body, active="psikotes", subtitle="Form data peserta")

    @app.route("/psikotes/ujian", methods=["GET", "POST"])
    def psikotes_ujian():
        gate = license_gate(False)
        if gate is not None:
            return gate
        pid = session.get("psikotes_pid")
        order = session.get("psikotes_order")
        idx = int(session.get("psikotes_index") or 0)
        if not pid or not order:
            flash("Sesi tes psikotes tidak ditemukan.", "error")
            return redirect(url_for("psikotes"))

        total = len(order)
        if idx < 0: idx = 0
        if idx >= total: return redirect(url_for("psikotes_selesai"))

        no = order[idx]
        kat, soal, opsi, kunci = PSIKOTES_SOAL[no - 1]
        kat_nama = PSIKOTES_KAT_MAP[kat]["nama"]

        conn = get_db()
        p = conn.execute("SELECT * FROM psikotes_peserta WHERE id=?", (pid,)).fetchone()
        answered_rows = conn.execute(
            "SELECT no_soal, jawaban FROM psikotes_jawaban WHERE peserta_id=?", (pid,)
        ).fetchall()
        conn.close()
        answered = {r["no_soal"]: r["jawaban"] for r in answered_rows}
        jaw_prev = answered.get(no, "")

        if request.method == "POST":
            aksi = request.form.get("aksi") or "jawab"
            if aksi == "prev":
                session["psikotes_index"] = max(0, idx - 1)
                return redirect(url_for("psikotes_ujian"))
            if aksi == "next":
                session["psikotes_index"] = min(total - 1, idx + 1)
                return redirect(url_for("psikotes_ujian"))
            if aksi == "goto":
                try:
                    g = int(request.form.get("goto_idx") or 0)
                    session["psikotes_index"] = max(0, min(total - 1, g))
                except ValueError:
                    pass
                return redirect(url_for("psikotes_ujian"))
            if aksi == "selesai":
                return redirect(url_for("psikotes_selesai"))

            jaw = (request.form.get("jawaban") or "").strip().upper()
            if not jaw:
                flash("Pilih jawaban terlebih dahulu.", "error")
                return redirect(url_for("psikotes_ujian"))
            if no in answered:
                session["psikotes_index"] = min(total - 1, idx + 1)
                return redirect(url_for("psikotes_ujian"))

            skor = 1 if (kunci is not None and jaw == kunci) else 0
            conn = get_db()
            conn.execute(
                "INSERT INTO psikotes_jawaban (peserta_id, no_soal, kategori, jawaban, skor) "
                "VALUES (?,?,?,?,?)",
                (pid, no, kat, jaw, skor),
            )
            conn.commit()
            conn.close()
            answered[no] = jaw

            if idx + 1 < total:
                session["psikotes_index"] = idx + 1
                return redirect(url_for("psikotes_ujian"))
            return redirect(url_for("psikotes_selesai"))

        grid = ""
        window = range(max(0, idx - 10), min(total, idx + 11))
        for i in window:
            sid = order[i]
            is_cur = i == idx
            is_ans = sid in answered
            if is_cur:
                bg, fg, border = "#7c3aed", "#fff", "#c4b5fd"
            elif is_ans:
                bg, fg, border = "#1e293b", "#e2e8f0", "#ef4444"
            else:
                bg, fg, border = "#0b1220", "#94a3b8", "#334155"
            dot = ('<span style="position:absolute;top:4px;right:5px;width:7px;'
                   'height:7px;border-radius:50%;background:#ef4444"></span>') if is_ans else ""
            grid += f"""
            <form method="post" style="margin:0;display:inline">
              <input type="hidden" name="aksi" value="goto">
              <input type="hidden" name="goto_idx" value="{i}">
              <button type="submit" style="position:relative;width:40px;height:40px;
                margin:2px;border-radius:8px;border:2px solid {border};
                background:{bg};color:{fg};font-weight:700;cursor:pointer;font-size:0.8rem">
                {i+1}{dot}
              </button>
            </form>"""

        opsi_html = ""
        for letter_idx, opt in enumerate(opsi):
            letter = chr(65 + letter_idx)
            checked = 'checked' if jaw_prev == letter else ''
            disabled = 'disabled' if jaw_prev else ''
            # Jika opsi hanya huruf A/B/C/D, jangan tampilkan teksnya agar tidak dobel (A. A)
            display_opt = "" if opt.upper() == letter else f" {opt}"
            
            opsi_html += f"""
            <label style="display:block;padding:10px;border:2px solid #334155;
              border-radius:8px;margin:6px 0;cursor:pointer;background:#0b1220">
              <input type="radio" name="jawaban" value="{letter}" {checked} {disabled}
                     style="width:auto;margin-right:8px">
              <b>{letter}.</b>{display_opt}
            </label>"""

        progress = int((len(answered) / total) * 100) if total else 0
        p_kode = p["kode"] if p else "—"
        p_nama = p["nama"] if p else "—"

        body = f"""
        <style>
          .exam-wrap {{ max-width: 920px; margin: 0 auto; }}
          .exam-head {{ background: linear-gradient(135deg, #7c3aed, #a78bfa);
            color: #fff; border-radius: 14px 14px 0 0; padding: 14px; text-align: center; }}
          .exam-head .t {{ font-weight: 800; font-size: 1.15rem; letter-spacing: .06em; }}
          .exam-head .s {{ font-size: 0.85rem; margin-top: 4px; }}
          .exam-meta {{ background: #1e293b; border: 1px solid #334155; border-top: none;
            padding: 10px 12px; display: grid; grid-template-columns: repeat(4, 1fr);
            gap: 8px; font-size: 0.75rem; }}
          .exam-meta .k {{ color: #94a3b8; font-size: 0.68rem; }}
          .exam-body {{ background: #0f172a; border: 1px solid #334155; border-top: none;
            border-radius: 0 0 14px 14px; padding: 20px 16px; }}
          .exam-q {{ font-size: 1.05rem; font-weight: 700; line-height: 1.5;
            color: #f1f5f9; margin: 8px 0 14px; }}
          /* SVG Wartegg dan Gambar Pola responsif di layar kecil */
          .exam-q svg {{ max-width: min(150px, 60vw); height: auto; }}
          .exam-q img {{ max-width: 100%; height: auto; border-radius: 8px; margin: 10px 0; display: block; }}
          .exam-q div[style*="max-width:220px"] {{ max-width: 100%; }}
          .exam-nav {{ display: flex; justify-content: space-between; gap: 8px;
            margin-bottom: 12px; }}
          .exam-nav .arrow {{ background: #334155; color: #fff; border: none;
            border-radius: 8px; padding: 8px 16px; font-weight: 800; cursor: pointer; }}
          .exam-nav .arrow:disabled {{ opacity: .35; cursor: not-allowed; }}
          .locked-note {{ background: #422006; border: 1px solid #b45309;
            color: #fde68a; padding: 8px 12px; border-radius: 8px;
            font-size: 0.8rem; margin-top: 10px; }}
        </style>
        <div class="exam-wrap">
          <div class="exam-head">
            <div class="t">TES PSIKOTES</div>
            <div class="s">15 Kategori · Form Isian Interaktif</div>
          </div>
          <div class="exam-meta">
            <div><div class="k">SOAL</div><strong>{idx + 1} / {total}</strong></div>
            <div><div class="k">KODE</div><strong>{p_kode}</strong></div>
            <div><div class="k">NAMA</div><strong>{p_nama}</strong></div>
            <div><div class="k">KATEGORI</div><strong>{kat_nama}</strong></div>
          </div>
          <div class="exam-body">
            <div class="exam-nav">
              <form method="post" style="margin:0">
                <input type="hidden" name="aksi" value="prev">
                <button class="arrow" type="submit" {"disabled" if idx==0 else ""}>◀ Sebelumnya</button>
              </form>
              <form method="post" style="margin:0">
                <input type="hidden" name="aksi" value="next">
                <button class="arrow" type="submit" {"disabled" if idx>=total-1 else ""}>Berikutnya ▶</button>
              </form>
            </div>
            <div class="exam-q">{no}. {soal}</div>
            {('<form method="post">' if not jaw_prev else '<div>')}
              {opsi_html}
              {('<button class="btn" type="submit" style="width:100%;margin-top:10px">Simpan &amp; Lanjut</button>' if not jaw_prev else '')}
            {('</form>' if not jaw_prev else '</div>')}
            {('<div class="locked-note">Soal ini sudah dijawab (<b>' + jaw_prev + '</b>).</div>') if jaw_prev else ''}
            <div style="height:8px;background:#1e293b;border-radius:99px;
              overflow:hidden;margin-top:16px;width:100%;border:1px solid #334155">
              <div style="height:100%;width:{progress}%;background:#7c3aed"></div>
            </div>
            <p style="margin:8px 0 0;color:#64748b;font-size:0.8rem">
              Terjawab {len(answered)}/{total}
            </p>
            <div style="margin-top:12px">{grid}</div>
            <form method="post" style="margin-top:16px;text-align:center">
              <input type="hidden" name="aksi" value="selesai">
              <button type="submit" style="background:#dc2626;color:#fff;border:none;
                border-radius:10px;padding:12px 28px;font-weight:800;cursor:pointer">
                SELESAI &amp; LIHAT HASIL
              </button>
            </form>
          </div>
        </div>
        """
        return page(f"Soal {idx + 1}", body, active="psikotes",
                    subtitle=f"Soal {idx+1} / {total}")

    @app.route("/psikotes/selesai")
    def psikotes_selesai():
        gate = license_gate(False)
        if gate is not None:
            return gate
        pid = session.get("psikotes_pid")
        if not pid:
            return redirect(url_for("psikotes"))

        conn = get_db()
        rows = conn.execute(
            "SELECT no_soal, jawaban FROM psikotes_jawaban WHERE peserta_id=?", (pid,)
        ).fetchall()
        if len(rows) < len(PSIKOTES_SOAL):
            conn.close()
            flash(f"Masih ada soal belum dijawab ({len(rows)}/{len(PSIKOTES_SOAL)}).", "error")
            answered = {r["no_soal"] for r in rows}
            order = session.get("psikotes_order") or list(range(1, len(PSIKOTES_SOAL)+1))
            for i, n in enumerate(order):
                if n not in answered:
                    session["psikotes_index"] = i
                    break
            return redirect(url_for("psikotes_ujian"))

        jawaban_map = {r["no_soal"]: r["jawaban"] for r in rows}
        hasil = _hitung_skor(jawaban_map)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ringkasan = "; ".join(
            f"{k}: {v['benar']}/{v['total']} ({v['persen']}%)"
            for k, v in hasil["indikator"].items()
        ) or "—"

        conn.execute("UPDATE psikotes_peserta SET selesai_at=? WHERE id=?", (now, pid))
        conn.execute(
            "INSERT OR REPLACE INTO psikotes_hasil "
            "(peserta_id, skor_json, ringkasan, created_at) VALUES (?,?,?,?)",
            (pid, _json.dumps(hasil, ensure_ascii=False), ringkasan, now),
        )
        conn.commit()
        conn.close()
        session.pop("psikotes_pid", None)
        session.pop("psikotes_index", None)
        session.pop("psikotes_order", None)
        return redirect(url_for("psikotes_hasil", pid=pid))

    @app.route("/psikotes/hasil/<int:pid>")
    def psikotes_hasil(pid):
        gate = license_gate(False)
        if gate is not None:
            return gate
        conn = get_db()
        p = conn.execute("SELECT * FROM psikotes_peserta WHERE id=?", (pid,)).fetchone()
        h = conn.execute("SELECT * FROM psikotes_hasil WHERE peserta_id=?", (pid,)).fetchone()
        conn.close()
        if not p or not h:
            flash("Data tidak ditemukan.", "error")
            return redirect(url_for("psikotes_riwayat"))

        try:
            hasil = _json.loads(h["skor_json"] or "{}")
        except Exception:
            hasil = {"indikator": {}, "kepribadian": []}

        indikator = hasil.get("indikator", {})
        kepribadian = hasil.get("kepribadian", [])

        rows_html = ""
        for k, v in indikator.items():
            color = ("#10b981" if v["persen"] >= 80
                     else "#3b82f6" if v["persen"] >= 60
                     else "#f59e0b" if v["persen"] >= 40
                     else "#ef4444")
            rows_html += (
                f'<tr><td><b>{k.capitalize()}</b></td>'
                f'<td class="num">{v["benar"]}</td>'
                f'<td class="num">{v["total"]}</td>'
                f'<td class="num"><b>{v["persen"]}%</b></td>'
                f'<td><span style="display:inline-block;width:12px;height:12px;'
                f'border-radius:50%;background:{color};margin-right:6px"></span>{v["level"]}</td></tr>'
            )

        bars_html = ""
        for k, v in indikator.items():
            bars_html += (
                f'<div class="bar-row">'
                f'<div class="bar-label">{k.capitalize()}</div>'
                f'<div class="bar-track"><div class="bar-fill" '
                f'style="width:{v["persen"]}%"></div></div>'
                f'<div class="bar-value">{v["persen"]}%</div></div>'
            )

        kep_html = ""
        for item in kepribadian:
            soal_esc = (item["soal"] or "").replace("<", "&lt;")
            jaw = item["jawaban"] or "—"
            kep_html += (
                f'<tr><td style="vertical-align:top;font-size:0.78rem">'
                f'{item["no"]}. [{item["nama_kategori"]}] {soal_esc}</td>'
                f'<td class="num">{jaw}</td></tr>'
            )
        kep_section = (
            '<div class="psych-section">ANALISIS KEPRIBADIAN (MBTI / DISC / WARTEGG / HTP)</div>'
            '<p class="psych-note">Jawaban soal kepribadian tercatat untuk interpretasi psikolog.</p>'
            '<div style="overflow-x:auto"><table class="psych-table">'
            '<thead><tr><th>Pertanyaan</th><th>Jawaban</th></tr></thead>'
            f'<tbody>{kep_html or "<tr><td colspan=\'2\'>—</td></tr>"}</tbody>'
            '</table></div>'
        ) if kepribadian else ""

        logo_url = url_for("static", filename="logo.png")
        p_nama = p["nama"]
        p_kode = p["kode"]
        p_jk = p["jk"] or "—"
        p_pend = p["pendidikan"] or "—"
        p_kerja = p["pekerjaan"] or "—"
        tgl = (p["mulai_at"] or "")[:10]
        selesai = p["selesai_at"] or "—"
        ttd = datetime.now().strftime("%d-%m-%Y")

        body = f"""
        <style>
          .psych-report {{ max-width:900px;margin:0 auto;background:#fff;color:#172033;
            border:1px solid #d7dee8;border-radius:10px;padding:24px;font-size:13px; }}
          .psych-head {{ text-align:center;border-bottom:3px double #1e3a5f;
            padding-bottom:14px;margin-bottom:16px; }}
          .psych-head img {{width:64px;height:64px;object-fit:contain;margin-bottom:6px}}
          .psych-head h1 {{font-size:19px;margin:3px 0;color:#123b70}}
          .psych-head p {{margin:3px 0;color:#475569}}
          .psych-code {{font-size:15px;font-weight:800;letter-spacing:1px;margin-top:8px}}
          .psych-meta {{display:grid;grid-template-columns:1fr 1fr;gap:7px 24px;margin:14px 0 18px}}
          .psych-meta div {{padding:6px 0;border-bottom:1px solid #e2e8f0}}
          .psych-meta b {{display:inline-block;min-width:130px;color:#475569}}
          .psych-section {{font-size:14px;color:#123b70;font-weight:800;
            border-bottom:1px solid #94a3b8;padding-bottom:5px;margin:18px 0 10px}}
          .psych-bars {{display:grid;gap:9px;margin:12px 0}}
          .bar-row {{display:grid;grid-template-columns:minmax(155px,180px) minmax(80px,1fr) 55px;
            gap:10px;align-items:center}}
          .bar-label {{font-size:12px}}
          .bar-track {{height:12px;background:#e8edf4;border-radius:3px;overflow:hidden}}
          .bar-fill {{height:100%;background:#1764b0;border-radius:3px}}
          .bar-value {{text-align:right;font-weight:800}}
          .psych-table {{width:100%;border-collapse:collapse;font-size:12px}}
          .psych-table th,.psych-table td {{border:1px solid #cbd5e1;padding:7px;text-align:left}}
          .psych-table th {{background:#eaf0f7;color:#123b70}}
          .psych-table .num {{text-align:center;white-space:nowrap}}
          .psych-note {{font-size:11px;line-height:1.6;color:#475569}}
          .psych-sign {{margin:36px 0 0 auto;width:245px;text-align:center;line-height:1.6}}
          .psych-sign .space {{height:58px}}
          .psych-sign .line {{border-top:1px solid #334155;width:180px;margin:0 auto 4px}}
          @media print {{
            .sidebar,.topbar,.no-print,nav,.btn,.menu-btn,.sidebar-overlay,
            .app-footer {{display:none!important}}
            .main {{margin:0!important;padding:0!important;background:#fff!important}}
            .psych-report {{max-width:none;border:0;box-shadow:none;padding:0}}
            .bar-fill {{background:#1764b0!important;
              -webkit-print-color-adjust:exact;print-color-adjust:exact}}
          }}
        </style>
        <div class="psych-report">
          <header class="psych-head">
            <img src="{logo_url}" alt="SIPSI">
            <h1>LAPORAN HASIL TES PSIKOTES</h1>
            <p>SIPSI — Soal Psikotes · 15 Kategori</p>
            <div class="psych-code">KODE: {p_kode}</div>
          </header>
          <div class="psych-section">IDENTITAS PESERTA</div>
          <div class="psych-meta">
            <div><b>Nama</b> : {p_nama}</div>
            <div><b>Jenis kelamin</b> : {p_jk}</div>
            <div><b>Pendidikan</b> : {p_pend}</div>
            <div><b>Pekerjaan</b> : {p_kerja}</div>
            <div><b>Tanggal tes</b> : {tgl}</div>
            <div><b>Selesai</b> : {selesai}</div>
          </div>
          <div class="psych-section">GRAFIK PER INDIKATOR</div>
          <div class="psych-bars">{bars_html or '<p>—</p>'}</div>
          <div class="psych-section">RINCIAN SKOR PER INDIKATOR</div>
          <div style="overflow-x:auto">
            <table class="psych-table">
              <thead><tr>
                <th>Indikator</th><th>Benar</th><th>Total</th>
                <th>Persentase</th><th>Level</th>
              </tr></thead>
              <tbody>{rows_html or '<tr><td colspan="5">—</td></tr>'}</tbody>
            </table>
          </div>
          {kep_section}
          <div class="psych-section">CATATAN DAN BATASAN</div>
          <p class="psych-note">
            Tes Psikotes ini merupakan instrumen latihan/simulasi. Bukan diagnosis
            klinis. Soal kepribadian (MBTI/DISC/Wartegg/HTP) hanya dicatat,
            interpretasi memerlukan psikolog berlisensi.
          </p>
          <div class="psych-sign">
            <div>................................, {ttd}</div>
            <div>Tempat, tanggal / bulan / tahun</div>
            <div class="space"></div>
            <div class="line"></div>
            <b>{p_nama}</b>
          </div>
        </div>
        <div class="no-print" style="max-width:900px;margin:16px auto;text-align:center">
          <button class="btn" onclick="window.print()">🖨 Cetak Laporan</button>
          <a class="btn secondary" href="{url_for('psikotes_riwayat')}">Riwayat</a>
          <a class="btn secondary" href="{url_for('psikotes')}">Tes Baru</a>
        </div>
        """
        return page("Hasil Tes Psikotes", body, active="psikotes", subtitle="Laporan hasil")

    @app.route("/psikotes/riwayat", methods=["GET", "POST"])
    def psikotes_riwayat():
        gate = license_gate(False)
        if gate is not None:
            return gate
        conn = get_db()
        if request.method == "POST":
            aksi = request.form.get("aksi")
            if aksi == "hapus":
                ids = [int(x) for x in request.form.getlist("ids") if str(x).isdigit()]
                if ids:
                    for pidx in ids:
                        conn.execute("DELETE FROM psikotes_jawaban WHERE peserta_id=?", (pidx,))
                        conn.execute("DELETE FROM psikotes_hasil WHERE peserta_id=?", (pidx,))
                        conn.execute("DELETE FROM psikotes_peserta WHERE id=?", (pidx,))
                    conn.commit()
                    flash(f"{len(ids)} riwayat dihapus.", "success")
                conn.close()
                return redirect(url_for("psikotes_riwayat"))

        rows = conn.execute(
            """SELECT p.id, p.kode, p.nama, p.selesai_at, h.skor_json
               FROM psikotes_peserta p
               LEFT JOIN psikotes_hasil h ON h.peserta_id = p.id
               ORDER BY p.id DESC LIMIT 200"""
        ).fetchall()
        conn.close()

        tr = ""
        for r in rows:
            lihat = (f'<a href="{url_for("psikotes_hasil", pid=r["id"])}">Lihat</a>'
                     if r["skor_json"] else "—")
            tr += (
                f'<tr><td class="checkbox-cell">'
                f'<input type="checkbox" name="ids" value="{r["id"]}" class="row-check">'
                f'</td><td>{r["kode"]}</td><td>{r["nama"]}</td>'
                f'<td>{r["selesai_at"] or "—"}</td><td>{lihat}</td></tr>'
            )

        body = f"""
        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;
            flex-wrap:wrap;gap:8px">
            <h2 style="margin:0">Riwayat Tes Psikotes</h2>
            <a class="btn" href="{url_for('psikotes')}">
              <i class="fas fa-plus"></i> Tes Baru
            </a>
          </div>
          <form method="post" onsubmit="return confirm('Hapus data terpilih?');">
            <input type="hidden" name="aksi" value="hapus">
            <div style="margin:12px 0;display:flex;gap:10px;align-items:center;flex-wrap:wrap">
              <label style="display:flex;align-items:center;gap:8px;color:#e2e8f0">
                <input type="checkbox" id="checkAllPst" style="width:auto"> Pilih semua
              </label>
              <button type="submit" class="btn danger">
                <i class="fas fa-trash"></i> Hapus
              </button>
            </div>
            <table>
              <thead><tr>
                <th style="width:36px"></th>
                <th>Kode</th><th>Nama</th><th>Selesai</th><th>Aksi</th>
              </tr></thead>
              <tbody>{tr or '<tr><td colspan="5" class="muted">Belum ada data</td></tr>'}</tbody>
            </table>
          </form>
        </div>
        <script>
        (function(){{
          var all = document.getElementById('checkAllPst');
          if (!all) return;
          all.addEventListener('change', function(){{
            document.querySelectorAll('.row-check').forEach(function(cb){{
              cb.checked = all.checked;
            }});
          }});
        }})();
        </script>
        """
        return page("Riwayat Tes Psikotes", body, active="psikotes",
                    subtitle="Daftar hasil")