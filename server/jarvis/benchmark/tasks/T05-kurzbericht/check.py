"""T05 check (held-out): python3 check.py RESULT_DIR"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Check, guard  # noqa: E402
import gen  # noqa: E402


def words(t: str) -> list[str]:
    return re.findall(r'\w+', t)


def inspect(c: Check, cid: str, pdf: Path, data: dict):
    from pypdf import PdfReader
    pages = [p.extract_text() or '' for p in PdfReader(str(pdf)).pages]
    n = len(data['abschnitte']) + 1
    c.ok(f'{cid}-seitenzahl', len(pages) == n, f'{len(pages)} Seiten, erwartet {n}')
    if len(pages) != n:
        return
    c.ok(f'{cid}-titelseite', data['titel'] in pages[0] and 'Kurzbericht' in pages[0] and not re.search(r'Seite \d', pages[0]), pages[0][:120])
    for i, s in enumerate(data['abschnitte'], start=2):
        t = pages[i - 1]
        c.ok(f'{cid}-abschnitt{i - 1}', t.strip().startswith(s['ueberschrift']) and all(w in words(t) for w in words(s['text'])[:15]), t[:120])
        c.ok(f'{cid}-fuss{i - 1}', f'Seite {i} von {n}' in t, t[-60:])


def compare(c: Check, cid: str, fixture: Path):
    code, out = c.run(['python3', 'kurzbericht.py', fixture.name, '--out', f'{cid}.pdf'])
    if c.ok(f'{cid}-laeuft', code == 0, out[-300:]):
        inspect(c, cid, c.file(f'{cid}.pdf'), json.loads(fixture.read_text(encoding='utf-8')))


def main():
    c = Check('T05', sys.argv[1])
    for f in ('kurzbericht.py', 'test_kurzbericht.py', 'README.md', 'kurzbericht.pdf'):
        c.ok(f'datei:{f}', c.file(f).is_file())
    if c.file('kurzbericht.py').is_file():
        code, out = c.run(['python3', '-m', 'unittest', 'discover', '-p', 'test_*.py'], timeout=180)
        c.ok('eigene-tests', code == 0 and 'Ran 0 tests' not in out, out[-300:])
        for n, seed in (('s', 1), ('a', 101), ('b', 202)):
            gen.make(c.work, seed, f'{n}.json')
            guard(c, f'{n}', lambda n=n: compare(c, n, c.file(f'{n}.json')))
    c.ok('readme-aufruf', c.file('README.md').is_file() and 'kurzbericht.py' in c.file('README.md').read_text(encoding='utf-8', errors='replace'))
    c.done()


if __name__ == '__main__':
    main()
