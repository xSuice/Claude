"""T05 generator: report sections. Texts are short and use only plain words (no hyphenation traps)."""
import json
import random
from pathlib import Path

HEADS = ['Ausgangslage', 'Vorgehen', 'Ergebnisse', 'Risiken', 'Kosten', 'Zeitplan', 'Fazit', 'Anhang']
WORDS = 'der die das Server Dienst Aufgabe prüft läuft stabil schnell Messung Wert Ergebnis Plan Team Woche Test Datei'.split()


def make(out: Path, seed: int, name: str = 'abschnitte.json') -> Path:
    rnd = random.Random(seed)
    secs = [{'ueberschrift': h, 'text': ' '.join(rnd.choice(WORDS) for _ in range(rnd.randrange(25, 60))) + '.'}
            for h in rnd.sample(HEADS, rnd.randrange(3, 7))]
    out.mkdir(parents=True, exist_ok=True)
    p = out / name
    p.write_text(json.dumps({'titel': f'Bericht Nr. {seed}', 'abschnitte': secs}, ensure_ascii=False, indent=1), encoding='utf-8')
    return p


def visible(out: Path):
    make(out, 1)
