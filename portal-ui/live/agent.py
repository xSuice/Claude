#!/usr/bin/python3
"""Narrow host helper. No user-supplied commands, images or container arguments."""
import concurrent.futures
import grp
import ipaddress
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import socket
import socketserver
import stat
import struct
import subprocess
import threading
import time
import uuid
import psutil

ROOT = Path('/srv/ma-home')
CFG = Path('/etc/ma-home/host.json')
SOCKET = '/run/ma-home/agent.sock'
LOCK = threading.Lock()
POOL = concurrent.futures.ThreadPoolExecutor(max_workers=1)
DOCKER = ['docker', '--host', 'unix:///var/run/docker.sock']
EXTENSIONS = {'.pdf', '.doc', '.docx', '.odt', '.ppt', '.pptx', '.odp', '.xls', '.xlsx', '.ods', '.txt', '.rtf', '.png', '.jpg', '.jpeg', '.tif', '.tiff'}
UUID = re.compile('[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}\\Z')


def cfg():
    return json.loads(CFG.read_text())


def run(args, timeout=15, **kw):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, **kw)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or 'Befehl fehlgeschlagen')[-1200:])
    return result.stdout


def atomic(path, obj):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(obj, ensure_ascii=False))
    os.chmod(temp, 0o600)
    temp.replace(path)


def compose(*args):
    return run(DOCKER + ['compose', '-p', 'ma-home', '-f', '/etc/ma-home/compose.json', *args], timeout=90)


