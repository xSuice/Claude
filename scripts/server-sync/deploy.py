#!/usr/bin/env python3
"""Auto-Deploy PC -> MA-Server (ohne Modell). Liefert nur COMMITTETE Staende aus (git HEAD), nie halbfertige Arbeitskopien.
 1. Eigene Dateien des Server-Benutzers (Cron-Skripte, ask.py): direkt per ssh nach ~/MA-Server/...
 2. Portal-Oberflaeche, Claude-Bruecke, Router: nach ~/deploy-staging, dann `sudo -n /usr/local/sbin/ma-deploy`
    (einmalig eingerichtet mit server/deploy/auto-deploy-einrichten.sh; ohne diese Regel wird nur gemeldet, nichts kaputtgemacht).
Vorher: JS mit `node --check`, Python mit compile(). Fehler -> kein Deploy.
Aufruf: python deploy.py [--dry] [--quiet]     Log: ~/.claude/state/deploy.log     Exit 0 = ok/nichts zu tun, 1 = Fehler, 2 = Regel fehlt"""
import hashlib
import io
import os
import subprocess
import sys
import tarfile
import tempfile
import time

PC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
HOST = 'ma-server'
LOG = os.path.expanduser('~/.claude/state/deploy.log')
DRY, QUIET = '--dry' in sys.argv, '--quiet' in sys.argv

WEB = ['index.html', 'app.js', 'style.css', 'sw.js', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png']
WEB_HASHED = WEB[:5]                                   # fuer diese fuehrt ma-deploy Pruefsummen in DEPLOYED-UI.sha256
ROOT_FILES = {                                         # Repo-Pfad -> (Staging-Name, Zielpfad auf dem Server fuer den Vergleich)
    'server/claude-bridge/ma-claude-bridge.py': ('ma-claude-bridge.py', '/usr/local/lib/ma-claude-bridge.py'),
    'scripts/router/router_core.py': ('router_core.py', '/usr/local/lib/router_core.py'),
}
USER_FILES = {                                         # Repo-Pfad -> Pfad im Home des Server-Benutzers
    'scripts/server-sync/morgenbrief.py': 'MA-Server/scripts/server-sync/morgenbrief.py',
    'scripts/server-sync/vault-graph-export.py': 'MA-Server/scripts/server-sync/vault-graph-export.py',
    'scripts/ext-ai/ask.py': 'MA-Server/scripts/ext-ai/ask.py',
    'scripts/server-sync/fristen-erinnerung.py': 'MA-Server/scripts/server-sync/fristen-erinnerung.py',
}


def log(m):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'a', encoding='utf-8') as fh:
        fh.write(time.strftime('%Y-%m-%d %H:%M:%S ') + m + '\n')
    if not QUIET:
        print(m)


def head(path):
    r = subprocess.run(['git', '-C', PC, 'show', 'HEAD:' + path], capture_output=True, timeout=30)
    return r.stdout.replace(b'\r\n', b'\n') if r.returncode == 0 else None


def sha(b):
    return hashlib.sha256(b.replace(b'\r\n', b'\n')).hexdigest()


def ssh(cmd, data=None, timeout=180):
    return subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', HOST, cmd], input=data, capture_output=True, timeout=timeout)


def server_hashes():
    script = ("[ -f /opt/ma-home/DEPLOYED-UI.sha256 ] && sed 's/^/D /' /opt/ma-home/DEPLOYED-UI.sha256\n"
              + ''.join(f'echo "H {srv} $(tr -d \'\\r\' < {srv} 2>/dev/null | sha256sum | cut -d" " -f1)"\n' for _, srv in ROOT_FILES.values())
              + ''.join(f'echo "U {p} $(tr -d \'\\r\' < "$HOME/{p}" 2>/dev/null | sha256sum | cut -d" " -f1)"\n' for p in {**USER_FILES, **project_skills()}.values())
              + 'echo "R $(sudo -n -l /usr/local/sbin/ma-deploy >/dev/null 2>&1 && echo ja || echo nein)"\n')
    r = ssh('bash -s', script.encode())
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode('utf-8', 'replace')[:200] or 'ssh Code %d' % r.returncode)
    web, root, user, regel = {}, {}, {}, False
    for ln in r.stdout.decode('utf-8', 'replace').splitlines():
        k, _, rest = ln.partition(' ')
        if k == 'D':
            h, _, n = rest.partition('  ')
            web[n.strip()] = h.strip()
        elif k in ('H', 'U'):
            p, _, h = rest.rpartition(' ')
            (root if k == 'H' else user)[p] = h
        elif k == 'R':
            regel = rest.strip() == 'ja'
    return web, root, user, regel


def check_syntax(files):
    """files: {name: bytes}. Gibt Fehlertext oder None."""
    for name, data in files.items():
        if name.endswith('.js'):
            with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as t:
                t.write(data)
            try:
                r = subprocess.run(['node', '--check', t.name], capture_output=True, timeout=30)
            except FileNotFoundError:
                r = None                                # ohne node nicht pruefbar, nicht blockieren
            finally:
                os.unlink(t.name)
            if r is not None and r.returncode != 0:
                return f'{name}: ' + r.stderr.decode('utf-8', 'replace')[:300]
        elif name.endswith('.py'):
            try:
                compile(data.decode('utf-8'), name, 'exec')
            except SyntaxError as e:
                return f'{name}: {e}'
    return None


def project_skills():
    """Projekt-Skills (.claude/skills im Repo) -> ~/MA-Server/.claude/skills auf dem Server."""
    r = subprocess.run(['git', '-C', PC, 'ls-tree', '-r', '--name-only', 'HEAD', '.claude/skills'], capture_output=True, timeout=30)
    return {p: 'MA-Server/' + p for p in r.stdout.decode('utf-8', 'replace').splitlines() if p.endswith(('.md', '.py', '.sh', '.json'))}


