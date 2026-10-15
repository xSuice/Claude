"""Selbstprüfung der Benchmark-Prüfungen: Referenzlösung muss vollständig bestehen, ein leerer Ordner darf es nie.
Aufruf: python3 selfcheck.py [TASK-ID ...]   (ohne Argument: alle Aufgaben mit refs/<ID>/). Keine Claude-Aufrufe."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run_check(task_dir: Path, result: Path) -> dict:
    p = subprocess.run([sys.executable, str(task_dir / 'check.py'), str(result)], capture_output=True, text=True, timeout=900)
    try:
        return json.loads(p.stdout)
    except ValueError:
        return {'complete': False, 'passed': 0, 'total': 0, 'criteria': [{'id': 'check-absturz', 'ok': False, 'detail': (p.stdout + p.stderr)[-500:]}]}


def main() -> int:
    ids = sys.argv[1:] or sorted(d.name.split('-')[0] for d in (HERE / 'refs').iterdir() if d.is_dir())
    bad = 0
    for tid in ids:
        task_dir = next(HERE.glob(f'tasks/{tid}-*'))
        tmp = Path(tempfile.mkdtemp(prefix=f'selfcheck-{tid}-'))
        try:
            ref = tmp / 'ref'
            shutil.copytree(HERE / 'refs' / tid, ref)
            sys.path.insert(0, str(task_dir))
            import importlib
            gen = importlib.import_module('gen')
            gen.visible(ref)
            sys.path.pop(0); sys.modules.pop('gen', None)
            if (ref / '_final.sh').is_file():
                subprocess.run(['bash', '_final.sh'], cwd=ref, check=True, capture_output=True, timeout=300)
            good = run_check(task_dir, ref)
            empty = tmp / 'leer'; empty.mkdir()
            nothing = run_check(task_dir, empty)
            ok = good.get('complete') is True and nothing.get('complete') is False
            bad += not ok
            fails = [c['id'] + ': ' + c['detail'][:120] for c in good.get('criteria', []) if not c['ok']]
            print(f'{tid}: Referenz {good.get("passed")}/{good.get("total")}, leer {nothing.get("passed")}/{nothing.get("total")} -> {"OK" if ok else "FEHLER"}', *fails, sep='\n  ' if fails else '')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
