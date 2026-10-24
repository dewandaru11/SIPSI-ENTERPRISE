# -*- coding: utf-8 -*-
"""Helper SVG stimulus Wartegg klasik (8 kotak) — versi diperbesar.

Dipakai bersama oleh modul psikotes lain yang butuh gambar Wartegg.
"""


def _svg_wartegg(n, size=150):
    """Kotak Wartegg dengan stimulus klasik (1..8).

    Menghasilkan blok HTML berisi SVG berbingkai tebal, background putih,
    drop-shadow, dan caption 'STIMULUS WARTEGG n/8' di bawahnya — sehingga
    tampil jelas sebagai gambar stimulus (bukan sekedar ikon inline).
    """
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