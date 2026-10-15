"""T02 generator: training diary entries (Ausbildungsnachweis) over three ISO weeks, unsorted JSON."""
import json
import random
from datetime import date, timedelta
from pathlib import Path

TAETIGKEITEN = {
    'Betrieb': ['Fehleranalyse im Ticketsystem', 'REST-Schnittstelle erweitert', 'Code-Review mit Ausbilder',
                'Datenbankabfragen optimiert', 'Unit-Tests für Rechnungsmodul', 'Deployment auf Testserver begleitet',
                'Dokumentation der API ergänzt', 'Backup-Konzept geprüft'],
    'Berufsschule': ['LF 5: Datenbankmodellierung', 'LF 6: Serviceanfragen', 'Wirtschafts- und Sozialkunde',
                     'LF 8: Daten systemübergreifend bereitstellen', 'Englisch: technische Dokumentation'],
}


def make(out: Path, seed: int, start: date | None = None, name: str = 'berichtsheft.json') -> Path:
    rnd = random.Random(seed)
    start = start or date(2026, 9, 28) + timedelta(weeks=rnd.randrange(0, 6))
    start -= timedelta(days=start.weekday())
    entries = []
    for w in range(3):
        school = rnd.sample(range(5), 1 if w != 1 else 2)
        for d in range(5):
            day = start + timedelta(weeks=w, days=d)
            if rnd.random() < 0.08:
                continue  # Urlaub/krank: no entry
            area = 'Berufsschule' if d in school else 'Betrieb'
            parts = 2 if area == 'Betrieb' and rnd.random() < 0.35 else 1
            hours = [6.0, 8.0][area == 'Betrieb']
            split = [hours] if parts == 1 else [rnd.choice([2.5, 3.0, 4.5]), None]
            if parts == 2:
                split[1] = hours - split[0]
            for h in split:
                entries.append({'datum': day.isoformat(), 'bereich': area, 'taetigkeit': rnd.choice(TAETIGKEITEN[area]),
                                'stunden': h})
    order = list(range(len(entries)))
    rnd.shuffle(order)
    data = {'auszubildende': 'Philipp Muster', 'ausbildungsjahr': 2, 'eintraege': [dict(entries[i], nr=i + 1) for i in order]}
    out.mkdir(parents=True, exist_ok=True)
    p = out / name
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    return p


def expected(path: Path) -> list[dict]:
    """[{'kw': 'KW 05/2027', 'rows': [(TT.MM.JJJJ, bereich, taetigkeit, '7,5'), ...], 'summe': '40,0'}] in week order."""
    data = json.loads(path.read_text(encoding='utf-8'))
    es = sorted(data['eintraege'], key=lambda e: (e['datum'], e['nr']))
    weeks = {}
    for e in es:
        d = date.fromisoformat(e['datum'])
        y, w, _ = d.isocalendar()
        weeks.setdefault((y, w), []).append(e)
    out = []
    for (y, w), rows in sorted(weeks.items()):
        out.append({'kw': f'KW {w:02d}/{y}',
                    'rows': [(date.fromisoformat(e['datum']).strftime('%d.%m.%Y'), e['bereich'], e['taetigkeit'],
                              f"{e['stunden']:.1f}".replace('.', ',')) for e in rows],
                    'summe': f"{sum(e['stunden'] for e in rows):.1f}".replace('.', ',')})
    return out


def visible(out: Path):
    make(out, 1)


if __name__ == '__main__':
    import sys
    visible(Path(sys.argv[1]))