def source_fd(user, path):
    if not isinstance(path, str) or not path or len(path) > 2048 or '\\' in path or '\x00' in path:
        raise ValueError('Ungueltiger Dateipfad')
    parts = path.split('/')
    if any(not p or p.startswith('.') for p in parts):
        raise ValueError('Versteckte Dateien und relative Pfade sind nicht freigegeben')
    fd = os.open(ROOT / 'files' / user, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for index, part in enumerate(parts):
            nxt = os.open(part, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | (os.O_DIRECTORY if index < len(parts)-1 else 0), dir_fd=fd)
            os.close(fd)
            fd = nxt
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size > 30*1024*1024:
            raise ValueError('Nur regulaere Dateien bis 30 MB sind erlaubt')
        return fd
    except Exception:
        os.close(fd)
        raise


def safe_copy(src, dest, maximum=110*1024*1024):
    fd = os.open(src, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size > maximum:
            raise ValueError('Ungueltige Ausgabedatei')
        with os.fdopen(fd, 'rb', closefd=False) as inp, open(dest, 'xb') as out:
            shutil.copyfileobj(inp, out, 65536)
    finally:
        os.close(fd)


def set_state(path, **fields):
    state = json.loads(path.read_text())
    state.update(fields)
    atomic(path, state)


def job_worker(job, meta, settings):
    state = job / 'state.json'
    name = 'ma-home-convert-' + meta['id']
    uid = settings['web_uid']
    try:
        set_state(state, state='running')
        inp, out = job / 'input', job / 'output'
        out.mkdir(mode=0o700)
        os.chown(out, uid, uid)
        if meta['kind'] == 'scan':
            device = settings.get('scanner')
            if not device:
                raise ValueError('Kein unterstuetzter Scanner erkannt. sudo ma-home scan-detect ausfuehren.')
            scan_user = pwd.getpwnam('ma-scan')
            groups = [grp.getgrnam(n).gr_gid for n in ('scanner', 'lp') if n in {g.gr_name for g in grp.getgrall()}]
            # The device comes only from a root-owned discovery result, never the HTTP request.
            with open(inp / 'document.png', 'xb') as stream:
                process = subprocess.run(['prlimit', '--as=536870912', '--fsize=100663296', '--', 'scanimage', '--device-name', device, '--format=png', '--resolution', '150'], stdout=stream, stderr=subprocess.PIPE, timeout=180, user=scan_user.pw_uid, group=scan_user.pw_gid, extra_groups=groups)
            if process.returncode:
                raise RuntimeError(process.stderr.decode(errors='replace')[-1000:])
            os.chmod(inp / 'document.png', 0o644)
        image = settings['converter_image']
        # All image and volume parameters are root-managed constants. Container has no network.
        args = DOCKER + ['run', '--rm', '--name', name, '--network', 'none', '--read-only', '--user', f'{uid}:{uid}', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true', '--memory', '768m', '--memory-swap', '1024m', '--cpus', '0.8', '--pids-limit', '128', '--ulimit', 'fsize=115343360:115343360', '--tmpfs', '/tmp:rw,nosuid,nodev,size=256m,mode=1777', '--mount', f'type=bind,src={inp},dst=/input,readonly', '--mount', f'type=bind,src={out},dst=/output', image]
        try:
            run(args, timeout=300)
        finally:
            subprocess.run(DOCKER + ['rm', '-f', name], capture_output=True, timeout=15)
        manifest_fd = os.open(out / 'result.json', os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(manifest_fd) as stream:
            manifest = json.loads(stream.read(4096))
        pages = int(manifest['pages'])
        if not 1 <= pages <= 20:
            raise ValueError('Ungueltige Seitenzahl')
        # Copy generated files out of the container without following links.
        pub = ROOT / 'previews' / meta['user'] / meta['id']
        pub.mkdir(mode=0o750)
        # PREVIEW-GRP-FIX (2026-10-27): laeuft das Portal als extra_uid (andrew, Mitglied der Gruppe web_gid), muessen
        # Vorschau-Ordner/-Seiten fuer diese Gruppe lesbar sein; sonst PermissionError -> HTTP 500. Ohne extra_uids: altes Verhalten.
        pgid = settings['web_gid'] if settings.get('extra_uids') and 'web_gid' in settings else uid
        pmode_dir, pmode_file = (0o750, 0o640) if pgid != uid else (0o750, 0o600)
        os.chown(pub, uid, pgid)
        os.chmod(pub, pmode_dir)
        for n in range(1, pages+1):
            target = pub / ('page-%d.jpg' % n)
            safe_copy(out / target.name, target, maximum=5*1024*1024)
            os.chown(target, uid, pgid)
            os.chmod(target, pmode_file)
        checked = job / 'document.pdf'
        safe_copy(out / 'document.pdf', checked)
        os.chown(checked, uid, uid)
        os.chmod(job, 0o711)
        os.chmod(checked, 0o600)
        result = dict(state='done', preview=True, pages=pages, total_pages=int(manifest['total_pages']))
        if meta['kind'] == 'print':
            if not settings.get('printer_ready'):
                raise ValueError('Drucker noch nicht eingerichtet: sudo ma-home printer-detect')
            # Mark before submitting. Interrupted submissions are never automatically repeated.
            set_state(state, state='submitting', message='Druckauftrag wird uebergeben; nicht erneut senden.')
            output = run(['lp', '-h', 'localhost', '-d', 'ma_home', '-n', '1', '--', str(checked)], timeout=30, user=uid, group=uid)
            result['message'] = output.strip()
        elif meta['kind'] == 'scan':
            directory = ROOT / 'files' / meta['user'] / 'Scans'
            # The web user can rename its Scans folder. Reject links and non-directories.
            try:
                directory.mkdir(mode=0o750)
                os.chown(directory, uid, uid)
            except FileExistsError:
                pass
            dirfd = os.open(directory, os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                filename = 'Scan-' + time.strftime('%Y%m%d-%H%M%S') + '-' + meta['id'][:8] + '.pdf'
                fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dirfd)
                os.fchown(fd, uid, uid)
                with os.fdopen(fd, 'wb') as dst, open(checked, 'rb') as src:
                    shutil.copyfileobj(src, dst)
                result['message'] = 'Gespeichert unter Scans/' + filename
            finally:
                os.close(dirfd)
        set_state(state, **result)
    except Exception as error:
        old = json.loads(state.read_text())
        extra = ' Druckstatus unklar; zuerst Druckerwarteschlange pruefen, nicht blind wiederholen.' if old['state'] == 'submitting' else ''
        set_state(state, state='error', message=str(error)[-1500:] + extra)
    finally:
        for path in (job / 'input', job / 'output'):
            shutil.rmtree(path, ignore_errors=True)
        (job / 'document.pdf').unlink(missing_ok=True)
        LOCK.release()


def start_job(req, settings):
    key, kind, user = req.get('key', ''), req.get('kind'), req['user']
    if not isinstance(key, str) or not UUID.fullmatch(key) or kind not in ('preview', 'print', 'scan'):
        raise ValueError('Ungueltiger Auftrag')
    job = ROOT / 'jobs' / key
    if job.exists():
        meta = json.loads((job / 'state.json').read_text())
        if meta['user'] != user or meta['kind'] != kind:
            raise ValueError('Auftragskennung ist bereits vergeben')
        return {'id': key, 'state': meta['state']}
    if not LOCK.acquire(blocking=False):
        return {'error': 'Ein Dokument- oder Scanauftrag laeuft bereits. Bitte warten.', 'status': 409}
    try:
        # Prevent a user's job accumulation from filling the disk.
        jobs = list((ROOT / 'jobs').iterdir())
        for old in jobs:
            if old.is_dir() and time.time()-old.stat().st_mtime > 7*86400:
                info = json.loads((old / 'state.json').read_text())
                shutil.rmtree(ROOT / 'previews' / info['user'] / old.name, ignore_errors=True)
                shutil.rmtree(old)
        if shutil.disk_usage(ROOT).free < 1024**3 or len(jobs) > 1000:
            raise ValueError('Zu wenig Speicher oder zu viele Auftraege; alte Vorschauen zuerst bereinigen')
        job.mkdir(mode=0o700)
        (job / 'input').mkdir(mode=0o755)
        os.chmod(job / 'input', 0o755)  # mkdir(mode=) wird von UMask=0077 maskiert; Container-Benutzer muss /input lesen koennen
        if kind != 'scan':
            ext = Path(req.get('path', '')).suffix.lower()
            if ext not in EXTENSIONS:
                raise ValueError('Dieses Dateiformat wird nicht unterstuetzt')
            fd = source_fd(user, req.get('path'))
            with os.fdopen(fd, 'rb') as source, open(job / 'input' / ('document' + ext), 'xb') as dest:
                shutil.copyfileobj(source, dest, 65536)
            os.chmod(job / 'input' / ('document' + ext), 0o644)
        meta = {'id': key, 'user': user, 'kind': kind, 'state': 'queued', 'created': int(time.time())}
        atomic(job / 'state.json', meta)
        POOL.submit(job_worker, job, meta, settings)
        return {'id': key, 'state': 'queued'}
    except Exception:
        shutil.rmtree(job, ignore_errors=True)
        LOCK.release()
        raise


def status(settings, admin):
    mem = psutil.virtual_memory()
    disk = shutil.disk_usage(ROOT)
    status = dict(cpu=psutil.cpu_percent(interval=0.1), ram_used=mem.used, ram_total=mem.total, disk_used=disk.used, disk_total=disk.total, uptime=int(time.time()-psutil.boot_time()), printer=settings.get('printer_ready', False), scanner=bool(settings.get('scanner')), backup=Path('/etc/ma-home/backup.json').exists(), service='MA Home', busy=LOCK.locked())
    if admin:
        ids = run(DOCKER + ['ps', '-aq', '--filter', 'label=io.ma-home.managed=v1']).split()
        data = json.loads(run(DOCKER + ['inspect', *ids])) if ids else []
        status['containers'] = [dict(name=c['Config']['Labels'].get('com.docker.compose.service', c['Name']), state=c['State']['Status'], oom=c['State'].get('OOMKilled'), memory=c['HostConfig']['Memory']) for c in data]
        status['firewall'] = run(['ufw', 'status'], timeout=5).strip()
        status['backup_status'] = json.loads((ROOT / 'backup-status.json').read_text()) if (ROOT / 'backup-status.json').exists() else {'state': 'Kein externer Backup-Datentraeger eingerichtet'}
    return status


def handle(req):
    settings = cfg()
    user = req.get('user', '')
    if user not in settings['users']:
        raise ValueError('Unbekannter Benutzer')
    admin = settings['users'][user]['admin']
    action = req.get('action')
    if action == 'status':
        return status(settings, admin)
    if action == 'job':
        return start_job(req, settings)
    if action == 'job-status':
        key = req.get('id', '')
        if not isinstance(key, str) or not UUID.fullmatch(key):
            raise ValueError('Ungueltige Auftragskennung')
        result = json.loads((ROOT / 'jobs' / key / 'state.json').read_text())
        if result['user'] != user:
            return {'error': 'Auftrag nicht gefunden', 'status': 404}
        return result
    if action == 'service' and admin:
        name, verb = req.get('service'), req.get('verb')
        if name not in ('filebrowser', 'ntfy', 'couchdb') or verb not in ('start', 'stop', 'restart'):
            raise ValueError('Dieser Dienst kann hier nicht veraendert werden')
        compose(verb, name)
        return {'ok': True}
    raise ValueError('Aktion nicht freigegeben')


def auth_failure_line(event):
    """Parse JSON fields, never regex arbitrary user-agent strings into firewall bans."""
    req = event.get('request', {})
    uri = req.get('uri', '').split('?', 1)[0]
    if req.get('method') != 'POST' or event.get('status') not in (401,403):
        return None
    if uri not in ('/auth/api/firstfactor','/auth/api/secondfactor/totp'):
        return None
    address = str(ipaddress.ip_address(req.get('remote_ip', '')))
    return 'MA_HOME_AUTH_FAILURE ip=' + address + '\n'


def audit_log():
    path = ROOT / 'caddylogs/access.log'
    stream, inode = None, None
    while True:
        try:
            current = path.stat()
            if stream is None or inode != current.st_ino:
                if stream: stream.close()
                stream = path.open()
                stream.seek(0, 2)  # No historic failures rebanned after a restart.
                inode = current.st_ino
            for _ in range(100):
                position = stream.tell()
                line = stream.readline(1024*1024)
                if not line:break
                if not line.endswith('\n'):
                    stream.seek(position)
                    break
                try:
                    failure = auth_failure_line(json.loads(line))
                    if failure:
                        with open(ROOT / 'web-failures.log','a') as failures:
                            failures.write(failure)
                except (ValueError, TypeError):
                    pass
        except OSError:
            pass
        time.sleep(2)


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        pid, uid, gid = struct.unpack('3i', self.request.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        c = cfg()
        if uid not in (0, c['web_uid'], *c.get('extra_uids', [])):   # extra_uids: optional, fehlt es -> altes Verhalten
            return
        self.request.settimeout(15)
        line = self.rfile.readline(16385)
        try:
            if len(line) > 16384:
                raise ValueError('Anfrage zu gross')
            response = handle(json.loads(line))
        except Exception as error:
            response = {'error': str(error)[-1500:], 'status': 400}
        self.wfile.write(json.dumps(response).encode() + b'\n')


class Server(socketserver.UnixStreamServer):
    request_queue_size = 16


if __name__ == '__main__':
    # Jobs that survived a crash must never be automatically printed again.
    for state in (ROOT / 'jobs').glob('*/state.json'):
        old = json.loads(state.read_text())
        if old['state'] in ('queued', 'running', 'submitting'):
            set_state(state, state='error', message='Server wurde unterbrochen. Vor erneutem Druck die Warteschlange pruefen.')
    threading.Thread(target=audit_log, daemon=True).start()
    Path(SOCKET).unlink(missing_ok=True)
    with Server(SOCKET, Handler) as server:
        c = cfg()
        if c.get('extra_uids'):   # Portal laeuft nicht als web_uid: Gruppe oeffnen, UID-Pruefung (SO_PEERCRED) bleibt massgeblich
            os.chown(SOCKET, c['web_uid'], c.get('extra_gid', c['web_uid']))
            os.chmod(SOCKET, 0o660)
        else:
            os.chown(SOCKET, c['web_uid'], c['web_uid'])
            os.chmod(SOCKET, 0o600)
        server.serve_forever()
