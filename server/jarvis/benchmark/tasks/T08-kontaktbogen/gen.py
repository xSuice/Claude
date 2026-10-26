"""T08 generator: PNG images with a seeded size and a unique solid colour each."""
import random
from pathlib import Path

from PIL import Image


def make(out: Path, seed: int, name: str = 'bilder') -> Path:
    rnd = random.Random(seed)
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    for i in range(rnd.randrange(5, 9)):
        w = rnd.randrange(120, 700)
        h = rnd.randrange(60, w + 1)   # Höhe der Vorschau höchstens 200: passt in die Zelle
        Image.new('RGB', (w, h), (30 + i * 25, rnd.randrange(256), 255 - i * 25)).save(d / f'bild{i + 1:02d}.png')
    (d / 'notiz.txt').write_text('kein Bild', encoding='utf-8')
    return d


def expected(d: Path) -> dict:
    pics = sorted(d.glob('*.png'))
    sizes = {p.name: Image.open(p).size for p in pics}
    thumbs = {n: (200, max(1, round(h * 200 / w))) for n, (w, h) in sizes.items()}
    rows = -(-len(pics) // 3)
    return {'names': [p.name for p in pics], 'thumbs': thumbs, 'sheet': (640, rows * 200 + (rows + 1) * 10),
            'colors': {p.name: Image.open(p).convert('RGB').getpixel((0, 0)) for p in pics}}


def visible(out: Path):
    make(out, 1)
