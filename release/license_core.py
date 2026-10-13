# -*- coding: utf-8 -*-
"""
Inti lisensi SIPSI — dipakai app.py dan buat_serial.py
Ganti SECRET hanya di kedua file ini secara bersamaan.

Kuota:
  - max_peserta  → dari serial
  - used_peserta → counter PERMANEN di sipsi.lic (hanya naik, tidak turun
                   saat data riwayat dihapus)
"""
from __future__ import annotations

import hashlib
import hmac
import os
import struct
import json
from datetime import datetime

# ============================================================
# RAHASIA PEMBUAT SERIAL — ganti sesuai keinginan Anda
# Harus SAMA di app yang dibagikan ke klien.
# ============================================================
SECRET = b"SIPSI-BK-TECH-ADHA-HY-2026-RAHASIA-JANGAN-SEBAR"

PREFIX = "SIPSI"
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # tanpa 0 O 1 I


def _b32_encode(data: bytes) -> str:
    """Base32 custom (alphabet di atas)."""
    bits = ""
    for b in data:
        bits += f"{b:08b}"
    while len(bits) % 5:
        bits += "0"
    out = []
    for i in range(0, len(bits), 5):
        chunk = bits[i : i + 5]
        out.append(ALPHABET[int(chunk, 2)])
    return "".join(out)


def _b32_decode(text: str) -> bytes:
    text = text.upper().replace(" ", "").replace("-", "")
    if text.startswith(PREFIX):
        text = text[len(PREFIX) :]
    bits = ""
    for ch in text:
        if ch not in ALPHABET:
            raise ValueError("Karakter serial tidak valid")
        bits += f"{ALPHABET.index(ch):05b}"
    nbytes = len(bits) // 8
    out = bytearray()
    for i in range(nbytes):
        out.append(int(bits[i * 8 : (i + 1) * 8], 2))
    return bytes(out)


def generate_serial(max_peserta: int, note: str = "") -> str:
    """
    Buat serial.
    max_peserta: 1 .. 65535  (batas jumlah peserta)
    """
    max_peserta = int(max_peserta)
    if max_peserta < 1 or max_peserta > 65535:
        raise ValueError("max_peserta harus 1..65535")
    nonce = int.from_bytes(os.urandom(2), "big")
    payload = struct.pack(">HH", max_peserta, nonce)  # 4 bytes
    mac = hmac.new(SECRET, payload, hashlib.sha256).digest()[:4]
    raw = payload + mac  # 8 bytes → ~13 char base32
    enc = _b32_encode(raw)
    while len(enc) % 4:
        enc += ALPHABET[0]
    groups = [enc[i : i + 4] for i in range(0, len(enc), 4)]
    return PREFIX + "-" + "-".join(groups[:4])  # SIPSI-XXXX-XXXX-XXXX-XXXX


def validate_serial(serial: str) -> dict:
    """
    Validasi serial.
    Return: {"ok": True, "max_peserta": N} atau {"ok": False, "error": "..."}
    """
    try:
        s = (serial or "").strip().upper().replace(" ", "")
        if not s:
            return {"ok": False, "error": "Serial kosong"}
        raw = _b32_decode(s)
        if len(raw) < 8:
            return {"ok": False, "error": "Serial tidak lengkap"}
        payload, mac = raw[:4], raw[4:8]
        expect = hmac.new(SECRET, payload, hashlib.sha256).digest()[:4]
        if not hmac.compare_digest(mac, expect):
            return {"ok": False, "error": "Serial tidak valid / palsu"}
        max_peserta, nonce = struct.unpack(">HH", payload)
        if max_peserta < 1:
            return {"ok": False, "error": "Serial rusak"}
        return {"ok": True, "max_peserta": int(max_peserta), "nonce": int(nonce)}
    except Exception as e:
        return {"ok": False, "error": f"Serial tidak dapat dibaca ({e})"}


def license_path(base_dir: str) -> str:
    return os.path.join(base_dir, "sipsi.lic")


