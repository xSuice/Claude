"""T06 generator: orders. expected() is the reference result as a Python list."""
import json
import random
from pathlib import Path

KUNDEN = ['Adler', 'Becker', 'Chen', 'Dietz', 'Esser', 'Fuchs', 'Graf']


def make(out: Path, seed: int, name: str = 'bestellungen.json') -> Path:
    rnd = random.Random(seed)
    orders = [{'id': i, 'kunde': rnd.choice(KUNDEN), 'status': rnd.choice(['offen', 'bezahlt', 'bezahlt', 'storniert']),
               'positionen': [{'menge': rnd.randrange(1, 9), 'preis': round(rnd.uniform(0.5, 120), 2)} for _ in range(rnd.randrange(1, 5))]}
              for i in range(1, rnd.randrange(15, 30))]
    out.mkdir(parents=True, exist_ok=True)
    p = out / name
    p.write_text(json.dumps(orders, indent=1), encoding='utf-8')
    return p


def expected(path: Path) -> list[dict]:
    agg = {}
    for o in json.loads(path.read_text(encoding='utf-8')):
        if o['status'] == 'bezahlt':
            a = agg.setdefault(o['kunde'], [0, 0.0])
            a[0] += 1
            a[1] += sum(p['menge'] * p['preis'] for p in o['positionen'])
    rows = [{'kunde': k, 'bestellungen': n, 'umsatz': round(u, 2)} for k, (n, u) in agg.items()]
    return sorted(rows, key=lambda r: (-r['umsatz'], r['kunde']))


def visible(out: Path):
    make(out, 1)
