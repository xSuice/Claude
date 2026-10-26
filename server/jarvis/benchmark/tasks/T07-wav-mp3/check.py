"""T07 check: python3 check.py RESULT_DIR"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Check, guard  # noqa: E402
import gen  # noqa: E402


def probe(path: Path) -> tuple[str, float]:
    o = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=format_name,duration', '-of', 'default=nw=1', str(path)],
                       capture_output=True, text=True, timeout=60).stdout
    return (re.search(r'format_name=(\S+)', o) or [0, ''])[1], float((re.search(r'duration=([\d.]+)', o) or [0, 0])[1])


def compare(c: Check, cid: str, wav: Path):
    code, out = c.run(['python3', 'wav2mp3.py', wav.name, '--out', f'{cid}.mp3'])
    if not c.ok(f'{cid}-laeuft', code == 0, out[-300:]):
        return
    fmt, dur = probe(c.file(f'{cid}.mp3'))
    true = gen.duration(wav)
    c.ok(f'{cid}-format', 'mp3' in fmt, fmt)
    c.ok(f'{cid}-dauer-datei', abs(dur - true) <= 0.1, f'mp3 {dur:.2f} s, wav {true:.2f} s')
    m = re.search(r'Dauer: (\d+\.\d)$', out.strip().splitlines()[-1] if out.strip() else '')
    c.ok(f'{cid}-dauer-ausgabe', bool(m) and abs(float(m.group(1)) - dur) <= 0.1, out.strip()[-80:])


def main():
    c = Check('T07', sys.argv[1])
    for f in ('wav2mp3.py', 'test_wav2mp3.py', 'README.md', 'ton.mp3'):
        c.ok(f'datei:{f}', c.file(f).is_file())
    if c.file('wav2mp3.py').is_file():
        code, out = c.run(['python3', '-m', 'unittest', 'discover', '-p', 'test_*.py'], timeout=180)
        c.ok('eigene-tests', code == 0 and 'Ran 0 tests' not in out, out[-300:])
        for n, seed in (('s', 1), ('a', 101), ('b', 202)):
            gen.make(c.work, seed, f'{n}.wav')
            guard(c, n, lambda n=n: compare(c, n, c.file(f'{n}.wav')))
        code, out = c.run(['python3', 'wav2mp3.py', 'gibt-es-nicht.wav', '--out', 'x.mp3'])
        c.ok('fehlende-datei-exit2', code == 2 and not c.file('x.mp3').exists(), f'Exit {code}')
    c.ok('readme-aufruf', c.file('README.md').is_file() and 'wav2mp3.py' in c.file('README.md').read_text(encoding='utf-8', errors='replace'))
    c.done()


if __name__ == '__main__':
    main()
