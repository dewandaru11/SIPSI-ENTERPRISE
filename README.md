# SIPSI Interprise — 600 Soal Orisinal

## PENTING
- Soal dibuat orisinal untuk skrining.
- **Bukan diagnosis klinis.**
- Nama domain (Hs, D, Hy, …) hanya struktur pengelompokan.
- Hasil bersifat skrining awal.

## Isi paket
| File | Keterangan |
|------|------------|
| `questions_600.json` | 600 soal Ya/Tidak orisinal (60 per domain × 10 domain) |
| `scoring_interprise.py` | Skoring + interpretasi + saran otomatis |
| `app.py` | Aplikasi utama Flask + desktop |

## 10 Domain
1. **Hs** — Hipokondriasis (keluhan tubuh)
2. **D** — Depresi
3. **Hy** — Histeria / keluhan terkait stres
4. **Pd** — Deviasi psikopatiform (impuls/aturan)
5. **Mf** — Peran & minat (skrining umum)
6. **Pa** — Paranoia / kecurigaan
7. **Pt** — Psikatstenia (cemas, ruminasi)
8. **Sc** — Pengalaman tidak biasa / menarik diri
9. **Ma** — Hipomania (energi/impuls cepat)
10. **Si** — Introversi sosial

## Cara skoring (sederhana)
- Jawaban **Ya** pada item gejala = 1 (kecuali `reverse=true`)
- Skor domain = % gejala di domain itu (0–100)
- **Wellness index** = 100 − rata-rata skor domain (semakin tinggi semakin “sehat”)
- Level: Sangat Rendah → Sangat Tinggi (gejala) / Sangat Baik → Sangat Rendah (wellness)

## Etika
Domain depresi / kecurigaan / pengalaman tidak biasa hanya untuk **skrining awal**.  
Jika ada indikasi risiko, tampilkan rujukan ke profesional / hotline.
