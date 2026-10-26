"""T08 check (held-out): python3 check.py RESULT_DIR"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Check, guard  # noqa: E402
import gen  # noqa: E402


def compare(c: Check, cid: str, imgdir: Path):
    from PIL import Image
    code, out = c.run(['python3', 'kontakt.py', imgdir.name, '--out', f'{cid}-sheet.png', '--thumbs', f'{cid}-thumbs'])
    if not c.ok(f'{cid}-laeuft', code == 0, out[-300:]):
        return
    exp = gen.expected(imgdir)
    got = {p.name: Image.open(p).size for p in c.file(f'{cid}-thumbs').glob('*.png')}
    c.ok(f'{cid}-thumbs', got == exp['thumbs'], f'erwartet {exp["thumbs"]}, erhalten {got}')
    sheet = Image.open(c.file(f'{cid}-sheet.png')).convert('RGB')
    c.ok(f'{cid}-masse', sheet.size == exp['sheet'], f'{sheet.size} statt {exp["sheet"]}')
    if sheet.size != exp['sheet']:
        return
    bad = []
    for i, n in enumerate(exp['names']):
        x, y = 10 + (i % 3) * 210, 10 + (i // 3) * 210
        if sheet.getpixel((x + 2, y + 2)) != exp['colors'][n]:
            bad.append(n)
        # outside the thumbnail inside the cell stays white
        tw, th = exp['thumbs'][n]
        if th < 198 and sheet.getpixel((x + 2, y + th + 2)) != (255, 255, 255):
            bad.append(n + '(Hintergrund)')
    c.ok(f'{cid}-raster', not bad, f'falsch: {bad}')
    c.ok(f'{cid}-rand', sheet.getpixel((2, 2)) == (255, 255, 255) and sheet.getpixel((sheet.size[0] - 3, sheet.size[1] - 3)) == (255, 255, 255))


def main():
    c = Check('T08', sys.argv[1])
    for f in ('kontakt.py', 'test_kontakt.py', 'README.md', 'kontaktbogen.png'):
        c.ok(f'datei:{f}', c.file(f).is_file())
    c.ok('datei:thumbs', c.file('thumbs').is_dir() and any(c.file('thumbs').glob('*.png')))
    if c.file('kontakt.py').is_file():
        code, out = c.run(['python3', '-m', 'unittest', 'discover', '-p', 'test_*.py'], timeout=180)
        c.ok('eigene-tests', code == 0 and 'Ran 0 tests' not in out, out[-300:])
        for n, seed in (('s', 1), ('a', 101), ('b', 202)):
            d = gen.make(c.work, seed, f'bilder_{n}')
            guard(c, n, lambda n=n, d=d: compare(c, n, d))
        (c.work / 'leer').mkdir()
        code, out = c.run(['python3', 'kontakt.py', 'leer', '--out', 'leer.png', '--thumbs', 'leer-thumbs'])
        c.ok('ohne-bilder-exit4', code == 4 and not c.file('leer.png').exists(), f'Exit {code}')
    c.ok('readme-aufruf', c.file('README.md').is_file() and 'kontakt.py' in c.file('README.md').read_text(encoding='utf-8', errors='replace'))
    c.done()


if __name__ == '__main__':
    main()
