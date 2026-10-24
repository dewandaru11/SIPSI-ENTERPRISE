import fitz  # pip install PyMuPDF
import os

PDF_FILE = "ilide.info-sub-tes-pola-gambar-pr_0bd2f2d64068352121ecd74ad89ed409.pdf"
OUT_DIR = "static/pola"

if not os.path.exists(OUT_DIR):
    os.makedirs(OUT_DIR)

if not os.path.exists(PDF_FILE):
    print(f"Error: File {PDF_FILE} tidak ditemukan di folder ini.")
else:
    doc = fitz.open(PDF_FILE)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=300)
        pix.save(f"{OUT_DIR}/halaman_{i+1}.png")
    print(f"Berhasil! Buka folder {OUT_DIR}, Anda akan melihat gambar halaman PDF.")