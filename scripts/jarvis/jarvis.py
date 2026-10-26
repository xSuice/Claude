#!/usr/bin/env python3
"""JARVIS V16 client (PC and server). Hands jobs to the JARVIS core on the MA-Server - it never does the work itself.

  python jarvis.py submit "Auftrag" [--file PFAD ...] [--model haiku|sonnet|opus] [--public] [--quality TEXT]
                                    [--deadline-min N] [--plan-approval] [--no-web]
  python jarvis.py status [JOB] | events JOB [--since N] | wait JOB [--minutes 9] | list | usage | caps | learned | doctor
  python jarvis.py result JOB [--fetch] [--to ORDNER]      (Standard-Ziel: Dokumente/JARVIS-Ergebnisse/<JOB>)
  python jarvis.py cancel JOB | approve JOB [--step S] [--answer TEXT] | forget template|lesson ID | flush
  python jarvis.py pc-report | pc-worker [--once] [--allow-once CAP] | pc-gradle-seed
                                                          (PC-Fähigkeiten; isoliert, nur mit lokaler Freigabe)
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
# Every PC step runs in winsandbox (AppContainer + Job Object): no network unless "<cap>:network" is allowed, file access
# only to its own step folder and the separate JARVIS Gradle home, memory/process/CPU caps, tree killed at the end.
# There is deliberately NO unsandboxed fallback: if the sandbox cannot start, the step fails.
GRADLE_HOME = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'ma-jarvis' / 'gradle-home'
JAVA_LIMITS = {'mem_mb': 3072, 'procs': 32, 'cpu_pct': 75, 'timeout_s': 1800}
SKIP_OUT = {'.gradle', '.home', '.tmp', 'build-cache'}


def pc_config() -> dict:
    try:
        return json.loads(PC_ALLOW.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def pc_allowed() -> set[str]:
    return {a.split(':')[0] for a in (pc_config().get('allowed') or [])}


def pc_network(cap: str) -> bool:
    return f'{cap}:network' in set(pc_config().get('allowed') or [])


def _sandbox():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import winsandbox
    return winsandbox


def java_home() -> str:
    cfg = pc_config().get('java_home')
    if cfg:
        return cfg
    root = Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'Eclipse Adoptium'
    jdks = sorted(root.glob('jdk-21*'), reverse=True) + sorted(root.glob('jdk-*'), reverse=True)
    return str(jdks[0]) if jdks else ''


def _sbx_run(cmd: list[str], work: Path, network: bool = False, timeout: int | None = None) -> tuple[int, str]:
    wsb = _sandbox()
    GRADLE_HOME.mkdir(parents=True, exist_ok=True)
    sb = wsb.Sandbox()
    marker = GRADLE_HOME / '.jarvis-granted'
    if not marker.exists():  # grant once; files created later inherit the ACE
        wsb.grant(GRADLE_HOME, sb.sid)
        marker.write_text(sb.sid)
    jh = java_home()
    env = wsb.base_env(work, {'GRADLE_USER_HOME': str(GRADLE_HOME), **({'JAVA_HOME': jh} if jh else {}),
                              'GRADLE_OPTS': '-Xmx1536m', 'PATH': ';'.join(filter(None, [str(Path(jh) / 'bin') if jh else '',
                                                                                         wsb.base_env(work)['PATH']]))})
    lim = wsb.Limits(network=network, **{**JAVA_LIMITS, **({'timeout_s': timeout} if timeout else {})})
    r = sb.run(cmd, work, lim, env)
    head = (f'[sandbox: AppContainer, Netz {"an" if network else "aus"}, max {lim.mem_mb} MB / {lim.procs} Prozesse / '
            f'{lim.cpu_pct} % CPU / {lim.timeout_s} s; Spitze {r.peak_mem_mb} MB, {r.processes} Prozesse, {r.seconds} s'
            f'{", ZEITLIMIT" if r.timed_out else ""}]\n')
    return r.code, head + r.output[-3000:]


def java_build(work: Path, args: dict, network: bool = False) -> tuple[bool, str]:
    d = (work / (args.get('dir') or '.')).resolve()
    if work.resolve() not in (d, *d.parents):
        return False, 'dir außerhalb des Arbeitsordners'
    gradle_flags = ['build', '--no-daemon', '--console=plain'] + ([] if network else ['--offline'])
    if (d / 'gradlew.bat').is_file():
        code, out = _sbx_run([str(d / 'gradlew.bat'), *gradle_flags], d, network)
    elif (d / 'build.gradle').is_file() or (d / 'build.gradle.kts').is_file():
        dists = sorted(GRADLE_HOME.glob('wrapper/dists/gradle-*-bin/*/gradle-*/bin/gradle.bat'), reverse=True)
        if not dists:
            return False, 'kein Gradle im JARVIS-Gradle-Home (python jarvis.py pc-gradle-seed)'
        code, out = _sbx_run([str(dists[0]), *gradle_flags], d, network)
    else:  # plain Java: javac + jar
        srcs = [str(p.relative_to(d)) for p in d.rglob('*.java')]
        if not srcs:
            return False, 'keine Java-Quellen gefunden'
        code, out = _sbx_run(['javac', '-d', 'build/classes', *srcs], d)
        if code == 0:
            (d / 'build' / 'libs').mkdir(parents=True, exist_ok=True)
            extra = ['-C', 'src/main/resources', '.'] if (d / 'src' / 'main' / 'resources').is_dir() else []
            code, out2 = _sbx_run(['jar', 'cf', f'build/libs/{d.name}.jar', '-C', 'build/classes', '.', *extra], d)
            out += out2
    return code == 0, out


PC_CAPS = {'java.build': java_build}


def safe_files(root: Path):
    """Regular files below root - never through junctions/symlinks (a sandboxed build must not smuggle user files out)."""
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [n for n in dirnames if n not in SKIP_OUT and not _is_reparse(Path(dirpath) / n)]
        for n in filenames:
            p = Path(dirpath) / n
            if not _is_reparse(p) and p.is_file():
                yield p


def _is_reparse(p: Path) -> bool:
    try:
        st = os.lstat(p)
    except OSError:
        return True
    return bool(getattr(st, 'st_file_attributes', 0) & 0x400) or os.path.islink(p)  # FILE_ATTRIBUTE_REPARSE_POINT


def pc_gradle_seed() -> int:
    """Copy Gradle distributions and the public dependency caches from ~/.gradle into the JARVIS Gradle home, so that
    sandboxed builds work offline. Never copies gradle.properties, init scripts or credentials."""
    import shutil
    src = Path.home() / '.gradle'
    parts = [('wrapper/dists', True), ('caches/modules-2', True), ('caches/fabric-loom', True)]
    for rel, _ in parts:
        s_, d_ = src / rel, GRADLE_HOME / rel
        if not s_.is_dir():
            print(f'  {rel}: nicht vorhanden')
            continue
        t = time.time()
        shutil.copytree(s_, d_, dirs_exist_ok=True, ignore=shutil.ignore_patterns('*.lck', '*.lock', 'gc.properties'))
        print(f'  {rel}: kopiert ({time.time() - t:.0f} s)')
    _sandbox().grant(GRADLE_HOME, _sandbox().container_sid())
    print(f'JARVIS-Gradle-Home: {GRADLE_HOME} (für den AppContainer freigegeben; ~/.gradle bleibt unsichtbar)')
    return 0


def pc_probe() -> dict:
    caps = {}
    jh = java_home()
    if os.name != 'nt' or not jh:
        caps['java.build'] = {'status': 'missing', 'detail': 'java nicht gefunden' if os.name == 'nt' else 'nur Windows'}
    else:  # real self-test inside the sandbox: compile and pack a tiny program (no network)
        try:
            wsb = _sandbox()
            t = wsb.new_workdir('selftest')
            try:
                (t / 'src').mkdir()
                (t / 'src' / 'Hallo.java').write_text('public class Hallo { public static void main(String[] a) { System.out.println("ok"); } }')
                ok, detail = java_build(t, {})
                status = 'tested' if ok and any(t.rglob('*.jar')) else 'failed'
            finally:
                wsb.cleanup(t)
        except OSError as e:
            status, detail = 'failed', f'Sandbox nicht verfügbar: {e}'
        caps['java.build'] = {'status': status, 'version': Path(jh).name, 'detail': detail.splitlines()[0][:200]}
    for name, cmd in (('blender.render', ['blender', '--version']), ('ollama.ask', ['ollama', '--version'])):
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, errors='replace', timeout=60)
            code, out = p.returncode, p.stdout + p.stderr
        except (OSError, subprocess.TimeoutExpired) as e:
            code, out = 127, f'{type(e).__name__}: {e}'
        caps[name] = {'status': 'available' if code == 0 else 'missing', 'version': (out.strip().splitlines() or [''])[0][:60],
                      'detail': 'noch kein Selbsttest/PC-Adapter in V16' if code == 0 else 'nicht installiert'}
    return caps


def pc_worker(once: bool, allow_once: set[str] | None = None) -> int:
    allowed = (pc_allowed() | (allow_once or set())) & set(PC_CAPS)
    if not allowed:
        print(f'PC-Worker: keine PC-Fähigkeit freigegeben. Freigabe durch Philipp: Datei {PC_ALLOW} mit '
              '{"allowed": ["java.build"]} anlegen. Builds laufen isoliert (AppContainer, ohne Netz, begrenzter Speicher); '
              'Netz nur mit zusätzlich "java.build:network".')
        return 3
    import shutil
    wsb = _sandbox()
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
        work = wsb.new_workdir(job)
        try:
            code, raw = call(['pc-pull', job], binary=True, timeout=900)
            if code != 0:
                raise RuntimeError('Arbeitsordner nicht ladbar')
            with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as tf:
                for m in tf.getmembers():
                    if not m.isfile() or m.name.startswith(('/', '..')) or '..' in Path(m.name).parts or ':' in m.name:
                        continue
                    dst = work / m.name
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    with tf.extractfile(m) as s, open(dst, 'wb') as fh:
                        shutil.copyfileobj(s, fh)
            before = {p: p.stat().st_mtime for p in safe_files(work)}
            cap = lease['capability']
            ok, detail = PC_CAPS[cap](work, lease.get('args') or {}, network=pc_network(cap))
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode='w:gz') as tf:
                for p in safe_files(work):
                    if before.get(p) != p.stat().st_mtime:
                        tf.add(str(p), arcname=str(p.relative_to(work)).replace('\\', '/'), recursive=False)
            code, r = call(['pc-push', job, sid, '--ok' if ok else '--fail', '--detail', detail[-1500:]], buf.getvalue(), timeout=900)
            print(f'PC-Worker: {job}/{sid} {cap}: {"ok" if ok else "gescheitert"} -> {r}')
        except Exception as e:  # noqa: BLE001
            call(['pc-push', job, sid, '--fail', '--detail', f'PC-Worker-Fehler: {type(e).__name__}: {e}'])
            print(f'PC-Worker: Fehler {e}')
        finally:
            wsb.cleanup(work)
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
    s.add_argument('--allow-once', action='append', default=[], help='Fähigkeit nur für diesen Lauf freigeben (Test)')
    sp.add_parser('pc-gradle-seed')
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
            return pc_worker(a.once, set(a.allow_once))
        if a.cmd == 'pc-gradle-seed':
            return pc_gradle_seed()
    except Offline as e:
        print(f'JARVIS-Server nicht erreichbar: {e}. Nichts verändert.')
        return 4
    return 2


if __name__ == '__main__':
    sys.exit(main())
