"""T04 check: python3 check.py RESULT_DIR"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Check, guard  # noqa: E402
import gen  # noqa: E402


def inspect(path: Path):
    from docx import Document
    d = Document(str(path))
    heads = [p.text for p in d.paragraphs if p.style.name in ('Heading 1', 'Überschrift 1')]
    tables = [[[c.text.strip() for c in r.cells] for r in t.rows] for t in d.tables]
    return heads, tables


def compare(c: Check, cid: str, fixture: Path):
    code, out = c.run(['python3', 'bericht.py', fixture.name, '--out', f'{cid}.docx'])
    if not c.ok(f'{cid}-laeuft', code == 0, out[-300:]):
        return
    heads, tables = inspect(c.file(f'{cid}.docx'))
    c.ok(f'{cid}-titel', heads[:1] == ['Umsatzbericht'], f'Überschriften {heads}')
    c.ok(f'{cid}-tabelle', len(tables) == 1 and tables[0] == gen.expected(fixture),
         f'erhalten {tables[0] if tables else None}')


def main():
    c = Check('T04', sys.argv[1])
    for f in ('bericht.py', 'test_bericht.py', 'README.md', 'umsatz.docx'):
        c.ok(f'datei:{f}', c.file(f).is_file())
    if c.file('bericht.py').is_file():
        code, out = c.run(['python3', '-m', 'unittest', 'discover', '-p', 'test_*.py'], timeout=180)
        c.ok('eigene-tests', code == 0 and 'Ran 0 tests' not in out, out[-300:])
        gen.make(c.work, 1, 'sichtbar.csv')
        guard(c, 'sichtbar', lambda: compare(c, 'sichtbar', c.file('sichtbar.csv')))
        for n, seed in (('a', 101), ('b', 202)):
            gen.make(c.work, seed, f'verdeckt_{n}.csv')
            guard(c, f'verdeckt_{n}', lambda n=n: compare(c, f'verdeckt_{n}', c.file(f'verdeckt_{n}.csv')))
    if c.file('umsatz.docx').is_file():
        guard(c, 'abgabe-oeffnet', lambda: c.ok('abgabe-oeffnet', bool(inspect(c.file('umsatz.docx'))[1]), 'Tabelle fehlt'))
    c.ok('readme-aufruf', c.file('README.md').is_file() and 'bericht.py' in c.file('README.md').read_text(encoding='utf-8', errors='replace'))
    c.done()


if __name__ == '__main__':
    main()
