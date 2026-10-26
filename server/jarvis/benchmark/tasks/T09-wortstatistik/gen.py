"""T09 generator: a text with a seeded word distribution (ties avoided so the top-5 is unambiguous)."""
import random
import re
from collections import Counter
from pathlib import Path

POOL = ['server', 'Dienst', 'Aufgabe', 'Test', 'Datei', 'Plan', 'Woche', 'Team', 'Wert', 'Messung', 'Lauf', 'Fehler', 'Ergebnis', 'Prüfung']


def make(out: Path, seed: int, name: str = 'text.txt') -> Path:
    rnd = random.Random(seed)
    words = []
    for rank, w in enumerate(rnd.sample(POOL, len(POOL))):
        words += [w if rnd.random() < 0.7 else w.upper()] * (60 - rank * 3)  # strictly decreasing counts: the top-5 is unambiguous
    rnd.shuffle(words)
    text = ' '.join(words + ['x', '7', 'a1'])
    out.mkdir(parents=True, exist_ok=True)
    p = out / name
    p.write_text(text, encoding='utf-8')
    return p


def expected(path: Path, top: int = 5) -> dict:
    ws = re.findall(r'[^\W\d_]{2,}', path.read_text(encoding='utf-8').casefold())
    f = Counter(ws)
    return {'woerter': len(ws), 'verschieden': len(f), 'haeufigste': [[w, n] for w, n in f.most_common(top)]}


def visible(out: Path):
    make(out, 1)
