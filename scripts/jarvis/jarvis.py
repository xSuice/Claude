#!/usr/bin/env python3
"""JARVIS V16 client (PC and server). Hands jobs to the JARVIS core on the MA-Server - it never does the work itself.

  python jarvis.py submit "Auftrag" [--file PFAD ...] [--model haiku|sonnet|opus] [--public] [--quality TEXT]
                                    [--deadline-min N] [--plan-approval] [--no-web]
  python jarvis.py status [JOB] | events JOB [--since N] | wait JOB [--minutes 9] | list | usage | caps | learned | doctor
  python jarvis.py result JOB [--fetch] [--to ORDNER]      (Standard-Ziel: Dokumente/JARVIS-Ergebnisse/<JOB>)
  python jarvis.py cancel JOB | approve JOB [--step S] [--answer TEXT] | forget template|lesson ID | flush
  python jarvis.py pc-report | pc-worker [--once]          (PC-Fähigkeiten; nur mit lokaler Freigabe)
  Global: --json (Rohdaten)

Transport: the existing SSH alias `ma-server` (BatchMode, no new ports). If the server is unreachable, `submit` stores the
job in a local outbox with its client id; the next command sends it. The server deduplicates by client id, so a job that
was sent twice runs once.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shlex
import subprocess
import sys
import tarfile
import time
import uuid
from pathlib import Path

HOST = os.environ.get('JARVIS_HOST', 'ma-server')
REMOTE_CLI = '~/.local/share/ma-jarvis/current/brain-runtime/jarvis_cli.py'
REMOTE_CFG = '~/.config/ma-jarvis/jarvis.json'
LOCAL_CFG = Path.home() / '.config' / 'ma-jarvis' / 'jarvis.json'
STATE = Path.home() / '.claude' / 'state'
OUTBOX = STATE / 'jarvis-outbox'
LAST = STATE / 'jarvis-last.json'
PC_ALLOW = STATE / 'jarvis-pc.json'
RESULTS = Path.home() / 'Documents' / 'JARVIS-Ergebnisse'
JOB_RE = re.compile(r'^j\d{8}-[0-9a-f]{6}$')
STATES = {'queued': 'wartet auf Planung', 'planning': 'wird geplant', 'running': 'läuft', 'waiting_approval': 'wartet auf deine Freigabe',
          'waiting_pc': 'wartet auf den PC-Worker', 'done': 'ERLEDIGT (alles geprüft)', 'partial': 'TEILERGEBNIS',
          'failed': 'NICHT ERREICHT', 'cancelled': 'abgebrochen'}


class Offline(RuntimeError):
    pass


def on_server() -> bool:
    return sys.platform.startswith('linux') and LOCAL_CFG.is_file()


def call(args: list[str], stdin: bytes = b'', binary: bool = False, timeout: int = 300):
    """Run the server CLI (locally on the server, else over SSH). Returns (exit, parsed JSON or bytes)."""
    if on_server():
        cmd = [sys.executable, str(Path(os.path.expanduser(REMOTE_CLI))), '--config', str(LOCAL_CFG), *args]
    else:
        remote = 'python3 %s --config %s %s' % (REMOTE_CLI, REMOTE_CFG, ' '.join(shlex.quote(a) for a in args))
        cmd = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=15', HOST, remote]
    try:
        p = subprocess.run(cmd, input=stdin, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Offline(f'Server nicht erreichbar ({type(e).__name__})') from e
    if p.returncode == 255 and not on_server():
        raise Offline('SSH-Verbindung fehlgeschlagen: ' + p.stderr.decode('utf-8', 'replace').strip()[-200:])
    if binary and p.returncode == 0:
        return 0, p.stdout
    text = p.stdout.decode('utf-8', 'replace').strip().splitlines()
    try:
        return p.returncode, json.loads(text[-1]) if text else {'error': p.stderr.decode('utf-8', 'replace')[-400:]}
    except ValueError:
        return p.returncode, {'error': (p.stdout + p.stderr).decode('utf-8', 'replace')[-400:]}


def remember(job: str) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    LAST.write_text(json.dumps({'job': job, 'ts': int(time.time())}), encoding='utf-8')


def last_job() -> str | None:
    try:
        return json.loads(LAST.read_text(encoding='utf-8'))['job']
    except (OSError, ValueError, KeyError):
        return None


def job_arg(j: str | None) -> str:
    j = j or last_job()
    if not j or not JOB_RE.match(j):
        sys.exit('Keine gültige Job-ID (Format j20261014-abc123).')
    return j


def inputs_tar(paths: list[str]) -> bytes:
    if not paths:
        return b''
    buf = io.BytesIO()
    total = 0
    with tarfile.open(fileobj=buf, mode='w:gz') as tf:
        for p in paths:
            src = Path(p).expanduser().resolve(strict=True)
            items = [src] if src.is_file() else [x for x in src.rglob('*') if x.is_file()]
            for f in items:
                if f.is_symlink():
                    continue
                total += f.stat().st_size
                if total > 150_000_000:
                    sys.exit('Eingabedateien zusammen größer als 150 MB - bitte verkleinern.')
                arc = f.name if src.is_file() else str(Path(src.name) / f.relative_to(src)).replace('\\', '/')
                tf.add(str(f), arcname=arc, recursive=False)
    return buf.getvalue()


def send(entry: dict) -> tuple[int, dict]:
    head = json.dumps({'request': entry['request'], 'client_id': entry['client_id'], 'options': entry['options']}).encode() + b'\n'
    return call(['submit'], head + inputs_tar(entry.get('files') or []), timeout=600)


def flush(quiet: bool = True) -> list[dict]:
    done = []
    if not OUTBOX.is_dir():
        return done
    for f in sorted(OUTBOX.glob('*.json')):
        entry = json.loads(f.read_text(encoding='utf-8'))
        try:
            code, r = send(entry)
        except Offline:
            break
        if code == 0:
            f.unlink()
            remember(r['job_id'])
            done.append(r)
            if not quiet:
                print(f'Aus der Warteschlange gesendet: {r["job_id"]} ({"Duplikat" if r.get("duplicate") else "neu"})')
        else:
            bad = OUTBOX / 'abgelehnt'
            bad.mkdir(exist_ok=True)
            f.rename(bad / f.name)
            print(f'Warteschlange: Auftrag abgelehnt ({r.get("error")}) -> {bad / f.name}')
    return done


def fmt_status(s: dict) -> str:
    lines = [f'JARVIS {s["id"]}: {STATES.get(s["state"], s["state"])}']
    if s.get('goal'):
        lines.append(f'Ziel: {s["goal"]}')
    if s.get('summary'):
        lines.append(f'Ergebnis: {s["summary"]}')
    lines.append(f'Datenklasse {s["data_class"]}, Plan: {s.get("plan_source") or "-"}, Typ: {s.get("task_type") or "-"}')
    for st in s.get('steps', []):
        cap = f' [{st["capability"]}]' if st.get('capability') else ''
        lines.append(f'  {st["sid"]} {st["kind"]:6} {st["state"]:8} {st["title"]}{cap}')
    b = s['budget']
    lines.append(f'Verbrauch: {s["claude_calls"]}/{b["claude_calls"]} Claude-Aufrufe, {s["tokens_new"]} neue Token '
                 f'(+{s["tokens_cache"]} Cache), Listenpreis-Äquivalent {round(s["list_usd"], 3)} USD (keine Rechnung), '
                 f'{s["local_runs"]} lokale Läufe, {s["fix_rounds"]} Korrekturrunden, {s["deferrals"]} Wartephasen')
    if s['state'] in ('done', 'partial', 'failed'):
        lines.append(f'Abholen: python {Path(__file__).as_posix()} result {s["id"]} --fetch')
    if s['state'] == 'waiting_approval':
        lines.append(f'Freigeben: python {Path(__file__).as_posix()} approve {s["id"]} [--step sN --answer "..."]')
    return '\n'.join(lines)


# ---------------------------------------------------------------- PC worker (Windows; only allowed capabilities)
def pc_allowed() -> set[str]:
    try:
        return set(json.loads(PC_ALLOW.read_text(encoding='utf-8')).get('allowed') or [])
    except (OSError, ValueError):
        return set()


def _run(cmd, cwd, timeout=1800):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, errors='replace', timeout=timeout,
                           shell=False, env={**os.environ, 'GRADLE_OPTS': os.environ.get('GRADLE_OPTS', '-Xmx2g')})
        return p.returncode, (p.stdout + p.stderr)[-3000:]
    except (OSError, subprocess.TimeoutExpired) as e:
        return 124, f'{type(e).__name__}: {e}'


def java_build(work: Path, args: dict) -> tuple[bool, str]:
    d = (work / (args.get('dir') or '.')).resolve()
    if work.resolve() not in (d, *d.parents):
        return False, 'dir außerhalb des Arbeitsordners'
    if (d / 'gradlew.bat').is_file() and os.name == 'nt':
        code, out = _run([str(d / 'gradlew.bat'), 'build', '--no-daemon', '--console=plain'], d)
    elif (d / 'build.gradle').is_file() or (d / 'build.gradle.kts').is_file():
        code, out = _run(['gradle', 'build', '--no-daemon', '--console=plain'], d)
    else:  # plain Java: javac + jar, no network
        srcs = [str(p) for p in d.rglob('*.java')]
        if not srcs:
            return False, 'keine Java-Quellen gefunden'
        (d / 'build' / 'classes').mkdir(parents=True, exist_ok=True)
        code, out = _run(['javac', '-d', str(d / 'build' / 'classes'), *srcs], d)
        if code == 0:
            (d / 'build' / 'libs').mkdir(parents=True, exist_ok=True)
            res = d / 'src' / 'main' / 'resources'
            extra = ['-C', str(res), '.'] if res.is_dir() else []
            code, out2 = _run(['jar', 'cf', str(d / 'build' / 'libs' / f'{d.name}.jar'), '-C', str(d / 'build' / 'classes'), '.', *extra], d)
            out += out2
    return code == 0, out


PC_CAPS = {'java.build': java_build}


def pc_probe() -> dict:
    caps = {}
    code, out = _run(['java', '-version'], str(Path.home()), 60)
    jv = out.strip().splitlines()[0] if out.strip() else ''
    if code != 0:
        caps['java.build'] = {'status': 'missing', 'detail': 'java nicht gefunden'}
    else:  # real self-test: compile and pack a tiny program (no network)
        import tempfile
        t = Path(tempfile.mkdtemp(prefix='jarvis-pc-'))
        (t / 'src').mkdir()
        (t / 'src' / 'Hallo.java').write_text('public class Hallo { public static void main(String[] a) { System.out.println("ok"); } }')
        ok, detail = java_build(t, {})
        caps['java.build'] = {'status': 'tested' if ok and any(t.rglob('*.jar')) else 'failed', 'version': jv, 'detail': detail[-200:]}
    for name, cmd in (('blender.render', ['blender', '--version']), ('ollama.ask', ['ollama', '--version'])):
        code, out = _run(cmd, str(Path.home()), 60)
        caps[name] = {'status': 'available' if code == 0 else 'missing', 'version': (out.strip().splitlines() or [''])[0][:60],
                      'detail': 'noch kein Selbsttest/PC-Adapter in V16' if code == 0 else 'nicht installiert'}
    return caps


def pc_worker(once: bool) -> int:
    allowed = pc_allowed() & set(PC_CAPS)
    if not allowed:
        print(f'PC-Worker: keine PC-Fähigkeit freigegeben. Freigabe durch Philipp: Datei {PC_ALLOW} mit '
              '{"allowed": ["java.build"]} anlegen (Builds laufen am PC ohne Sandbox und mit Netz für Abhängigkeiten).')
        return 3
    import shutil
    import tempfile
    while True:
        code, r = call(['pc-lease'], json.dumps({'caps': sorted(allowed), 'worker': os.environ.get('COMPUTERNAME', 'pc')}).encode())
        lease = r.get('lease') if code == 0 else None
        if not lease:
            if once:
                print('PC-Worker: nichts zu tun.')
                return 0
            time.sleep(60)
            continue
        job, sid = lease['job_id'], lease['sid']
        work = Path(tempfile.mkdtemp(prefix=f'jarvis-{job}-'))
        try:
            code, raw = call(['pc-pull', job], binary=True, timeout=900)
            if code != 0:
                raise RuntimeError('Arbeitsordner nicht ladbar')
            with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as tf:
                for m in tf.getmembers():
                    if not m.isfile() or m.name.startswith(('/', '..')) or '..' in Path(m.name).parts:
                        continue
                    dst = work / m.name
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    with tf.extractfile(m) as s, open(dst, 'wb') as fh:
                        shutil.copyfileobj(s, fh)
            before = {p: p.stat().st_mtime for p in work.rglob('*') if p.is_file()}
            ok, detail = PC_CAPS[lease['capability']](work, lease.get('args') or {})
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode='w:gz') as tf:
                for p in work.rglob('*'):
                    if p.is_file() and not p.is_symlink() and before.get(p) != p.stat().st_mtime and '.gradle' not in p.parts:
                        tf.add(str(p), arcname=str(p.relative_to(work)).replace('\\', '/'), recursive=False)
            code, r = call(['pc-push', job, sid, '--ok' if ok else '--fail', '--detail', detail[-1500:]], buf.getvalue(), timeout=900)
            print(f'PC-Worker: {job}/{sid} {lease["capability"]}: {"ok" if ok else "gescheitert"} -> {r}')
        except Exception as e:  # noqa: BLE001
            call(['pc-push', job, sid, '--fail', '--detail', f'PC-Worker-Fehler: {type(e).__name__}: {e}'])
            print(f'PC-Worker: Fehler {e}')
        finally:
            shutil.rmtree(work, ignore_errors=True)
        if once:
            return 0


# ---------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog='jarvis', description='JARVIS V16: Aufträge an den MA-Server übergeben und verfolgen.')
    ap.add_argument('--json', action='store_true', help='Rohdaten ausgeben')
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('submit'); s.add_argument('request'); s.add_argument('--file', action='append', default=[])
    s.add_argument('--model', choices=['haiku', 'sonnet', 'opus']); s.add_argument('--public', action='store_true')
    s.add_argument('--quality', default=''); s.add_argument('--deadline-min', type=int); s.add_argument('--plan-approval', action='store_true')
    s.add_argument('--no-web', action='store_true')
    sp.add_parser('status').add_argument('job', nargs='?')
    s = sp.add_parser('events'); s.add_argument('job', nargs='?'); s.add_argument('--since', type=int, default=0)
    s = sp.add_parser('wait'); s.add_argument('job', nargs='?'); s.add_argument('--minutes', type=float, default=9)
    s = sp.add_parser('result'); s.add_argument('job', nargs='?'); s.add_argument('--fetch', action='store_true'); s.add_argument('--to')
    sp.add_parser('cancel').add_argument('job')
    s = sp.add_parser('approve'); s.add_argument('job'); s.add_argument('--step'); s.add_argument('--answer', default='')
    s = sp.add_parser('forget'); s.add_argument('kind', choices=['template', 'lesson', 'memory']); s.add_argument('ident')
    for name in ('list', 'usage', 'caps', 'learned', 'doctor', 'flush', 'pc-report', 'meta'):
        sp.add_parser(name)
    s = sp.add_parser('pc-worker'); s.add_argument('--once', action='store_true')
    a = ap.parse_args(argv)
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass

    def show(code, r, fmt=None):
        if a.json or fmt is None or code != 0:
            print(json.dumps(r, ensure_ascii=False, indent=1))
        else:
            print(fmt(r))
        return code

    try:
        if a.cmd != 'flush':
            flush()
        if a.cmd == 'submit':
            opts = {'origin': 'pc' if not on_server() else 'server'}
            if a.model:
                opts['model'] = a.model
            if a.public:
                opts['data_class'] = 'public'
            if a.quality:
                opts['quality'] = a.quality
            if a.deadline_min:
                opts['deadline_min'] = a.deadline_min
            if a.plan_approval:
                opts['plan_approval'] = True
            if a.no_web:
                opts['no_web'] = True
            entry = {'request': a.request, 'client_id': 'pc-' + uuid.uuid4().hex, 'options': opts,
                     'files': [str(Path(f).expanduser().resolve(strict=True)) for f in a.file]}
            try:
                code, r = send(entry)
            except Offline as e:
                OUTBOX.mkdir(parents=True, exist_ok=True)
                (OUTBOX / f'{entry["client_id"]}.json').write_text(json.dumps(entry, ensure_ascii=False), encoding='utf-8')
                print(f'Server offline ({e}). Auftrag sicher in der Warteschlange ({entry["client_id"]}); wird beim nächsten Aufruf gesendet.')
                return 0
            if code == 0:
                remember(r['job_id'])
            return show(code, r, lambda r: (f'An JARVIS übergeben: {r["job_id"]} ({"bereits vorhanden" if r.get("duplicate") else "neu"}), '
                                            f'Datenklasse {r.get("data_class", "?")}'
                                            + (f', erkannte externe Wirkungen: {", ".join(r["effects"])} (werden nicht ausgeführt)' if r.get('effects') else '')
                                            + '.\nJARVIS arbeitet jetzt selbstständig auf dem Server. Stand: python '
                                            + Path(__file__).as_posix() + f' status {r["job_id"]}'))
        if a.cmd == 'status':
            return show(*call(['status', job_arg(a.job)]), fmt_status)
        if a.cmd == 'events':
            return show(*call(['events', job_arg(a.job), '--since', str(a.since)]),
                        lambda r: '\n'.join(time.strftime('%H:%M:%S', time.localtime(e['ts'])) + f' [{e["kind"]}] {e["text"]}' for e in r['events']))
        if a.cmd == 'wait':
            j = job_arg(a.job)
            end = time.time() + a.minutes * 60
            while True:
                code, r = call(['status', j])
                if code != 0 or r['state'] in ('done', 'partial', 'failed', 'cancelled', 'waiting_approval') or time.time() > end:
                    return show(code, r, fmt_status)
                time.sleep(20)
        if a.cmd == 'result':
            j = job_arg(a.job)
            code, r = call(['result', j])
            if code != 0 or not a.fetch:
                return show(code, r, lambda r: f'{j}: {r["state"]}, Dateien am Server in {r["results_dir"]}:\n'
                                              + '\n'.join('  ' + f for f in r['files']))
            if not r.get('final'):
                print('Der Auftrag ist noch nicht fertig.')
                return 2
            code, raw = call(['result-tar', j], binary=True, timeout=900)
            if code != 0:
                return show(code, raw if isinstance(raw, dict) else {'error': 'Download fehlgeschlagen'})
            dest = Path(a.to).expanduser() if a.to else RESULTS / j
            dest.mkdir(parents=True, exist_ok=True)
            with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as tf:
                for m in tf.getmembers():
                    if m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts:
                        tgt = dest / m.name
                        tgt.parent.mkdir(parents=True, exist_ok=True)
                        with tf.extractfile(m) as s, open(tgt, 'wb') as fh:
                            fh.write(s.read())
            print(f'Ergebnis {j} ({r["state"]}) liegt in: {dest}')
            return 0
        if a.cmd == 'list':
            return show(*call(['list']), lambda r: '\n'.join(
                f'{x["id"]}  {STATES.get(x["state"], x["state"]):26} {x["claude_calls"]:>2} Aufrufe  {x["request"]}' for x in r['jobs']) or 'Keine Aufträge.')
        if a.cmd == 'usage':
            return show(*call(['usage']), lambda r: json.dumps(r, ensure_ascii=False, indent=1))
        if a.cmd in ('caps', 'learned', 'doctor', 'meta'):
            return show(*call([a.cmd]), lambda r: json.dumps(r, ensure_ascii=False, indent=1))
        if a.cmd == 'cancel':
            return show(*call(['cancel', job_arg(a.job)]), lambda r: f'{r["job_id"]}: {r["state"]}')
        if a.cmd == 'approve':
            args = ['approve', job_arg(a.job)] + (['--step', a.step] if a.step else []) + (['--answer', a.answer] if a.answer else [])
            return show(*call(args), lambda r: f'{r["job_id"]}: freigegeben, läuft weiter')
        if a.cmd == 'forget':
            return show(*call(['forget', a.kind, a.ident]), lambda r: f'widerrufen: {r}')
        if a.cmd == 'flush':
            n = flush(quiet=False)
            print(f'{len(n)} Auftrag/Aufträge aus der Warteschlange gesendet.' if n else 'Warteschlange leer oder Server offline.')
            return 0
        if a.cmd == 'pc-report':
            caps = pc_probe()
            code, r = call(['pc-report'], json.dumps({'caps': caps}).encode())
            return show(code, {'pc': caps, 'server': r}, lambda x: json.dumps(x, ensure_ascii=False, indent=1))
        if a.cmd == 'pc-worker':
            return pc_worker(a.once)
    except Offline as e:
        print(f'JARVIS-Server nicht erreichbar: {e}. Nichts verändert.')
        return 4
    return 2


if __name__ == '__main__':
    sys.exit(main())
