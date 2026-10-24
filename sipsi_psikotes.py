# -*- coding: utf-8 -*-
"""
SIPSI - Modul Tes Psikotes 100 Soal
-----------------------------------
Fitur:
- Form identitas peserta
- 100 soal dengan urutan acak
- 80 soal kemampuan dan 20 soal kecenderungan kepribadian
- Nilai otomatis dan indikator per kategori
- Hasil cetak melalui browser
- Penyimpanan hasil dengan SQLite

Catatan:
Ini adalah contoh latihan dan skrining awal, bukan alat diagnosis
psikologis atau pengganti pemeriksaan oleh psikolog profesional.
"""

import os
import json
import random
import sqlite3
from datetime import datetime

from flask import (
    Blueprint,
    request,
    session,
    url_for,
    render_template_string,
    redirect,
)

psikotes_bp = Blueprint(
    "psikotes",
    __name__,
    url_prefix="/sipsi/psikotes",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get(
    "SIPSI_PSIKOTES_DB",
    os.path.join(BASE_DIR, "psikotes.db"),
)

BANK = []


# ============================================================
# PEMBENTUK BANK SOAL
# ============================================================

def tambah_soal(kategori, pertanyaan, opsi, jawaban):
    BANK.append({
        "id": len(BANK) + 1,
        "kategori": kategori,
        "tipe": "cognitive",
        "q": pertanyaan,
        "o": opsi,
        "a": jawaban,
        "map": [],
    })


def tambah_mbti(dimensi, pertanyaan, pilihan_a, pilihan_b, huruf_a, huruf_b):
    BANK.append({
        "id": len(BANK) + 1,
        "kategori": "Kepribadian",
        "tipe": "mbti",
        "dimensi": dimensi,
        "q": pertanyaan,
        "o": [pilihan_a, pilihan_b],
        "a": None,
        "map": [huruf_a, huruf_b],
    })


def tambah_disc(pertanyaan, pilihan_d, pilihan_i, pilihan_s, pilihan_c):
    BANK.append({
        "id": len(BANK) + 1,
        "kategori": "Kepribadian",
        "tipe": "disc",
        "q": pertanyaan,
        "o": [pilihan_d, pilihan_i, pilihan_s, pilihan_c],
        "a": None,
        "map": ["D", "I", "S", "C"],
    })


# ============================================================
# 1. VERBAL: SINONIM DAN ANTONIM (10 SOAL)
# Indeks jawaban dimulai dari 0.
# ============================================================

tambah_soal("Verbal", "Sinonim kata 'abstrak' adalah ...",
            ["Nyata", "Teoretis", "Konkret", "Fisik"], 1)
tambah_soal("Verbal", "Antonim kata 'objektif' adalah ...",
            ["Netral", "Rasional", "Subjektif", "Adil"], 2)
tambah_soal("Verbal", "Sinonim kata 'vital' adalah ...",
            ["Sepele", "Penting", "Lambat", "Biasa"], 1)
tambah_soal("Verbal", "Antonim kata 'progresif' adalah ...",
            ["Inovatif", "Aktif", "Stagnan", "Maju"], 2)
tambah_soal("Verbal", "Sinonim kata 'intensif' adalah ...",
            ["Mendalam", "Ringan", "Biasa", "Longgar"], 0)
tambah_soal("Verbal", "Antonim kata 'loyal' adalah ...",
            ["Setia", "Patuh", "Berkhianat", "Jujur"], 2)
tambah_soal("Verbal", "Sinonim kata 'valid' adalah ...",
            ["Sah", "Salah", "Lemah", "Palsu"], 0)
tambah_soal("Verbal", "Antonim kata 'transparan' adalah ...",
            ["Terbuka", "Jelas", "Tertutup", "Terang"], 2)
tambah_soal("Verbal", "Sinonim kata 'akurat' adalah ...",
            ["Tepat", "Samar", "Kasar", "Umum"], 0)
tambah_soal("Verbal", "Sinonim kata 'efisien' adalah ...",
            ["Boros", "Tepat guna", "Rumit", "Lambat"], 1)


# ============================================================
# 2. ANALOGI DAN KLASIFIKASI KATA (10 SOAL)
# ============================================================

tambah_soal("Analogi", "Dokter : Pasien = Guru : ...",
            ["Buku", "Murid", "Sekolah", "Kelas"], 1)
tambah_soal("Analogi", "Pisau : Tajam = Kapas : ...",
            ["Ringan", "Lembut", "Putih", "Tipis"], 1)
tambah_soal("Analogi", "Mobil : Jalan = Kapal : ...",
            ["Darat", "Laut", "Garasi", "Jembatan"], 1)
tambah_soal("Analogi", "Api : Panas = Es : ...",
            ["Air", "Beku", "Dingin", "Putih"], 2)
tambah_soal("Analogi", "Kaki : Sepatu = Tangan : ...",
            ["Topi", "Sarung tangan", "Kaos kaki", "Ikat pinggang"], 1)
tambah_soal("Analogi", "Buku : Membaca = Pisau : ...",
            ["Mengasah", "Menulis", "Memotong", "Menggambar"], 2)
tambah_soal("Analogi", "Benih : Pohon = Telur : ...",
            ["Sarang", "Ayam", "Bulu", "Paruh"], 1)
tambah_soal("Analogi", "Jari : Tangan = Gigi : ...",
            ["Hidung", "Mulut", "Pipi", "Mata"], 1)
tambah_soal("Analogi", "Peta : Wilayah = Denah : ...",
            ["Jalan", "Bangunan", "Kendaraan", "Kota"], 1)
tambah_soal("Klasifikasi", "Kucing, harimau, singa, sapi. Yang berbeda adalah ...",
            ["Kucing", "Harimau", "Singa", "Sapi"], 3)


# ============================================================
# 3. ARITMATIKA (10 SOAL)
# ============================================================

tambah_soal("Aritmatika", "125 + 75 = ...",
            ["150", "175", "200", "225"], 2)
tambah_soal("Aritmatika", "36 x 4 = ...",
            ["124", "144", "154", "164"], 1)
tambah_soal("Aritmatika", "144 dibagi 12 = ...",
            ["10", "11", "12", "13"], 2)
tambah_soal("Aritmatika", "18 + 27 - 9 = ...",
            ["34", "35", "36", "37"], 2)
tambah_soal("Aritmatika", "15 x 6 - 20 = ...",
            ["60", "65", "70", "75"], 2)
tambah_soal("Aritmatika", "(25 + 15) x 2 = ...",
            ["60", "70", "80", "90"], 2)
tambah_soal("Aritmatika", "12% dari 250 adalah ...",
            ["25", "30", "35", "40"], 1)
tambah_soal("Aritmatika", "Harga Rp200.000 didiskon 15%. Harga akhirnya adalah ...",
            ["Rp160.000", "Rp165.000", "Rp170.000", "Rp175.000"], 2)
tambah_soal("Aritmatika", "1/4 + 1/2 = ...",
            ["1/2", "2/3", "3/4", "1"], 2)
tambah_soal("Aritmatika", "3/5 dari 100 adalah ...",
            ["20", "40", "50", "60"], 3)


# ============================================================
# 4. MATEMATIKA DASAR (10 SOAL)
# ============================================================

tambah_soal("Matematika Dasar", "Jika 3x + 5 = 20, maka x = ...",
            ["3", "4", "5", "6"], 2)
tambah_soal("Matematika Dasar", "Rata-rata dari 6, 8, dan 10 adalah ...",
            ["6", "7", "8", "9"], 2)
tambah_soal("Matematika Dasar", "Keliling persegi panjang dengan panjang 8 cm dan lebar 5 cm adalah ...",
            ["13 cm", "26 cm", "40 cm", "16 cm"], 1)
tambah_soal("Matematika Dasar", "Luas persegi panjang 9 cm x 4 cm adalah ...",
            ["13 cm2", "26 cm2", "36 cm2", "45 cm2"], 2)
tambah_soal("Matematika Dasar", "Sepertiga dari 90 adalah ...",
            ["15", "20", "30", "45"], 2)
tambah_soal("Matematika Dasar", "20% dari 150 adalah ...",
            ["15", "20", "30", "35"], 2)
tambah_soal("Matematika Dasar", "Perbandingan A:B = 2:3. Jika totalnya 25, nilai A adalah ...",
            ["5", "10", "15", "20"], 1)
tambah_soal("Matematika Dasar", "Jarak 120 km ditempuh selama 2 jam. Kecepatan rata-ratanya ...",
            ["30 km/jam", "50 km/jam", "60 km/jam", "80 km/jam"], 2)
tambah_soal("Matematika Dasar", "2 pangkat 5 adalah ...",
            ["16", "25", "32", "64"], 2)
tambah_soal("Matematika Dasar", "7 kuadrat dikurangi 13 adalah ...",
            ["26", "36", "49", "62"], 1)


# ============================================================
# 5. DERET ANGKA (10 SOAL)
# ============================================================

tambah_soal("Deret Angka", "2, 4, 6, 8, ...",
            ["9", "10", "11", "12"], 1)
tambah_soal("Deret Angka", "5, 10, 20, 40, ...",
            ["45", "50", "60", "80"], 3)
tambah_soal("Deret Angka", "100, 90, 80, 70, ...",
            ["60", "65", "75", "85"], 0)
tambah_soal("Deret Angka", "1, 4, 9, 16, ...",
            ["20", "25", "30", "36"], 1)
tambah_soal("Deret Angka", "3, 6, 9, 12, ...",
            ["13", "14", "15", "16"], 2)
tambah_soal("Deret Angka", "64, 32, 16, 8, ...",
            ["2", "4", "6", "10"], 1)
tambah_soal("Deret Angka", "7, 14, 28, 56, ...",
            ["72", "98", "112", "120"], 2)
tambah_soal("Deret Angka", "2, 3, 5, 8, 12, 17, ...",
            ["22", "23", "24", "25"], 1)
tambah_soal("Deret Angka", "21, 18, 15, 12, ...",
            ["6", "8", "9", "10"], 2)
tambah_soal("Deret Angka", "13, 26, 52, ...",
            ["65", "78", "100", "104"], 3)


# ============================================================
# 6. LOGIKA PENALARAN (10 SOAL)
# ============================================================

tambah_soal("Logika", "Semua dokter adalah tenaga kesehatan. Rina adalah dokter. Kesimpulan yang benar ...",
            ["Rina bukan tenaga kesehatan", "Rina tenaga kesehatan",
             "Semua tenaga kesehatan adalah dokter", "Tidak dapat disimpulkan"], 1)
tambah_soal("Logika", "Semua A adalah B. Sebagian B adalah C. Apakah semua A pasti C?",
            ["Ya, selalu", "Tidak, belum tentu", "Pasti salah", "Semua C adalah A"], 1)
tambah_soal("Logika", "Jika hujan maka jalan basah. Jalan tidak basah. Maka, berdasarkan aturan tersebut ...",
            ["Pasti hujan", "Mungkin hujan", "Tidak hujan", "Jalan pasti rusak"], 2)
tambah_soal("Logika", "A lebih tinggi dari B, dan B lebih tinggi dari C. Maka ...",
            ["C lebih tinggi dari A", "A lebih tinggi dari C",
             "A sama tinggi dengan C", "Tidak dapat ditentukan"], 1)
tambah_soal("Logika", "Semua pegawai hadir tepat waktu. Dodi adalah pegawai. Maka ...",
            ["Dodi terlambat", "Dodi hadir tepat waktu",
             "Dodi bukan pegawai", "Tidak ada kesimpulan"], 1)
tambah_soal("Logika", "Andi lebih tua daripada Budi. Cici lebih muda daripada Budi. Siapa yang paling tua?",
            ["Andi", "Budi", "Cici", "Tidak diketahui"], 0)
tambah_soal("Logika", "3 mesin menghasilkan 300 unit per hari. 5 mesin setara menghasilkan ...",
            ["400", "450", "500", "550"], 2)
tambah_soal("Logika", "Hari ini Senin. Sepuluh hari lagi adalah hari ...",
            ["Selasa", "Rabu", "Kamis", "Jumat"], 2)
tambah_soal("Logika", "Budi lebih cepat daripada Andi. Andi lebih cepat daripada Citra. Paling lambat adalah ...",
            ["Budi", "Andi", "Citra", "Tidak diketahui"], 2)
tambah_soal("Logika", "Semua X adalah Y dan tidak ada Y yang Z. Kesimpulan yang benar ...",
            ["Semua X adalah Z", "Tidak ada X yang Z",
             "Sebagian X adalah Z", "Semua Z adalah X"], 1)


# ============================================================
# 7. PENALARAN ANALITIK (10 SOAL)
# ============================================================

tambah_soal("Analitik", "Tugas P harus sebelum Q dan Q harus sebelum R. Tugas pertama adalah ...",
            ["P", "Q", "R", "Tidak dapat ditentukan"], 0)
tambah_soal("Analitik", "A harus sebelum B dan B sebelum C. Urutan yang benar ...",
            ["C-B-A", "B-A-C", "A-B-C", "A-C-B"], 2)
tambah_soal("Analitik", "Empat orang membentuk pasangan unik. Jumlah pasangan yang mungkin adalah ...",
            ["4", "5", "6", "8"], 2)
tambah_soal("Analitik", "Dari 5 kandidat dipilih tepat 1 orang. Banyak pilihan yang mungkin ...",
            ["1", "2", "3", "5"], 3)
tambah_soal("Analitik", "Jika A=2, B=4, C=6, maka D=...",
            ["7", "8", "9", "10"], 1)
tambah_soal("Analitik", "Satu kotak memuat 12 barang. Tujuh kotak memuat ...",
            ["72", "78", "84", "90"], 2)
tambah_soal("Analitik", "Tiga tahap masing-masing berlangsung 5 menit. Total waktu ...",
            ["10 menit", "12 menit", "15 menit", "20 menit"], 2)
tambah_soal("Analitik", "Dua pekerja menghasilkan 20 unit dalam 4 jam. Produktivitas per pekerja per jam adalah ...",
            ["2 unit", "2,5 unit", "5 unit", "10 unit"], 1)
tambah_soal("Analitik", "B harus setelah A tetapi sebelum D. Urutan yang mungkin ...",
            ["A-B-C-D", "D-A-B-C", "A-D-B-C", "C-B-A-D"], 0)
tambah_soal("Analitik", "Empat orang menyelesaikan pekerjaan dalam 18 hari. Dengan 6 orang, secara proporsional perlu ...",
            ["9 hari", "10 hari", "12 hari", "15 hari"], 2)


# ============================================================
# 8. SPASIAL BERBASIS TEKS (10 SOAL)
# ============================================================

tambah_soal("Spasial", "Panah ↑ diputar 90 derajat searah jarum jam. Arahnya menjadi ...",
            ["←", "↑", "→", "↓"], 2)
tambah_soal("Spasial", "Sebuah kubus mempunyai berapa titik sudut?",
            ["4", "6", "8", "12"], 2)
tambah_soal("Spasial", "Sebuah kubus mempunyai berapa sisi bidang?",
            ["4", "5", "6", "8"], 2)
tambah_soal("Spasial", "Segi delapan mempunyai berapa sisi?",
            ["5", "6", "7", "8"], 3)
tambah_soal("Spasial", "Persegi panjang mempunyai berapa sudut?",
            ["2", "3", "4", "5"], 2)
tambah_soal("Spasial", "Urutan bentuk: lingkaran, persegi, lingkaran, persegi, ...",
            ["Lingkaran", "Segitiga", "Persegi", "Segi lima"], 0)
tambah_soal("Spasial", "Bentuk datar yang memiliki tiga sisi adalah ...",
            ["Persegi", "Lingkaran", "Segitiga", "Persegi panjang"], 2)
tambah_soal("Spasial", "Menghadap utara lalu berbelok 90 derajat ke kanan. Sekarang menghadap ...",
            ["Barat", "Timur", "Selatan", "Utara"], 1)
tambah_soal("Spasial", "Menghadap barat lalu berbelok ke kiri. Sekarang menghadap ...",
            ["Utara", "Barat", "Selatan", "Timur"], 2)
tambah_soal("Spasial", "Urutan poligon: segitiga, segi empat, segi lima, segi enam, ...",
            ["6 sisi", "7 sisi", "8 sisi", "9 sisi"], 1)


# ============================================================
# 9. KECENDERUNGAN MBTI-STYLE (12 SOAL)
# Tidak mempunyai jawaban benar atau salah.
# ============================================================

tambah_mbti(
    "E/I", "Saat bertemu lingkungan sosial baru, saya lebih nyaman ...",
    "Berkenalan dan berbicara dengan banyak orang",
    "Berbicara mendalam dengan beberapa orang",
    "E", "I",
)
tambah_mbti(
    "S/N", "Saat mempelajari hal baru, saya lebih suka ...",
    "Fakta konkret dan contoh nyata",
    "Konsep, pola, dan kemungkinan",
    "S", "N",
)
tambah_mbti(
    "T/F", "Saat mengambil keputusan, saya lebih menekankan ...",
    "Logika dan konsistensi",
    "Nilai dan dampak bagi orang lain",
    "T", "F",
)
tambah_mbti(
    "J/P", "Dalam pekerjaan, saya lebih menyukai ...",
    "Rencana dan jadwal yang jelas",
    "Fleksibilitas dalam menentukan langkah",
    "J", "P",
)
tambah_mbti(
    "E/I", "Setelah hari yang sibuk, saya biasanya memulihkan energi dengan ...",
    "Berinteraksi dengan orang lain",
    "Mempunyai waktu tenang sendiri",
    "E", "I",
)
tambah_mbti(
    "S/N", "Ketika membaca instruksi, saya lebih memperhatikan ...",
    "Detail dan langkah pelaksanaan",
    "Gambaran besar dan kaitan antargagasan",
    "S", "N",
)
tambah_mbti(
    "T/F", "Ketika memberi masukan kepada rekan, saya cenderung ...",
    "Langsung membahas fakta dan solusi",
    "Mempertimbangkan perasaan dan situasinya",
    "T", "F",
)
tambah_mbti(
    "J/P", "Saat mengerjakan proyek, saya lebih suka ...",
    "Menyelesaikannya dengan rencana terstruktur",
    "Menyesuaikan cara kerja saat ada informasi baru",
    "J", "P",
)
tambah_mbti(
    "E/I", "Dalam diskusi kelompok, saya biasanya ...",
    "Berpikir sambil berdiskusi",
    "Menyusun pemikiran dahulu sebelum berbicara",
    "E", "I",
)
tambah_mbti(
    "S/N", "Saya lebih tertarik pada ...",
    "Apa yang sudah terbukti dan dapat diterapkan",
    "Ide baru dan kemungkinan masa depan",
    "S", "N",
)
tambah_mbti(
    "T/F", "Dalam konflik kerja, fokus utama saya adalah ...",
    "Menemukan keputusan yang logis dan konsisten",
    "Menimbang kebutuhan orang yang terlibat",
    "T", "F",
)
tambah_mbti(
    "J/P", "Jika jadwal berubah mendadak, saya lebih nyaman ...",
    "Segera menetapkan rencana pengganti",
    "Membiarkan beberapa pilihan tetap terbuka",
    "J", "P",
)


# ============================================================
# 10. KECENDERUNGAN DISC-STYLE (8 SOAL)
# Tidak mempunyai jawaban benar atau salah.
# ============================================================

tambah_disc(
    "Saat tenggat pekerjaan sangat ketat, saya cenderung ...",
    "Segera mengambil keputusan dan mengejar hasil",
    "Membangun semangat dan mengajak orang berdiskusi",
    "Bekerja tenang secara bertahap",
    "Memeriksa detail agar kesalahan minimal",
)
tambah_disc(
    "Di lingkungan kerja baru, saya biasanya ...",
    "Mengambil inisiatif",
    "Cepat membangun relasi",
    "Mengamati dan menyesuaikan diri",
    "Mempelajari aturan dan prosedur",
)
tambah_disc(
    "Saat terjadi konflik, saya lebih cenderung ...",
    "Menghadapi masalah secara langsung",
    "Mendorong komunikasi terbuka",
    "Mencari titik temu secara tenang",
    "Mengumpulkan fakta sebelum mengambil posisi",
)
tambah_disc(
    "Saya paling puas ketika ...",
    "Target sulit berhasil dicapai",
    "Tim antusias dan hubungan berjalan baik",
    "Kerja sama berlangsung stabil",
    "Hasil memenuhi standar yang tinggi",
)
tambah_disc(
    "Saat menerima tugas baru, saya cenderung ...",
    "Langsung mulai dan menentukan tindakan",
    "Berdiskusi dengan pihak terkait",
    "Mengikuti alur kerja yang terbukti",
    "Memastikan spesifikasi dan detailnya jelas",
)
tambah_disc(
    "Dalam tim, peran yang terasa alami bagi saya adalah ...",
    "Pendorong keputusan",
    "Penghubung dan penyemangat",
    "Penjaga kestabilan kerja sama",
    "Penjaga mutu dan ketelitian",
)
tambah_disc(
    "Jika proses kerja terasa lambat, saya cenderung ...",
    "Mendorong perubahan segera",
    "Mengajak tim menemukan ide baru",
    "Mengusulkan perubahan bertahap",
    "Menganalisis proses sebelum mengubahnya",
)
tambah_disc(
    "Saat menghadapi masalah pekerjaan, saya biasanya ...",
    "Memutuskan langkah dan bergerak cepat",
    "Mencari dukungan dan masukan orang lain",
    "Menjaga proses tetap konsisten",
    "Mengecek data, aturan, dan ketepatan",
)


# Jangan lanjut bila jumlah item tidak tepat.
if len(BANK) != 100:
    raise RuntimeError(
        f"Bank soal harus berjumlah 100. Saat ini: {len(BANK)}"
    )


# ============================================================
# DATABASE
# ============================================================

def get_db():
    folder = os.path.dirname(DB_PATH)
    if folder:
        os.makedirs(folder, exist_ok=True)

    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS psikotes_hasil (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode TEXT NOT NULL,
            nama TEXT NOT NULL,
            tanggal_lahir TEXT,
            jenis_kelamin TEXT,
            jabatan TEXT,
            instansi TEXT,
            tanggal TEXT NOT NULL,
            total_soal INTEGER NOT NULL,
            benar INTEGER NOT NULL,
            persen REAL NOT NULL,
            kategori_json TEXT NOT NULL,
            mbti TEXT,
            disc TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


init_db()


# ============================================================
# PENGHITUNGAN SKOR
# ============================================================

MBTI_DIMENSI = [
    ("E", "I", "Interaksi sosial"),
    ("S", "N", "Cara memperoleh informasi"),
    ("T", "F", "Pertimbangan keputusan"),
    ("J", "P", "Gaya mengatur pekerjaan"),
]


def hitung_hasil(questions, answers):
    benar = 0
    kategori = {}

    mbti_votes = {
        "E": 0, "I": 0,
        "S": 0, "N": 0,
        "T": 0, "F": 0,
        "J": 0, "P": 0,
    }

    disc_votes = {"D": 0, "I": 0, "S": 0, "C": 0}

    for q in questions:
        value = answers.get(str(q["id"]))
        if value is None:
            continue

        try:
            index = int(value)
        except (TypeError, ValueError):
            continue

        if not 0 <= index < len(q["o"]):
            continue

        if q["tipe"] == "cognitive":
            key = q["kategori"]
            kategori.setdefault(key, {"benar": 0, "total": 0})
            kategori[key]["total"] += 1

            if index == q["a"]:
                benar += 1
                kategori[key]["benar"] += 1

        elif q["tipe"] == "mbti":
            huruf = q["map"][index]
            mbti_votes[huruf] += 1

        elif q["tipe"] == "disc":
            huruf = q["map"][index]
            disc_votes[huruf] += 1

    total_kognitif = sum(v["total"] for v in kategori.values())
    persen = round(benar * 100 / total_kognitif, 1) if total_kognitif else 0

    axes = []
    mbti_parts = []

    for left, right, nama in MBTI_DIMENSI:
        left_count = mbti_votes[left]
        right_count = mbti_votes[right]

        if left_count > right_count:
            hasil = left
        elif right_count > left_count:
            hasil = right
        else:
            hasil = left + "/" + right

        axes.append({
            "nama": nama,
            "kiri": left,
            "kanan": right,
            "nilai_kiri": left_count,
            "nilai_kanan": right_count,
            "hasil": hasil,
        })
        mbti_parts.append(hasil)

    mbti = " - ".join(mbti_parts)

    nilai_tertinggi = max(disc_votes.values())
    disc_puncak = [
        huruf for huruf, nilai in disc_votes.items()
        if nilai == nilai_tertinggi
    ]
    disc = "/".join(disc_puncak)

    return {
        "benar": benar,
        "total_kognitif": total_kognitif,
        "persen": persen,
        "kategori": kategori,
        "mbti": mbti,
        "mbti_axes": axes,
        "mbti_votes": mbti_votes,
        "disc": disc,
        "disc_votes": disc_votes,
    }


def indikator_nilai(persen):
    if persen >= 85:
        return (
            "Sangat Baik",
            "Skor latihan pada soal objektif tergolong tinggi.",
        )
    if persen >= 70:
        return (
            "Baik",
            "Skor latihan pada soal objektif tergolong baik.",
        )
    if persen >= 55:
        return (
            "Cukup",
            "Masih terdapat ruang untuk meningkatkan ketepatan jawaban.",
        )
    return (
        "Perlu Latihan",
        "Disarankan berlatih kembali pada kategori dengan nilai lebih rendah.",
    )


MBTI_DESC = {
    "E": "Cenderung menyukai interaksi dan aktivitas bersama orang lain.",
    "I": "Cenderung menyukai refleksi dan interaksi yang lebih terbatas.",
    "S": "Cenderung memperhatikan fakta, detail, dan pengalaman konkret.",
    "N": "Cenderung memperhatikan pola, ide, dan kemungkinan.",
    "T": "Cenderung menekankan logika dan konsistensi ketika memutuskan.",
    "F": "Cenderung mempertimbangkan nilai dan dampak keputusan bagi orang lain.",
    "J": "Cenderung menyukai struktur, rencana, dan penyelesaian yang terarah.",
    "P": "Cenderung menyukai fleksibilitas dan pilihan yang tetap terbuka.",
}

DISC_DESC = {
    "D": "Dominance: berorientasi pada tindakan, ketegasan, dan hasil.",
    "I": "Influence: berorientasi pada komunikasi, relasi, dan antusiasme.",
    "S": "Steadiness: berorientasi pada kestabilan, dukungan, dan kerja sama.",
    "C": "Conscientiousness: berorientasi pada ketelitian, data, dan standar.",
}


# ============================================================
# HALAMAN FORM PESERTA DAN 100 SOAL
# ============================================================

FORM_HTML = r"""
<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tes Psikotes SIPSI</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#f3f6fb;color:#1d2939;font-family:Arial,sans-serif}
.wrap{max-width:1000px;margin:24px auto;padding:0 14px}
.card{background:#fff;padding:22px;border-radius:15px;margin-bottom:16px;
      box-shadow:0 4px 18px rgba(18,59,112,.07)}
h1,h2{color:#123b70}
h1{margin-top:0}
.muted{color:#667085}
.notice{padding:13px;background:#eff6ff;border-left:4px solid #0860d8;
        border-radius:8px;line-height:1.55}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
input[type=text],input[type=date],select{
 width:100%;padding:11px;margin-top:6px;border:1px solid #d0d5dd;
 border-radius:9px;background:#fff
}
.field label{font-weight:700;font-size:14px}
.progress{position:sticky;top:6px;z-index:3;background:#fff;padding:12px;
 border:1px solid #d0d5dd;border-radius:10px;margin-bottom:14px}
.q{border:1px solid #e4e7ec;border-radius:12px;padding:15px;margin:13px 0}
.q h3{font-size:16px;line-height:1.5;margin:0 0 12px}
.opt{display:block;background:#f8fafc;border-radius:8px;padding:10px;margin:6px 0;
     font-weight:400;line-height:1.45}
.opt input{margin-right:7px}
.btn{background:#0860d8;color:#fff;border:0;border-radius:9px;
     padding:12px 18px;font-weight:700;cursor:pointer}
.warning{background:#fff4ed;color:#9a3412;padding:10px;border-radius:8px}
@media(max-width:650px){
 .grid{grid-template-columns:1fr}
 .card{padding:15px}
 .wrap{margin:12px auto;padding:0 9px}
}
</style>
</head>
<body>
<div class="wrap">
 <div class="card">
  <h1>Tes Psikotes SIPSI</h1>
  <p class="muted">100 soal | Urutan acak | Indikator hasil | Cetak hasil</p>
  <div class="notice">
   <b>Petunjuk:</b> Isi identitas dan jawab seluruh soal. Soal kemampuan
   memiliki jawaban benar/salah. Pertanyaan kepribadian hanya mencatat
   kecenderungan dan tidak memiliki jawaban benar atau salah.
  </div>
  {% if error %}
   <p class="warning">{{ error }}</p>
  {% endif %}
 </div>

 <form method="post" action="{{ url_for('psikotes.submit') }}" onsubmit="return validasiForm()">
  <div class="card">
   <h2>Identitas Peserta</h2>
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
     <label>Tanggal Lahir
      <input type="date" name="tanggal_lahir">
     </label>
    </div>
    <div class="field">
     <label>Jenis Kelamin
      <select name="jenis_kelamin">
       <option value="">-- Pilih --</option>
       <option value="Laki-laki">Laki-laki</option>
       <option value="Perempuan">Perempuan</option>
       <option value="Tidak dicantumkan">Tidak dicantumkan</option>
      </select>
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
   Terjawab: <b id="jumlahTerjawab">0</b> / {{ questions|length }}
  </div>

  <div class="card">
   <h2>Daftar Soal</h2>
   {% for q in questions %}
    <div class="q">
     <h3>{{ loop.index }}. {{ q.q }}</h3>
     {% for opsi in q.o %}
      <label class="opt">
       <input
        type="radio"
        name="q_{{ q.id }}"
        value="{{ loop.index0 }}"
        {% if loop.first %}required{% endif %}
        onchange="perbaruiProgress()">
       <b>{{ "ABCD"[loop.index0] }}.</b> {{ opsi }}
      </label>
     {% endfor %}
    </div>
   {% endfor %}

   <button type="submit" class="btn">Selesaikan Tes dan Lihat Hasil</button>
  </div>
 </form>
</div>
<script>
function perbaruiProgress(){
 const kelompok = new Set();
 document.querySelectorAll('input[type="radio"]:checked').forEach(function(el){
   kelompok.add(el.name);
 });
 document.getElementById('jumlahTerjawab').textContent = kelompok.size;
}
function validasiForm(){
 const total = {{ questions|length }};
 const kelompok = new Set();
 document.querySelectorAll('input[type="radio"]:checked').forEach(function(el){
   kelompok.add(el.name);
 });
 if(kelompok.size !== total){
   alert('Masih ada ' + (total - kelompok.size) + ' soal yang belum dijawab.');
   return false;
 }
 return confirm('Kirim jawaban dan hitung hasil tes sekarang?');
}
</script>
</body>
</html>
"""


# ============================================================
# HALAMAN HASIL DAN CETAK
# ============================================================

RESULT_HTML = r"""
<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hasil Psikotes SIPSI</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#f3f6fb;color:#1d2939;font-family:Arial,sans-serif}
.wrap{max-width:1000px;margin:24px auto;padding:0 14px}
.card{background:#fff;padding:22px;border-radius:14px;margin-bottom:16px;
      box-shadow:0 3px 15px rgba(0,0,0,.05)}
h1,h2{color:#123b70}
.info{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.item{padding:12px;background:#f8fafc;border-radius:8px;overflow-wrap:anywhere}
.score{font-size:42px;font-weight:800;color:#0860d8}
.badge{display:inline-block;padding:7px 11px;border-radius:20px;background:#eef6ff;
       font-weight:700}
table{width:100%;border-collapse:collapse;margin-top:14px}
th,td{padding:10px;border-bottom:1px solid #eaecf0;text-align:left}
th{background:#f8fafc}
.actions{display:flex;gap:10px;flex-wrap:wrap}
.btn{display:inline-block;background:#0860d8;color:white;border:0;border-radius:9px;
     padding:12px 18px;text-decoration:none;font-weight:700;cursor:pointer}
.secondary{background:#667085}
.muted{color:#667085}
@media(max-width:650px){
 .info{grid-template-columns:1fr}
 .card{padding:15px}
 .wrap{margin:12px auto;padding:0 9px}
 table{font-size:13px}
 th,td{padding:7px}
}
@media print{
 body{background:#fff}
 .wrap{max-width:none;margin:0;padding:0}
 .card{box-shadow:none;border:1px solid #ddd;break-inside:avoid}
 .actions{display:none!important}
}
</style>
</head>
<body>
<div class="wrap">
 <div class="card">
  <h1>HASIL TES PSIKOTES SIPSI</h1>
  <div class="info">
   <div class="item"><b>Kode peserta</b><br>{{ data.kode }}</div>
   <div class="item"><b>Nama</b><br>{{ data.nama }}</div>
   <div class="item"><b>Tanggal tes</b><br>{{ data.tanggal }}</div>
   <div class="item"><b>Tanggal lahir</b><br>{{ data.tanggal_lahir or "-" }}</div>
   <div class="item"><b>Jenis kelamin</b><br>{{ data.jenis_kelamin or "-" }}</div>
   <div class="item"><b>Jabatan</b><br>{{ data.jabatan or "-" }}</div>
   <div class="item"><b>Instansi / unit</b><br>{{ data.instansi or "-" }}</div>
  </div>
 </div>

 <div class="card">
  <h2>Indikator Kemampuan</h2>
  <div class="score">{{ hasil.persen }}%</div>
  <p><span class="badge">{{ level }}</span></p>
  <p>{{ deskripsi_level }}</p>
  <p>
   Jawaban benar: <b>{{ hasil.benar }}</b> dari
   <b>{{ hasil.total_kognitif }}</b> soal kemampuan.
  </p>
  <table>
   <thead>
    <tr>
     <th>Kategori</th>
     <th>Benar</th>
     <th>Total</th>
     <th>Persentase</th>
    </tr>
   </thead>
   <tbody>
    {% for nama, nilai in hasil.kategori.items() %}
     <tr>
      <td>{{ nama }}</td>
      <td>{{ nilai.benar }}</td>
      <td>{{ nilai.total }}</td>
      <td>{{ ((nilai.benar / nilai.total) * 100)|round(1) }}%</td>
     </tr>
    {% endfor %}
   </tbody>
  </table>
 </div>

 <div class="card">
  <h2>Indikator Kepribadian MBTI-style</h2>
  <p><b>Ringkasan pilihan:</b></p>
  <p><span class="badge">{{ hasil.mbti }}</span></p>
  <table>
   <thead>
    <tr>
     <th>Dimensi</th>
     <th>Pilihan pertama</th>
     <th>Pilihan kedua</th>
     <th>Ringkasan</th>
    </tr>
   </thead>
   <tbody>
    {% for a in hasil.mbti_axes %}
     <tr>
      <td>{{ a.nama }}</td>
      <td>{{ a.kiri }}: {{ a.nilai_kiri }}</td>
      <td>{{ a.kanan }}: {{ a.nilai_kanan }}</td>
      <td>{{ a.hasil }}</td>
     </tr>
    {% endfor %}
   </tbody>
  </table>
  <p class="muted">
   Ringkasan ini hanya menggambarkan pilihan pada pertanyaan dalam modul ini,
   bukan penetapan tipe kepribadian resmi.
  </p>
 </div>

 <div class="card">
  <h2>Indikator Kepribadian DISC-style</h2>
  <p><b>Kecenderungan yang memperoleh skor tertinggi:</b></p>
  <p><span class="badge">{{ hasil.disc }}</span></p>
  <table>
   <thead><tr><th>Gaya</th><th>Jumlah pilihan</th><th>Deskripsi umum</th></tr></thead>
   <tbody>
    {% for huruf, nilai in hasil.disc_votes.items() %}
     <tr>
      <td>{{ huruf }}</td>
      <td>{{ nilai }}</td>
      <td>{{ disc_desc[huruf] }}</td>
     </tr>
    {% endfor %}
   </tbody>
  </table>
  <p class="muted">
   Hasil bergantung pada pilihan peserta dalam pertanyaan singkat ini.
   Ini bukan tes DISC terstandar.
  </p>
 </div>

 <div class="card">
  <h2>Catatan Interpretasi</h2>
  <p>
   Nilai kemampuan merupakan hasil latihan dari soal pilihan ganda dalam modul.
   Hasil tidak otomatis setara dengan IQ atau hasil pemeriksaan psikologis formal.
  </p>
  <p>
   Indikator MBTI-style dan DISC-style merupakan ringkasan kecenderungan
   jawaban, bukan diagnosis dan bukan satu-satunya dasar keputusan kepegawaian.
  </p>
 </div>

 <div class="card actions">
  <button class="btn" onclick="window.print()">Cetak Hasil</button>
  <a class="btn secondary" href="{{ url_for('psikotes.index') }}">Tes Baru</a>
 </div>
</div>
</body>
</html>
"""


# ============================================================
# ROUTE TES
# ============================================================

@psikotes_bp.route("/", methods=["GET"])
def index():
    # Urutan 100 soal diacak setiap kali memulai sesi baru.
    questions = list(BANK)
    random.shuffle(questions)

    session["psikotes_ids"] = [q["id"] for q in questions]

    return render_template_string(
        FORM_HTML,
        questions=questions,
        error=None,
    )


@psikotes_bp.route("/submit", methods=["POST"])
def submit():
    ids = session.get("psikotes_ids")

    if not ids or len(ids) != 100:
        return redirect(url_for("psikotes.index"))

    by_id = {q["id"]: q for q in BANK}

    try:
        questions = [by_id[int(qid)] for qid in ids]
    except (KeyError, TypeError, ValueError):
        session.pop("psikotes_ids", None)
        return redirect(url_for("psikotes.index"))

    # Validasi seluruh jawaban di server.
    answers = {}

    for q in questions:
        key = "q_" + str(q["id"])
        value = request.form.get(key)

        if value is None:
            return (
                render_template_string(
                    FORM_HTML,
                    questions=questions,
                    error="Ada soal yang belum dijawab. Silakan lengkapi tes.",
                ),
                400,
            )

        try:
            index = int(value)
        except ValueError:
            return "Pilihan jawaban tidak valid.", 400

        if not 0 <= index < len(q["o"]):
            return "Pilihan jawaban tidak valid.", 400

        answers[str(q["id"])] = index

    hasil = hitung_hasil(questions, answers)
    level, deskripsi_level = indikator_nilai(hasil["persen"])

    data = {
        "kode": request.form.get("kode", "").strip(),
        "nama": request.form.get("nama", "").strip(),
        "tanggal_lahir": request.form.get("tanggal_lahir", "").strip(),
        "jenis_kelamin": request.form.get("jenis_kelamin", "").strip(),
        "jabatan": request.form.get("jabatan", "").strip(),
        "instansi": request.form.get("instansi", "").strip(),
        "tanggal": datetime.now().strftime("%d-%m-%Y %H:%M"),
    }

    if not data["kode"] or not data["nama"]:
        return "Kode peserta dan nama harus diisi.", 400

    # Simpan data hasil ke database terpisah.
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO psikotes_hasil
            (
                kode, nama, tanggal_lahir, jenis_kelamin,
                jabatan, instansi, tanggal,
                total_soal, benar, persen, kategori_json,
                mbti, disc, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["kode"],
                data["nama"],
                data["tanggal_lahir"],
                data["jenis_kelamin"],
                data["jabatan"],
                data["instansi"],
                data["tanggal"],
                100,
                hasil["benar"],
                hasil["persen"],
                json.dumps(hasil["kategori"], ensure_ascii=False),
                hasil["mbti"],
                hasil["disc"],
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    # Menghindari tes yang sama terkirim kembali melalui sesi browser.
    session.pop("psikotes_ids", None)

    return render_template_string(
        RESULT_HTML,
        data=data,
        hasil=hasil,
        level=level,
        deskripsi_level=deskripsi_level,
        disc_desc=DISC_DESC,
    )


# ============================================================
# INTEGRASI KE app.py
# ============================================================
#
# Tambahkan setelah objek Flask app dibuat:
#
# from sipsi_psikotes import psikotes_bp
# app.register_blueprint(psikotes_bp)
#
# URL tes:
# http://127.0.0.1:5000/sipsi/psikotes/
#
# URL untuk kembali memulai tes:
# /sipsi/psikotes/
#
# Pastikan aplikasi Flask sudah memiliki secret_key karena modul ini
# menggunakan session untuk mempertahankan urutan soal.