# -*- coding: utf-8 -*-
"""Skoring Enterprise  — bukan diagnosis klinis."""
from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).resolve().parent / "questions_600.json"

CATEGORY = [
    (0, 20, "Sangat Rendah"),
    (21, 40, "Rendah"),
    (41, 60, "Sedang"),
    (61, 80, "Tinggi"),
    (81, 100, "Sangat Tinggi"),
]

CRITICAL = {"Pa", "Sc", "Pd", "D"}  # domain yang perlu perhatian ekstra


def load_bank():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def level_of(score_0_100: float) -> str:
    for lo, hi, lab in CATEGORY:
        if lo <= score_0_100 <= hi:
            return lab
    return "Sedang"


def score_answers(jawaban: dict) -> dict:
    """
    jawaban: {question_id: 'Ya'|'Tidak'}
    Return detail per domain + indeks umum.
    """
    bank = load_bank()
    by_id = {q["id"]: q for q in bank["questions"]}
    domain_raw = {}
    domain_n = {}

    for qid, ans in jawaban.items():
        q = by_id.get(int(qid))
        if not q:
            continue
        a = (ans or "").strip().lower()
        is_ya = a == "ya"
        if q.get("reverse"):
            poin = 0 if is_ya else 1
        else:
            poin = 1 if is_ya else 0
        code = q["domain_code"]
        domain_raw[code] = domain_raw.get(code, 0) + poin
        domain_n[code] = domain_n.get(code, 0) + 1

    domains_meta = {d["code"]: d for d in bank["meta"]["domains"]}
    detail = {}
    for code, meta in domains_meta.items():
        n = domain_n.get(code, 0)
        raw = domain_raw.get(code, 0)
        pct = round((raw / n) * 100) if n else 0
        detail[code] = {
            "code": code,
            "name": meta["name"],
            "skor_mentah": raw,
            "jumlah_soal": n,
            "skor": pct,
            "level": level_of(pct),
            "kritis": code in CRITICAL and pct >= 50,
        }

    scores = [v["skor"] for v in detail.values() if v["jumlah_soal"]]
    index = round(sum(scores) / len(scores)) if scores else 0
    # Indeks kesehatan jiwa: semakin rendah gejala semakin "baik"
    # Tampilkan juga sebagai 100 - index untuk mirip SIPSI "semakin tinggi semakin sehat"
    wellness = max(0, min(100, 100 - index))

    flags = [v["name"] for v in detail.values() if v["kritis"]]
    interpretasi = _interpret(detail, wellness, flags)
    saran = _saran(detail, flags)

    return {
        "domain": detail,
        "gejala_index": index,
        "wellness_index": wellness,
        "wellness_level": level_of(wellness) if False else _wellness_label(wellness),
        "flags": flags,
        "interpretasi": interpretasi,
        "saran": saran,
        "disclaimer": bank["meta"]["disclaimer"],
    }


def _wellness_label(w: int) -> str:
    if w >= 81:
        return "Sangat Baik"
    if w >= 61:
        return "Baik"
    if w >= 41:
        return "Sedang / Cukup Sehat"
    if w >= 21:
        return "Rendah"
    return "Sangat Rendah"


def _interpret(detail: dict, wellness: int, flags: list) -> str:
    parts = [
        f"Hasil skrining Enterprise menunjukkan Indeks Kesejahteraan sekitar {wellness}/100 "
        f"({_wellness_label(wellness)})."
    ]
    tinggi = [v["name"] for v in detail.values() if v["skor"] >= 61]
    if tinggi:
        parts.append("Domain dengan skor gejala lebih tinggi: " + ", ".join(tinggi) + ".")
    if flags:
        parts.append(
            "Beberapa domain memerlukan perhatian tambahan: " + ", ".join(flags) + "."
        )
    parts.append(
        "Ini adalah alat skrining, bukan diagnosis klinis. "
        "Konsultasikan hasil dengan tenaga profesional jika diperlukan."
    )
    return " ".join(parts)


def _saran(detail: dict, flags: list) -> list:
    s = [
        "Istirahat cukup 7–8 jam dan jaga pola tidur.",
        "Kelola stres dengan napas dalam, olahraga ringan, atau aktivitas yang menenangkan.",
        "Jaga komunikasi dengan orang yang dipercaya.",
        "Batasi konsumsi zat yang dapat memengaruhi kondisi psikologis.",
    ]
    if flags:
        s.append(
            "Karena ada domain yang menonjol, disarankan konsultasi dengan psikolog/psikiater."
        )
    if any(detail.get(c, {}).get("skor", 0) >= 50 for c in ("D", "Pa", "Sc")):
        s.append(
            "Jika muncul ide menyakiti diri atau gejala mengganggu berat, segera hubungi bantuan darurat / hotline kesehatan jiwa / IGD."
        )
    return s
