"""T11 check: python3 check.py RESULT_DIR"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Check, guard  # noqa: E402
import gen  # noqa: E402


def docx_lines(path: Path):
    from docx import Document
    d = Document(str(path))
    return [p.text.strip() for p in d.paragraphs if p.style.name in ('Heading 1', 'Überschrift 1')], \
           [p.text.strip() for p in d.paragraphs if p.text.strip() and not p.style.name.startswith(('Heading', 'Überschrift', 'Title'))]


def close(a: dict, b: dict) -> bool:
    return all(set(a.get(k, {})) == {'anzahl', 'min', 'max', 'mittel'} and a[k]['anzahl'] == b[k]['anzahl']
               and all(abs(a[k][x] - b[k][x]) < 0.0051 for x in ('min', 'max', 'mittel')) for k in b)


def compare(c: Check, cid: str, fixture: Path):
    code, out = c.run(['python3', 'auswertung.py', fixture.name, '--json', f'{cid}.json', '--docx', f'{cid}.docx'])
    if not c.ok(f'{cid}-laeuft', code == 0, out[-300:]):
        return
    exp = gen.expected(fixture)
    got = json.loads(c.file(f'{cid}.json').read_text(encoding='utf-8'))
    c.ok(f'{cid}-json', close(got, exp), f'erwartet {exp}, erhalten {got}')
    heads, paras = docx_lines(c.file(f'{cid}.docx'))
    c.ok(f'{cid}-titel', heads[:1] == ['Messbericht'], str(heads))
    c.ok(f'{cid}-absaetze', paras == [gen.line(k, exp[k]) for k in ('temperatur', 'feuchte')], str(paras)[:300])


def main():
    c = Check('T11', sys.argv[1])
    for f in ('auswertung.py', 'test_auswertung.py', 'README.md', 'statistik.json', 'bericht.docx'):
        c.ok(f'datei:{f}', c.file(f).is_file())
    if c.file('auswertung.py').is_file():
        code, out = c.run(['python3', '-m', 'unittest', 'discover', '-p', 'test_*.py'], timeout=180)
        c.ok('eigene-tests', code == 0 and 'Ran 0 tests' not in out, out[-300:])
        gen.make(c.work, 1, 'sichtbar.csv')
        guard(c, 'sichtbar', lambda: compare(c, 'sichtbar', c.file('sichtbar.csv')))
        for n, seed in (('a', 101), ('b', 202)):
            gen.make(c.work, seed, f'verdeckt_{n}.csv')
            guard(c, f'verdeckt_{n}', lambda n=n: compare(c, f'verdeckt_{n}', c.file(f'verdeckt_{n}.csv')))
    if c.file('statistik.json').is_file() and c.file('bericht.docx').is_file() and c.file('messdaten.csv').is_file():
        def abgabe():
            exp = gen.expected(c.file('messdaten.csv'))
            c.ok('abgabe-json', close(json.loads(c.file('statistik.json').read_text(encoding='utf-8')), exp))
            c.ok('abgabe-docx-passt-zu-json', docx_lines(c.file('bericht.docx'))[1] == [gen.line(k, exp[k]) for k in ('temperatur', 'feuchte')])
        guard(c, 'abgabe', abgabe)
    c.ok('readme-aufruf', c.file('README.md').is_file() and 'auswertung.py' in c.file('README.md').read_text(encoding='utf-8', errors='replace'))
    c.done()


if __name__ == '__main__':
    main()
