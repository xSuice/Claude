"""Erzeugt die PWA-Icons (PNG) ohne Zusatzbibliothek: portal-ui/web/icon-192.png, icon-512.png, apple-touch-icon.png.
Motiv wie das Logo im Portal: dunkler Grund, rotes Sechseck. Aufruf: python portal-ui/make-icons.py
Gehoert zu: portal-ui/web/manifest.webmanifest, portal-ui/web/sw.js (Vault: Server-Claude Variante 2)."""
import os
import struct
import zlib

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
BG, FILL, EDGE = (7, 8, 12), (20, 10, 16), (229, 23, 63)


def hexagon(cx, cy, r):
    import math
    return [(cx + r * math.cos(math.radians(60 * i - 90)), cy + r * math.sin(math.radians(60 * i - 90))) for i in range(6)]


def inside(poly, x, y):
    n, ok = len(poly), False
    for i in range(n):
        x1, y1, x2, y2 = *poly[i], *poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            ok = not ok
    return ok


def dist_edge(poly, x, y):
    best = 1e9
    for i in range(len(poly)):
        x1, y1, x2, y2 = *poly[i], *poly[(i + 1) % len(poly)]
        dx, dy = x2 - x1, y2 - y1
        t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        best = min(best, ((x - (x1 + t * dx)) ** 2 + (y - (y1 + t * dy)) ** 2) ** 0.5)
    return best


def png(size, margin):
    poly = hexagon(size / 2, size / 2, size * (0.5 - margin))
    stroke = size * 0.03
    ss = 2                                         # 2x2 Unterabtastung gegen Treppen
    rows = []
    for py in range(size):
        row = bytearray([0])
        for px in range(size):
            acc = [0, 0, 0]
            for sy in range(ss):
                for sx in range(ss):
                    x, y = px + (sx + 0.5) / ss, py + (sy + 0.5) / ss
                    c = EDGE if (inside(poly, x, y) and dist_edge(poly, x, y) < stroke) or (not inside(poly, x, y) and dist_edge(poly, x, y) < stroke / 2) \
                        else FILL if inside(poly, x, y) else BG
                    for k in range(3):
                        acc[k] += c[k]
            row += bytes(v // (ss * ss) for v in acc)
        rows.append(bytes(row))
    raw = zlib.compress(b"".join(rows), 9)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)

    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")


for name, size, margin in (("icon-192.png", 192, 0.14), ("icon-512.png", 512, 0.14), ("apple-touch-icon.png", 180, 0.14)):
    open(os.path.join(OUT, name), "wb").write(png(size, margin))
    print("geschrieben:", name)
