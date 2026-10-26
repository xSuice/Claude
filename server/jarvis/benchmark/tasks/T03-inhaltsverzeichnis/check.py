"""T03 check (held-out): python3 check.py RESULT_DIR"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Check, guard  # noqa: E402
import gen  # noqa: E402


def compare(c: Check, cid: str, fixture: Path):
    code, out = c.run(['python3', 'toc.py', fixture.name, '--out', f'{cid}.out.md'])
    if not c.ok(f'{cid}-laeuft', code == 0, out[-300:]):
        return
    got, want = c.file(f'{cid}.out.md').read_text(encoding='utf-8'), gen.expected(fixture)
    diff = next((f'Zeile {i}: erwartet {w!r}, erhalten {g!r}' for i, (w, g) in enumerate(zip(want.split('\n'), got.split('\n'))) if w != g), '')
    c.ok(f'{cid}-inhalt', got == want, diff or 'Länge weicht ab')


def main():
    c = Check('T03', sys.argv[1])
    for f in ('toc.py', 'test_toc.py', 'README.md', 'dokument_mit_toc.md'):
        c.ok(f'datei:{f}', c.file(f).is_file())
    if c.file('toc.py').is_file():
        code, out = c.run(['python3', '-m', 'unittest', 'discover', '-p', 'test_*.py'], timeout=180)
        c.ok('eigene-tests', code == 0 and 'Ran 0 tests' not in out, out[-300:])
        gen.make(c.work, 1, 'sichtbar.md')
        guard(c, 'sichtbar', lambda: compare(c, 'sichtbar', c.file('sichtbar.md')))
        for n, seed in (('a', 101), ('b', 202), ('c', 303)):
            gen.make(c.work, seed, f'verdeckt_{n}.md')
            guard(c, f'verdeckt_{n}', lambda n=n: compare(c, f'verdeckt_{n}', c.file(f'verdeckt_{n}.md')))
        (c.work / 'ohne.md').write_text('# Titel\n\nText\n', encoding='utf-8')
        code, out = c.run(['python3', 'toc.py', 'ohne.md', '--out', 'ohne.out.md'])
        c.ok('ohne-marker-exit3', code == 3, f'Exit {code}')
    c.ok('readme-aufruf', c.file('README.md').is_file() and 'toc.py' in c.file('README.md').read_text(encoding='utf-8', errors='replace'))
    c.done()


if __name__ == '__main__':
    main()
