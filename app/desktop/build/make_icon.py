#!/usr/bin/env python3
"""Erzeugt build/icon.ico (256x256 PNG im ICO) ohne Zusatzpakete: Verlauf-Quadrat mit weissem Haus."""
import math
import os
import struct
import zlib

N = 256
SS = 3  # Glaettung durch Mehrfachabtastung
SEGS = [((0.23, 0.70), (0.23, 0.44)), ((0.23, 0.44), (0.50, 0.26)), ((0.50, 0.26), (0.77, 0.44)), ((0.77, 0.44), (0.77, 0.70)),
        ((0.42, 0.70), (0.42, 0.55)), ((0.42, 0.55), (0.58, 0.55)), ((0.58, 0.55), (0.58, 0.70))]
W = 0.045  # halbe Strichbreite


def dist(px, py, a, b):
    ax, ay = a; bx, by = b
    dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def rr(px, py, r=0.22):
    x, y = abs(px - 0.5), abs(py - 0.5)
    qx, qy = x - (0.5 - r), y - (0.5 - r)
    return math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - r <= 0


rows = []
for j in range(N):
    row = bytearray([0])
    for i in range(N):
        acc = [0, 0, 0, 0]
        for sj in range(SS):
            for si in range(SS):
                px, py = (i + (si + .5) / SS) / N, (j + (sj + .5) / SS) / N
                if not rr(px, py):
                    continue
                t = (px + py) / 2
                col = (int(0x6d + (0x22 - 0x6d) * t), int(0x5e + (0xc1 - 0x5e) * t), int(0xfc + (0xc3 - 0xfc) * t))
                if any(dist(px, py, a, b) <= W for a, b in SEGS):
                    col = (255, 255, 255)
                acc[0] += col[0]; acc[1] += col[1]; acc[2] += col[2]; acc[3] += 255
        n = SS * SS
        if acc[3] == 0:
            row += bytes([0, 0, 0, 0])
        else:
            c = acc[3] // 255
            row += bytes([acc[0] // c, acc[1] // c, acc[2] // c, acc[3] // n])
    rows.append(bytes(row))
raw = b''.join(rows)


def chunk(tag, data):
    return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)


png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', N, N, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')
ico = struct.pack('<HHH', 0, 1, 1) + struct.pack('<BBBBHHII', 0, 0, 0, 0, 1, 32, len(png), 22) + png
here = os.path.dirname(os.path.abspath(__file__))
open(os.path.join(here, 'icon.ico'), 'wb').write(ico)
open(os.path.join(here, 'icon.png'), 'wb').write(png)
print('icon.ico', len(ico), 'Bytes')
