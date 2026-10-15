"""T09 check: python3 check.py RESULT_DIR
Prüft nur die Ergebnisse. Ob das Werkzeug tool.wortstatistik benutzt wurde, belegt das JARVIS-Protokoll (Fähigkeiten-Nutzung), nicht diese Prüfung."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Check, guard  # noqa: E402
import gen  # noqa: E402


def render(d: dict) -> str:
    out = ['# Wortstatistik', '', f'Wörter gesamt: {d["woerter"]}', f'Verschiedene Wörter: {d["verschieden"]}', '', '| Rang | Wort | Anzahl |', '|---|---|---|']
    return '\n'.join(out + [f'| {i} | {w} | {n} |' for i, (w, n) in enumerate(d['haeufigste'], start=1)])


def norm(t: str) -> list[str]:
    return [ln.rstrip() for ln in t.strip().splitlines()]


def main():
    c = Check('T09', sys.argv[1])
    for f in ('statistik.json', 'statistik.md', 'bericht.py', 'test_bericht.py', 'README.md', 'text.txt'):
        c.ok(f'datei:{f}', c.file(f).is_file())
    if c.file('statistik.json').is_file() and c.file('text.txt').is_file():
        def sichtbar():
            got = json.loads(c.file('statistik.json').read_text(encoding='utf-8'))
            c.ok('statistik-zahlen', got == gen.expected(c.file('text.txt')), f'{str(got)[:200]}')
        guard(c, 'statistik-zahlen', sichtbar)
    if c.file('bericht.py').is_file():
        code, out = c.run(['python3', '-m', 'unittest', 'discover', '-p', 'test_*.py'], timeout=180)
        c.ok('eigene-tests', code == 0 and 'Ran 0 tests' not in out, out[-300:])
        for n, seed in (('a', 101), ('b', 202), ('c', 303)):
            def one(n=n, seed=seed):
                p = gen.make(c.work, seed, f'v_{n}.txt')
                d = gen.expected(p)
                (c.work / f'v_{n}.json').write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
                code, out = c.run(['python3', 'bericht.py', f'v_{n}.json', '--out', f'v_{n}.md'])
                if c.ok(f'verdeckt_{n}-laeuft', code == 0, out[-300:]):
                    c.ok(f'verdeckt_{n}-inhalt', norm(c.file(f'v_{n}.md').read_text(encoding='utf-8')) == norm(render(d)), 'Markdown weicht ab')
            guard(c, f'verdeckt_{n}', one)
        if c.file('statistik.json').is_file():
            guard(c, 'abgabe-md', lambda: c.ok('abgabe-md', norm(c.file('statistik.md').read_text(encoding='utf-8')) == norm(render(json.loads(c.file('statistik.json').read_text(encoding='utf-8')))), 'statistik.md passt nicht zu statistik.json'))
    c.ok('readme-aufruf', c.file('README.md').is_file() and 'bericht.py' in c.file('README.md').read_text(encoding='utf-8', errors='replace'))
    c.done()


if __name__ == '__main__':
    main()
