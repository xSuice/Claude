"""T01 generator: hourly electricity meter readings around a DST change, German CSV, with duplicates, gaps,
unsorted lines and implausible (decreasing) readings. expected() is the reference interpretation of the task text."""
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Berlin')
DST_DAYS = {'spring': date(2026, 3, 29), 'autumn': date(2026, 10, 25)}


def make(out: Path, seed: int, season: str = 'spring', name: str = 'zaehler.csv') -> Path:
    rnd = random.Random(seed)
    d0 = DST_DAYS[season] - timedelta(days=2)
    t = datetime(d0.year, d0.month, d0.day, tzinfo=TZ).astimezone(timezone.utc)
    end = datetime.combine(d0 + timedelta(days=5), datetime.min.time(), TZ).astimezone(timezone.utc)
    stand = 10000 + rnd.uniform(0, 5000)
    rows = []
    while t < end:
        stand += rnd.uniform(0.1, 2.5)
        rows.append((t.astimezone(TZ), round(stand, 3)))
        t += timedelta(hours=1)
    # gaps (never the first row)
    rows = [rows[0]] + [r for r in rows[1:] if rnd.random() > 0.06]
    # implausible readings: lower than the previous true reading
    for i in rnd.sample(range(5, len(rows) - 1), 2):
        rows[i] = (rows[i][0], round(rows[i - 1][1] - rnd.uniform(5, 50), 3))
    lines = [f"{z.isoformat(timespec='minutes')};{f'{s:.3f}'.replace('.', ',')}" for z, s in rows]
    for i in rnd.sample(range(len(lines)), 3):  # exact duplicates
        lines.insert(i, lines[i])
    for _ in range(4):  # a few lines out of order
        i = rnd.randrange(1, len(lines) - 2)
        lines[i], lines[i + 1] = lines[i + 1], lines[i]
    out.mkdir(parents=True, exist_ok=True)
    p = out / name
    p.write_text('zeit;stand_kwh\n' + '\n'.join(lines) + '\n', encoding='utf-8')
    return p


def expected(csv_path: Path) -> dict:
    rows = set()
    for line in csv_path.read_text(encoding='utf-8').splitlines()[1:]:
        if line.strip():
            z, s = line.split(';')
            rows.add((z, float(s.replace(',', '.'))))
    seq = sorted(rows, key=lambda r: datetime.fromisoformat(r[0]))
    last = None
    anomalies, first, lastd = [], {}, {}
    for z, s in seq:
        if last is not None and s < last:
            anomalies.append(z)
            continue
        last = s
        d = datetime.fromisoformat(z).astimezone(TZ).date().isoformat()
        first.setdefault(d, s)
        lastd[d] = s
    days = sorted(lastd)
    daily = {}
    for i, d in enumerate(days):
        daily[d] = round(lastd[d] - (lastd[days[i - 1]] if i else first[d]), 3)
    return {'daily': daily, 'anomalies': anomalies}


def visible(out: Path):
    make(out, 1, 'spring')


if __name__ == '__main__':
    import sys
    visible(Path(sys.argv[1]))
