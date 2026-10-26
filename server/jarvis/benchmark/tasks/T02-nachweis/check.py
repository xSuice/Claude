"""T02 check: python3 check.py RESULT_DIR"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Check, guard  # noqa: E402
import gen  # noqa: E402


def render(exp: list[dict]) -> str:
    out = ['# Ausbildungsnachweis', '']
    for w in exp:
        out += [f'## {w["kw"]}', '', '| Datum | Bereich | Tätigkeit | Stunden |', '|---|---|---|---|']
        out += [f'| {a} | {b} | {c} | {d} |' for a, b, c, d in w['rows']]
        out += ['', f'**Summe: {w["summe"]} Stunden**', '']
    return '\n'.join(out)


def norm(t: str) -> list[str]:
    return [ln.rstrip() for ln in t.strip().splitlines() if ln.strip()]


def compare(c: Check, cid: str, fixture: Path):
    code, out = c.run(['python3', 'nachweis.py', fixture.name, '--out', f'{cid}.md'])
    if not c.ok(f'{cid}-laeuft', code == 0, out[-300:]):
        return
    got, want = norm(c.file(f'{cid}.md').read_text(encoding='utf-8')), norm(render(gen.expected(fixture)))
    diff = next((f'Zeile {i}: erwartet {w!r}, erhalten {g!r}' for i, (w, g) in enumerate(zip(want, got)) if w != g), '')
    c.ok(f'{cid}-inhalt', got == want, diff or f'{len(got)} statt {len(want)} Zeilen')


def main():
    c = Check('T02', sys.argv[1])
    for f in ('nachweis.py', 'test_nachweis.py', 'README.md', 'nachweis.md'):
        c.ok(f'datei:{f}', c.file(f).is_file())
    if c.file('nachweis.py').is_file():
        code, out = c.run(['python3', '-m', 'unittest', 'discover', '-p', 'test_*.py'], timeout=180)
        c.ok('eigene-tests', code == 0 and 'Ran 0 tests' not in out, out[-300:])
        gen.make(c.work, 1, name='sichtbar.json')
        guard(c, 'sichtbar', lambda: compare(c, 'sichtbar', c.file('sichtbar.json')))
        for n, seed in (('a', 101), ('b', 202)):
            gen.make(c.work, seed, name=f'verdeckt_{n}.json')
            guard(c, f'verdeckt_{n}', lambda n=n: compare(c, f'verdeckt_{n}', c.file(f'verdeckt_{n}.json')))
    c.ok('readme-aufruf', c.file('README.md').is_file() and 'nachweis.py' in c.file('README.md').read_text(encoding='utf-8', errors='replace'))
    c.done()


if __name__ == '__main__':
    main()
