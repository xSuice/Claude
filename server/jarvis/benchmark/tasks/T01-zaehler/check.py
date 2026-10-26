"""T01 check: python3 check.py RESULT_DIR"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Check, guard  # noqa: E402
import gen  # noqa: E402


def read_tage(p: Path) -> dict:
    lines = p.read_text(encoding='utf-8').strip().splitlines()
    assert lines[0].strip() == 'datum;kwh', f'Kopfzeile {lines[0]!r}'
    out = {}
    for line in lines[1:]:
        d, v = line.strip().split(';')
        assert len(v.split('.')[-1]) == 3 and ',' not in v, f'Format {v!r}'
        out[d] = float(v)
    return out


def compare(c: Check, cid: str, fixture: Path):
    exp = gen.expected(fixture)
    code, out = c.run(['python3', 'verbrauch.py', fixture.name, '--out', f'{cid}-tage.csv', '--anomalien', f'{cid}-anom.txt'])
    if not c.ok(f'{cid}-laeuft', code == 0, out[-300:]):
        return
    got = read_tage(c.file(f'{cid}-tage.csv'))
    bad = {d: (got.get(d), v) for d, v in exp['daily'].items() if got.get(d) is None or abs(got[d] - v) > 0.0015}
    c.ok(f'{cid}-tage', not bad and set(got) == set(exp['daily']), f'abweichend: {bad}' if bad else f'{len(got)} Tage')
    anom = [x.strip() for x in c.file(f'{cid}-anom.txt').read_text(encoding='utf-8').splitlines() if x.strip()]
    c.ok(f'{cid}-anomalien', anom == exp['anomalies'], f'erwartet {exp["anomalies"]}, erhalten {anom}')


def main():
    c = Check('T01', sys.argv[1])
    for f in ('verbrauch.py', 'test_verbrauch.py', 'README.md', 'tage.csv', 'anomalien.txt'):
        c.ok(f'datei:{f}', c.file(f).is_file())
    if c.file('verbrauch.py').is_file():
        code, out = c.run(['python3', '-m', 'unittest', 'discover', '-p', 'test_*.py'], timeout=180)
        c.ok('eigene-tests', code == 0 and 'Ran 0 tests' not in out, out[-300:])
        gen.make(c.work, 1, 'spring', 'sichtbar.csv')
        guard(c, 'sichtbar', lambda: compare(c, 'sichtbar', c.file('sichtbar.csv')))
        gen.make(c.work, 101, 'spring', 'verdeckt_a.csv')
        guard(c, 'verdeckt_a', lambda: compare(c, 'verdeckt_a', c.file('verdeckt_a.csv')))
        gen.make(c.work, 202, 'autumn', 'verdeckt_b.csv')
        guard(c, 'verdeckt_b', lambda: compare(c, 'verdeckt_b', c.file('verdeckt_b.csv')))
    readme = c.file('README.md')
    c.ok('readme-aufruf', readme.is_file() and 'verbrauch.py' in readme.read_text(encoding='utf-8', errors='replace'))
    c.done()


if __name__ == '__main__':
    main()