def main():
    try:
        web_srv, root_srv, user_srv, regel = server_hashes()
    except Exception as e:
        log('Server nicht erreichbar: ' + str(e))
        return 1
    # 1. Dateien des Server-Benutzers
    user_send = {}
    for repo, dest in {**USER_FILES, **project_skills()}.items():
        b = head(repo)
        if b is not None and sha(b) != user_srv.get(dest):
            user_send[dest] = b
    # 2. Dateien, die root installieren muss
    web_files = {}
    for n in WEB:
        b = head('portal-ui/web/' + n)
        if b is not None:
            web_files[n] = b
    web_diff = [n for n in WEB_HASHED if n in web_files and sha(web_files[n]) != web_srv.get(n)]
    root_send = {}
    for repo, (name, srv) in ROOT_FILES.items():
        b = head(repo)
        if b is not None and sha(b) != root_srv.get(srv):
            root_send[name] = b
    if not (user_send or web_diff or root_send):
        app_update()
        log('Nichts zu tun, Server hat den committeten Stand.')
        return 0
    err = check_syntax({**user_send, **{n: web_files[n] for n in web_diff}, **root_send})
    if err:
        log('Syntaxfehler, kein Deploy: ' + err)
        return 1
    log('Zu liefern: ' + ', '.join(list(user_send) + web_diff + list(root_send)))
    if DRY:
        return 0
    if user_send:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode='w', format=tarfile.PAX_FORMAT) as tf:
            for dest, b in user_send.items():
                ti = tarfile.TarInfo(dest); ti.size = len(b); ti.mode = 0o755 if dest.endswith('.py') else 0o644; ti.mtime = time.time()
                tf.addfile(ti, io.BytesIO(b))
        r = ssh('tar -xf - -C ~', buf.getvalue())
        if r.returncode != 0:
            log('Nutzerdateien fehlgeschlagen: ' + r.stderr.decode('utf-8', 'replace')[:200])
            return 1
    if web_diff or root_send:
        if not regel:
            log('Auto-Deploy-Regel fehlt (Server). Einmalig: ssh -t ma-server "sudo bash ~/deploy-staging/auto-deploy-einrichten.sh"')
            stage_setup()
            return 2
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode='w', format=tarfile.PAX_FORMAT) as tf:
            for n, b in {**{'web/' + k: v for k, v in web_files.items()}, **root_send}.items():
                ti = tarfile.TarInfo('deploy-staging/' + n); ti.size = len(b); ti.mode = 0o644; ti.mtime = time.time()
                tf.addfile(ti, io.BytesIO(b))
        r = ssh('mkdir -p ~/deploy-staging/web && tar -xf - -C ~', buf.getvalue())
        if r.returncode != 0:
            log('Staging fehlgeschlagen: ' + r.stderr.decode('utf-8', 'replace')[:200])
            return 1
        r = ssh('sudo -n /usr/local/sbin/ma-deploy', timeout=120)
        out = (r.stdout + r.stderr).decode('utf-8', 'replace').strip().replace('\n', ' | ')
        log(f'ma-deploy Code {r.returncode}: {out[:300]}')
        if r.returncode != 0:
            return 1
    app_update()
    log('Deploy fertig.')
    return 0


def app_update():
    """Windows-App: fertigen Installer (app/desktop/setup/MA Home Setup <version>.exe, Version aus package.json im HEAD) samt latest.json nach ~/app-updates legen."""
    import json
    pj = head('app/desktop/package.json')
    if pj is None:
        return
    ver = json.loads(pj)['version']
    exe = os.path.join(PC, 'app', 'desktop', 'setup', f'MA Home Setup {ver}.exe')
    if not os.path.isfile(exe):
        return
    data = open(exe, 'rb').read()
    h = hashlib.sha256(data).hexdigest()
    r = ssh('cat ~/app-updates/latest.json 2>/dev/null')
    try:
        if json.loads(r.stdout).get('sha256') == h:
            return
    except ValueError:
        pass
    log(f'App-Update {ver} wird bereitgestellt.')
    if DRY:
        return
    name = f'MA-Home-Setup-{ver}.exe'
    r = ssh(f'mkdir -p ~/app-updates && cat > ~/app-updates/{name}.tmp && mv ~/app-updates/{name}.tmp ~/app-updates/{name}', data, timeout=600)
    if r.returncode != 0:
        log('App-Upload fehlgeschlagen: ' + r.stderr.decode('utf-8', 'replace')[:200])
        return
    meta = json.dumps({'version': ver, 'file': name, 'sha256': h})
    ssh(f"printf '%s' '{meta}' > ~/app-updates/latest.json.tmp && mv ~/app-updates/latest.json.tmp ~/app-updates/latest.json && ls -t ~/app-updates/*.exe | tail -n +4 | xargs -r rm -f")
    log('App-Update bereit: ' + name)


def stage_setup():
    """Legt das Einrichtungs-Skript auf den Server (zum einmaligen Ausfuehren mit Sudo)."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w') as tf:
        for n in ('ma-deploy', 'auto-deploy-einrichten.sh'):
            b = open(os.path.join(PC, 'server', 'deploy', n), 'rb').read().replace(b'\r\n', b'\n')
            ti = tarfile.TarInfo('deploy-staging/' + n); ti.size = len(b); ti.mode = 0o755; ti.mtime = time.time()
            tf.addfile(ti, io.BytesIO(b))
    ssh('mkdir -p ~/deploy-staging && tar -xf - -C ~', buf.getvalue())


if __name__ == '__main__':
    sys.exit(main())