def _write_license_file(base_dir: str, data: dict) -> None:
    """Tulis sipsi.lic + sipsi.lic.sig (signature mengikuti isi file)."""
    path = license_path(base_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    dig = hmac.new(
        SECRET, json.dumps(data, sort_keys=True).encode(), hashlib.sha256
    ).hexdigest()
    with open(path + ".sig", "w", encoding="utf-8") as f:
        f.write(dig)


def _read_raw_license(base_dir: str) -> dict | None:
    path = license_path(base_dir)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_license(base_dir: str, serial: str, info: dict) -> None:
    """
    Simpan aktivasi.
    - Serial SAMA dengan sebelumnya → used_peserta dipertahankan (tidak reset).
    - Serial BERBEDA → used_peserta mulai dari 0.
    """
    serial = serial.strip().upper()
    max_p = int(info["max_peserta"])
    used = 0
    old = None
    try:
        old = _read_raw_license(base_dir)
    except Exception:
        old = None
    if old and (old.get("serial") or "").strip().upper() == serial:
        try:
            used = int(old.get("used_peserta") or 0)
        except (TypeError, ValueError):
            used = 0
        if used < 0:
            used = 0

    data = {
        "serial": serial,
        "max_peserta": max_p,
        "used_peserta": used,
        "activated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _write_license_file(base_dir, data)


def load_license(base_dir: str) -> dict:
    """
    Baca lisensi tersimpan + verifikasi ulang serial & signature file.
    """
    path = license_path(base_dir)
    if not os.path.exists(path):
        return {"ok": False, "error": "Belum aktivasi", "need_activate": True}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        serial = data.get("serial") or ""
        chk = validate_serial(serial)
        if not chk.get("ok"):
            return {
                "ok": False,
                "error": chk.get("error") or "Serial invalid",
                "need_activate": True,
            }
        # cek signature file
        sig_path = path + ".sig"
        if os.path.exists(sig_path):
            dig = hmac.new(
                SECRET, json.dumps(data, sort_keys=True).encode(), hashlib.sha256
            ).hexdigest()
            with open(sig_path, "r", encoding="utf-8") as f:
                old = f.read().strip()
            if not hmac.compare_digest(dig, old):
                return {
                    "ok": False,
                    "error": "File lisensi rusak / diubah",
                    "need_activate": True,
                }
        max_p = int(chk["max_peserta"])
        try:
            used = int(data.get("used_peserta") or 0)
        except (TypeError, ValueError):
            used = 0
        if used < 0:
            used = 0
        return {
            "ok": True,
            "serial": serial,
            "max_peserta": max_p,
            "used_peserta": used,
            "activated_at": data.get("activated_at"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "need_activate": True}


def get_used_peserta(base_dir: str) -> int:
    """Ambil counter used permanen (0 jika belum aktivasi / error)."""
    lic = load_license(base_dir)
    if not lic.get("ok"):
        return 0
    return int(lic.get("used_peserta") or 0)


def consume_peserta(base_dir: str) -> dict:
    """
    Naikkan used_peserta +1 (permanen).
    Return: {"ok": True, "used": N, "max": M} atau {"ok": False, "error": "..."}.
    Dipanggil saat peserta BARU berhasil dibuat.
    """
    path = license_path(base_dir)
    if not os.path.exists(path):
        return {"ok": False, "error": "Belum aktivasi"}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        serial = data.get("serial") or ""
        chk = validate_serial(serial)
        if not chk.get("ok"):
            return {"ok": False, "error": chk.get("error") or "Serial invalid"}
        max_p = int(chk["max_peserta"])
        try:
            used = int(data.get("used_peserta") or 0)
        except (TypeError, ValueError):
            used = 0
        if used < 0:
            used = 0
        if used >= max_p:
            return {
                "ok": False,
                "error": "Kuota peserta habis (%s/%s)" % (used, max_p),
                "used": used,
                "max": max_p,
            }
        used += 1
        data["used_peserta"] = used
        data["max_peserta"] = max_p
        _write_license_file(base_dir, data)
        return {"ok": True, "used": used, "max": max_p}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mask_serial(serial: str) -> str:
    s = (serial or "").upper()
    parts = s.split("-")
    if len(parts) >= 3:
        return parts[0] + "-" + parts[1] + "-****-****"
    if len(s) > 10:
        return s[:8] + "****"
    return "****"
