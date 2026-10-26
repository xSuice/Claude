"""T11 generator: sensor readings with a few empty cells."""
import random
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path


def make(out: Path, seed: int, name: str = 'messdaten.csv') -> Path:
    rnd = random.Random(seed)
    n = rnd.randrange(40, 100)
    rows = []
    for i in range(n):
        t = '' if rnd.random() < 0.05 else f'{rnd.uniform(15, 30):.2f}'
        f = '' if rnd.random() < 0.05 else f'{rnd.uniform(30, 80):.1f}'
        rows.append(f'2026-10-01T{i // 4:02d}:{(i % 4) * 15:02d};{t};{f}')
    out.mkdir(parents=True, exist_ok=True)
    p = out / name
    p.write_text('zeit;temperatur;feuchte\n' + '\n'.join(rows) + '\n', encoding='utf-8')
    return p


def r2(x: Decimal) -> Decimal:
    return x.quantize(Decimal('0.01'), ROUND_HALF_UP)


def expected(path: Path) -> dict:
    cols = {'temperatur': [], 'feuchte': []}
    for line in path.read_text(encoding='utf-8').splitlines()[1:]:
        _, t, f = line.split(';')
        if t: cols['temperatur'].append(Decimal(t))
        if f: cols['feuchte'].append(Decimal(f))
    return {k: {'anzahl': len(v), 'min': float(r2(min(v))), 'max': float(r2(max(v))), 'mittel': float(r2(sum(v) / len(v)))} for k, v in cols.items()}


def line(name: str, s: dict) -> str:
    k = lambda x: f'{x:.2f}'.replace('.', ',')
    return f'{name.capitalize()}: Anzahl {s["anzahl"]}, Minimum {k(s["min"])}, Maximum {k(s["max"])}, Mittelwert {k(s["mittel"])}'


def visible(out: Path):
    make(out, 1)
