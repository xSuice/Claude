"""T06 check: python3 check.py RESULT_DIR"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Check, guard  # noqa: E402
import gen  # noqa: E402


def same(got, want) -> bool:
    return (len(got) == len(want) and all(list(g) == ['kunde', 'bestellungen', 'umsatz'] and g['kunde'] == w['kunde']
            and g['bestellungen'] == w['bestellungen'] and isinstance(g['umsatz'], (int, float)) and abs(g['umsatz'] - w['umsatz']) < 0.0051
            for g, w in zip(got, want)))


def compare(c: Check, cid: str, fixture: Path):
    code, out = c.run(['jq', '-f', 'auswertung.jq', fixture.name])
    if not c.ok(f'{cid}-laeuft', code == 0, out[-300:]):
        return
    got, want = json.loads(out), gen.expected(fixture)
    c.ok(f'{cid}-inhalt', same(got, want), f'erwartet {want[:2]}..., erhalten {got[:2]}...')


def main():
    c = Check('T06', sys.argv[1])
    for f in ('auswertung.jq', 'pruefen.sh', 'README.md', 'ergebnis.json'):
        c.ok(f'datei:{f}', c.file(f).is_file())
    if c.file('auswertung.jq').is_file():
        gen.make(c.work, 1, 'sichtbar.json')
        guard(c, 'sichtbar', lambda: compare(c, 'sichtbar', c.file('sichtbar.json')))
        for n, seed in (('a', 101), ('b', 202), ('c', 303)):
            gen.make(c.work, seed, f'verdeckt_{n}.json')
            guard(c, f'verdeckt_{n}', lambda n=n: compare(c, f'verdeckt_{n}', c.file(f'verdeckt_{n}.json')))
        (c.work / 'leer.json').write_text('[]', encoding='utf-8')
        code, out = c.run(['jq', '-f', 'auswertung.jq', 'leer.json'])
        c.ok('leere-liste', code == 0 and json.loads(out or 'null') == [], out[-100:])
    if c.file('ergebnis.json').is_file():
        guard(c, 'abgabe', lambda: c.ok('abgabe-sichtbar', same(json.loads(c.file('ergebnis.json').read_text(encoding='utf-8')), gen.expected(c.file('bestellungen.json'))) if c.file('bestellungen.json').is_file() else False, 'ergebnis.json passt nicht zu bestellungen.json'))
    c.ok('readme-aufruf', c.file('README.md').is_file() and 'auswertung.jq' in c.file('README.md').read_text(encoding='utf-8', errors='replace'))
    c.done()


if __name__ == '__main__':
    main()
