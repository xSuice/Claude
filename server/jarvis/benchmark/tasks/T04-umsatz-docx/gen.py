"""T04 generator: sales CSV (German decimal comma). expected() gives the table cells."""
import random
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

NAMES = ['Kabel', 'Schraube M4', 'Netzteil', 'Maus', 'Tastatur', 'Monitorarm', 'Hub', 'Adapter', 'Dock', 'Lüfter']


def make(out: Path, seed: int, name: str = 'verkauf.csv') -> Path:
    rnd = random.Random(seed)
    rows = [(n, rnd.randrange(1, 60), Decimal(rnd.randrange(50, 9999)) / 100) for n in rnd.sample(NAMES, rnd.randrange(4, 9))]
    out.mkdir(parents=True, exist_ok=True)
    p = out / name
    p.write_text('artikel;menge;preis\n' + '\n'.join(f'{n};{m};{str(pr).replace(".", ",")}' for n, m, pr in rows) + '\n', encoding='utf-8')
    return p


def eur(d: Decimal) -> str:
    return str(d.quantize(Decimal('0.01'), ROUND_HALF_UP)).replace('.', ',')


def expected(path: Path) -> list[list[str]]:
    table, total, qty = [['Artikel', 'Menge', 'Einzelpreis (EUR)', 'Summe (EUR)']], Decimal(0), 0
    for line in path.read_text(encoding='utf-8').splitlines()[1:]:
        a, m, p = line.split(';')
        s = Decimal(m) * Decimal(p.replace(',', '.'))
        total += s; qty += int(m)
        table.append([a, m, eur(Decimal(p.replace(',', '.'))), eur(s)])
    table.append(['Gesamt', str(qty), '', eur(total)])
    return table


def visible(out: Path):
    make(out, 1)
