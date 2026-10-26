#!/usr/bin/env python3
"""Abgleich PC <-> MA-Server fuer Claude (ohne Modell):
 1. Regeln/Einstellungen: PC-CLAUDE.md + server-abschnitt.md, settings.json und Schutz-Hook -> Server (wenn anders).
 2. Projekt MA-Server: Dateien in beide Richtungen. Server geaendert + PC unveraendert -> holen; PC geaendert -> senden;
    beide geaendert -> Serverfassung als "<Datei>.server-konflikt" neben die PC-Datei. Neue Serverdateien werden geholt.
    Geholtes wird lokal committet und nach GitHub gepusht.
 3. Bericht "Was ist neu auf dem Server" -> Vault _Claude-Memory/Dienste/Server-Abgleich.md (Bibliothek, Claude-Sitzungen, Dienste).
Log: ~/.claude/state/claude-abgleich.log   Aufruf: python claude-abgleich.py [--dry]"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import time

PC = r"C:\Users\andre\Documents\MA-Server"
VAULT_REPORT = r"C:\Users\andre\Documents\Obsidian Vault\_Claude-Memory\Dienste\Server-Abgleich.md"
CFG = os.path.join(PC, "server", "claude-config")
HOST = "ma-server"
SRV = "/home/andrew/MA-Server"
STATE = os.path.expanduser("~/.claude/state/claude-abgleich.json")
LOG = os.path.expanduser("~/.claude/state/claude-abgleich.log")
SKIP_PARTS = {".git", "node_modules", "dist", "setup", "installer", "build", "__pycache__", "signing", ".router"}
SKIP_SUFFIX = (".pyc", ".apk", ".keystore", ".pass", ".key", ".log")
MAX = 5 * 1024 * 1024
DRY = "--dry" in sys.argv


def log(m):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "a", encoding="utf-8").write(time.strftime("%Y-%m-%d %H:%M:%S ") + m + "\n")


def ssh(cmd, data=None, binary=False, timeout=180):
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST, cmd], input=data, capture_output=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace")[:300])
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def ok_path(rel):
    parts = rel.split("/")
    return not (set(parts) & SKIP_PARTS) and not rel.endswith(SKIP_SUFFIX) and not parts[-1].startswith(".env")


def pc_files():
    out = {}
    for root, dirs, files in os.walk(PC):
        dirs[:] = [d for d in dirs if d not in SKIP_PARTS]
        for f in files:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, PC).replace("\\", "/")
            if not ok_path(rel) or os.path.getsize(p) > MAX:
                continue
            out[rel] = hashlib.sha1(open(p, "rb").read().replace(b"\r\n", b"\n")).hexdigest()
    return out


SRV_LIST = r"""python3 - <<'PY'
import hashlib, os, json
B = '/home/andrew/MA-Server'; SKIP = set(%s); SUF = tuple(%s); out = {}
for root, dirs, files in os.walk(B):
    dirs[:] = [d for d in dirs if d not in SKIP]
    for f in files:
        p = os.path.join(root, f); rel = os.path.relpath(p, B)
        if rel.endswith(SUF) or f.startswith('.env') or os.path.getsize(p) > %d: continue
        out[rel] = hashlib.sha1(open(p, 'rb').read().replace(b'\r\n', b'\n')).hexdigest()
print(json.dumps(out))
PY""" % (json.dumps(sorted(SKIP_PARTS)), json.dumps(list(SKIP_SUFFIX)), MAX)

REPORT_CMD = r"""python3 - <<'PY'
import os, json, time, glob, subprocess
since = float(%s); res = {}
lib = '/srv/ma-home/library'; neu = []
for root, dirs, files in os.walk(lib):
    dirs[:] = [d for d in dirs if d not in ('vault-notizen', 'vault-snapshots')]
    for f in files:
        p = os.path.join(root, f)
        try:
            if os.path.getmtime(p) > since: neu.append(os.path.relpath(p, lib))
        except OSError: pass
res['bibliothek_neu'] = sorted(neu)[:60]; res['bibliothek_neu_anzahl'] = len(neu)
ses = []
for p in glob.glob('/home/andrew/.claude/projects/*/*.jsonl'):
    if os.path.getmtime(p) <= since: continue
    first = ''
    try:
        for line in open(p, encoding='utf-8'):
            d = json.loads(line)
            if d.get('type') == 'user':
                c = d.get('message', {}).get('content')
                first = c if isinstance(c, str) else ' '.join(x.get('text', '') for x in c if isinstance(x, dict))
                break
    except Exception: pass
    ses.append({'zeit': time.strftime('%%Y-%%m-%%d %%H:%%M', time.localtime(os.path.getmtime(p))), 'ordner': os.path.basename(os.path.dirname(p)), 'start': ' '.join(first.split())[:110]})
res['claude_sitzungen'] = sorted(ses, key=lambda x: x['zeit'], reverse=True)[:20]
def sh(c):
    try: return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception: return '?'
res['dienste'] = sh('systemctl is-active ma-home-web ma-home-agent ma-claude-bridge docker ma-usb-backup.timer | paste -sd" "')
res['platte'] = sh("df -h / | tail -1 | awk '{print $4\" frei von \"$2}'")
res['backup_platte'] = sh("df -h /mnt/ma-backup 2>/dev/null | tail -1 | awk '{print $4\" frei\"}'")
res['letztes_backup'] = sh('systemctl show ma-usb-backup.service -p ExecMainExitTimestamp -p Result | paste -sd" "')
res['laufzeit'] = sh('uptime -p')
print(json.dumps(res))
PY"""


HAVE_CMD = r"""python3 - <<'PY'
import hashlib, json, os
L = %s
print(json.dumps({p: (hashlib.sha1(open(os.path.expanduser('~/' + p), 'rb').read()).hexdigest() if os.path.exists(os.path.expanduser('~/' + p)) else '') for p in L}))
PY"""


def push_config(changes):
    pc_md = open(os.path.expanduser("~/.claude/CLAUDE.md"), encoding="utf-8").read().replace("\r\n", "\n")
    want = {
        ".claude/CLAUDE.md": (pc_md.rstrip("\n") + "\n\n" + open(os.path.join(CFG, "server-abschnitt.md"), encoding="utf-8").read()).encode(),
        ".claude/settings.json": open(os.path.join(CFG, "settings.json"), "rb").read().replace(b"\r\n", b"\n"),
        ".claude/hooks/ma-guard.py": open(os.path.join(CFG, "hooks", "ma-guard.py"), "rb").read().replace(b"\r\n", b"\n"),
        ".claude/hooks/council-auto.py": open(os.path.join(CFG, "hooks", "council-auto.py"), "rb").read().replace(b"\r\n", b"\n"),
    }
    have = json.loads(ssh(HAVE_CMD % json.dumps(list(want))))
    send = {p: b for p, b in want.items() if hashlib.sha1(b).hexdigest() != have.get(p)}
    if send and not DRY:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tf:
            for p, b in send.items():
                ti = tarfile.TarInfo(p); ti.size = len(b); ti.mode = 0o755 if p.endswith(".py") else 0o644; ti.mtime = time.time()
                tf.addfile(ti, io.BytesIO(b))
        ssh("mkdir -p ~/.claude/hooks ~/.claude/skills ~/.claude/agents && tar -xf - -C ~", data=buf.getvalue())
    changes += [f"Regeln/Einstellung zum Server: {p}" for p in send]


GLOBAL_SKIP = ("synced",)          # von der Plattform verwaltet (Skills aus dem Konto)
REVIEW = r"C:\Users\andre\Documents\Obsidian Vault\00 Inbox\Review"
GROUPS = ((os.path.expanduser("~/.claude/skills"), ".claude/skills/"), (os.path.expanduser("~/.claude/agents"), ".claude/agents/"))

SRV_GLOBAL = r"""python3 - <<'PY'
import hashlib, os, json
out = {}
for sub in ('skills', 'agents'):
    base = os.path.expanduser('~/.claude/' + sub)
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in %s]
        for f in files:
            p = os.path.join(root, f)
            if f.endswith('.disabled') or os.path.getsize(p) > %d: continue
            out['.claude/' + sub + '/' + os.path.relpath(p, base).replace(os.sep, '/')] = hashlib.sha1(open(p, 'rb').read().replace(b'\r\n', b'\n')).hexdigest()
print(json.dumps(out))
PY""" % (json.dumps(list(GLOBAL_SKIP)), MAX)


def pc_global():
    out = {}
    for base, prefix in GROUPS:
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in GLOBAL_SKIP]
            for f in files:
                full = os.path.join(root, f)
                if f.endswith(".disabled") or os.path.getsize(full) > MAX:
                    continue
                out[prefix + os.path.relpath(full, base).replace("\\", "/")] = (full, hashlib.sha1(open(full, "rb").read().replace(b"\r\n", b"\n")).hexdigest())
    return out


def sync_global(st, changes):
    """Skills und Agenten (global, ~/.claude) in beide Richtungen. Dreiwege-Vergleich; bei Konflikt wird nichts ueberschrieben,
    die Serverfassung kommt nach 00 Inbox/Review."""
    srv = json.loads(ssh(SRV_GLOBAL))
    pc = pc_global()
    base = st.setdefault("gbase", {})
    pull, push = [], []
    for rel in set(pc) | set(srv):
        p = pc[rel][1] if rel in pc else None
        s, b = srv.get(rel), base.get(rel)
        if p == s:
            base[rel] = p
        elif s and (p is None and b is None or p == b):
            pull.append(rel)
        elif p and (s == b or s is None):
            push.append(rel)
        elif p and s:
            changes.append(f"**Konflikt Skill/Agent** `{rel}`: Serverfassung in `00 Inbox/Review`")
            if not DRY:
                data = ssh(f"tar -cf - -C ~ {rel}", binary=True)
                with tarfile.open(fileobj=io.BytesIO(data)) as tf:
                    m = tf.getmembers()[0]
                    os.makedirs(REVIEW, exist_ok=True)
                    open(os.path.join(REVIEW, "server-konflikt-" + rel.replace("/", "__")), "wb").write(tf.extractfile(m).read())
    changes += [f"Skill/Agent vom Server geholt: {x}" for x in pull] + [f"Skill/Agent zum Server gesendet: {x}" for x in push]
    if DRY:
        return
    if push:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tf:
            for rel in push:
                data = open(pc[rel][0], "rb").read().replace(b"\r\n", b"\n")
                ti = tarfile.TarInfo(rel); ti.size = len(data); ti.mode = 0o755 if rel.endswith((".py", ".sh")) else 0o644; ti.mtime = time.time()
                tf.addfile(ti, io.BytesIO(data))
        ssh("mkdir -p ~/.claude/skills ~/.claude/agents && tar -xf - -C ~", data=buf.getvalue())
        for rel in push:
            base[rel] = pc[rel][1]
    if pull:
        data = ssh("tar -cf - -C ~ -T -", data="\n".join(pull).encode(), binary=True)
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            for m in tf.getmembers():
                if not m.isfile() or ".." in m.name.split("/") or not m.name.startswith((".claude/skills/", ".claude/agents/")):
                    continue
                dest = os.path.join(os.path.expanduser("~"), m.name.replace("/", os.sep))
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                open(dest, "wb").write(tf.extractfile(m).read())
                base[m.name] = srv[m.name]


HIST_SKIP = ("AppData", "System32", "schema-test", "scratch")      # Ordnernamen-Teile ohne Nutzen
HIST_MAX = 50 * 1024 * 1024
SECRET_RE = re.compile(rb"sk-ant-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,}|ghp_[A-Za-z0-9]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|sk-or-v1-[A-Za-z0-9]{20,}")

SRV_HIST = r"""python3 - <<'PY'
import os, json
b = os.path.expanduser('~/.claude/projects'); out = {}
for root, dirs, files in os.walk(b):
    for f in files:
        if f.endswith('.jsonl'):
            p = os.path.join(root, f)
            out[os.path.relpath(p, b).replace(os.sep, '/')] = os.path.getsize(p)
print(json.dumps(out))
PY"""


SECRET_KEY = re.compile(r"key|token|secret|pass|auth|cookie|credential", re.I)
WIN_PATH = re.compile(r"[A-Za-z]:[\\/]|\\\\|\.exe\b|\.cmd\b|\.bat\b|\.ps1\b", re.I)
PORTABLE_CMDS = {"npx", "node", "uvx", "uv", "python", "python3", "docker", "bunx", "deno"}


def mcp_portable(cfg):
    """Eine MCP-Verbindung darf automatisch auf den Server, wenn sie keine Zugangsdaten und keine Windows-Programme/-Pfade braucht."""
    if not isinstance(cfg, dict):
        return False
    if cfg.get("type") in ("http", "sse") or "url" in cfg:
        return not cfg.get("headers") and "command" not in cfg and not SECRET_KEY.search(str(cfg.get("url", "")))
    cmd = str(cfg.get("command", ""))
    args = [str(a) for a in cfg.get("args", [])]
    if os.path.basename(cmd).lower() not in PORTABLE_CMDS or WIN_PATH.search(cmd + " " + " ".join(args)):
        return False
    return not any(SECRET_KEY.search(str(k)) for k in (cfg.get("env") or {})) and not any(SECRET_KEY.search(a) and "=" in a for a in args)


def mcp_windows(cfg):
    """Verbindung braucht ein Windows-Programm/-Pfad oder ein unbekanntes Programm: geht nicht einfach auf den Server."""
    if not isinstance(cfg, dict):
        return True
    if cfg.get("type") in ("http", "sse") or "url" in cfg:
        return "command" in cfg
    cmd = str(cfg.get("command", ""))
    return os.path.basename(cmd).lower() not in PORTABLE_CMDS or bool(WIN_PATH.search(cmd + " " + " ".join(str(a) for a in cfg.get("args", []))))


def mcp_plan(pc, srv, nur_pc, mit_zugang=False):
    """(hinzufuegen, abweichend, nicht_portabel): Verbindungen, die auf dem Server fehlen und portabel sind, werden hinzugefuegt.
    mit_zugang (ausdrueckliche Freigabe von Philipp, siehe mcp-zugang.ok): auch solche mit Zugangsdaten, solange kein Windows-Programm noetig ist."""
    add, differ, nicht = {}, [], []
    for name, cfg in pc.items():
        if name in nur_pc:
            continue
        if name in srv:
            if srv[name] != cfg:
                differ.append(name)
        elif mcp_portable(cfg) or (mit_zugang and not mcp_windows(cfg)):
            add[name] = cfg
        else:
            nicht.append(name)
    return add, differ, nicht


MCP_MERGE = r"""python3 -c '
import json, os, shutil, sys
p = os.path.expanduser("~/.claude.json"); add = json.load(sys.stdin)
d = json.load(open(p)) if os.path.exists(p) else {}
if os.path.exists(p): shutil.copy2(p, p + ".ma-bak")
m = d.setdefault("mcpServers", {})
[m.setdefault(k, v) for k, v in add.items()]
tmp = p + ".ma-tmp"; json.dump(d, open(tmp, "w"), indent=2); os.chmod(tmp, 0o600); os.replace(tmp, p)
print(len(add))'"""


def sync_mcp(changes):
    """Lokale MCP-Verbindungen (Namen und Einstellungen, nie Geheimnisse) vom PC auf den Server angleichen. Fehler stoppen den Abgleich nicht."""
    try:
        pc = json.load(open(os.path.expanduser("~/.claude.json"), encoding="utf-8")).get("mcpServers", {})
        srv = json.loads(ssh("cat ~/.claude.json 2>/dev/null || echo '{}'")).get("mcpServers", {})
        nur_pc = set()
        try:
            nur_pc = {l.strip() for l in open(os.path.join(CFG, "mcp-nur-pc.txt"), encoding="utf-8") if l.strip() and not l.startswith("#")}
        except OSError:
            pass
        zugang = "--mcp-zugang" in sys.argv or os.path.exists(os.path.join(CFG, "mcp-zugang.ok"))
        add, differ, nicht = mcp_plan(pc, srv, nur_pc, zugang)
        if add and not DRY:
            ssh(MCP_MERGE, data=json.dumps(add).encode())          # nur ueber ssh-Stdin in ~/.claude.json (0600) auf dem Server; Werte nie in Log, Git oder Bericht
        changes += [f"Verbindung (MCP) zum Server übertragen: {n}" + (" (mit Zugangsdaten, direkt per ssh)" if not mcp_portable(add[n]) else "") for n in add]
        changes += [f"Verbindung (MCP) `{n}` weicht auf dem Server ab (nicht überschrieben)" for n in differ]
        changes += [f"Verbindung (MCP) `{n}` nur am PC: braucht Zugangsdaten oder ein Windows-Programm (am Server einrichten oder in mcp-nur-pc.txt eintragen)" for n in nicht]
    except Exception as e:
        log(f"MCP-Abgleich fehlgeschlagen: {e!r}")


SECRET_FILE = re.compile(r"(^|/)(\.env[^/]*|[^/]*\.(key|pem|pfx|p12|keystore)|[^/]*(credential|token|passwor|secret)[^/]*)$", re.I)
SECRET_TEXT = re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9]{32,}|xox[baprs]-[A-Za-z0-9-]{20,}|AKIA[0-9A-Z]{16}")


def git(*args, data=None, timeout=60):
    return subprocess.run(["git", "-C", PC, "-c", "core.safecrlf=false", *args], input=data, capture_output=True, timeout=timeout)


def git_secrets(paths):
    """Dateien, die wie Geheimnisse aussehen (Name oder Inhalt); sie werden nie committet."""
    bad = []
    for p in paths:
        if SECRET_FILE.search(p):
            bad.append(p)
            continue
        try:
            full = os.path.join(PC, p.replace("/", os.sep))
            if os.path.getsize(full) <= 2_000_000 and SECRET_TEXT.search(open(full, "rb").read()):
                bad.append(p)
        except OSError:
            pass
    return bad


def git_publish(pulled):
    """Vom Server geholte Dateien committen (nur diese, nach Geheimnis-Pruefung) und alles pushen, was dem Remote voraus ist.
    Unfertige PC-Arbeit bleibt ungemeldet im Arbeitsordner (der Auto-Deploy liefert nur Committetes). Gibt Meldungen fuer den Bericht zurueck."""
    notes = []
    try:
        if pulled:
            bad = git_secrets(pulled)
            ok = [p for p in pulled if p not in bad]
            if bad:
                notes.append("GitHub: NICHT committet (mögliche Geheimnisse): " + ", ".join(bad[:5]))
            if ok:
                nul = ("\0".join(ok) + "\0").encode()
                git("add", "--pathspec-from-file=-", "--pathspec-file-nul", data=nul)
                r = git("commit", "-q", "-m", "Automatischer Abgleich: Änderungen vom Server (%d Dateien)" % len(ok), "--pathspec-from-file=-", "--pathspec-file-nul", data=nul)
                if r.returncode == 0:
                    notes.append("GitHub: %d vom Server geholte Dateien committet" % len(ok))
                elif b"nothing to commit" not in r.stdout + r.stderr:
                    notes.append("GitHub: Commit fehlgeschlagen: " + (r.stderr or r.stdout).decode("utf-8", "replace").strip().splitlines()[0][:150])
        status = git("status", "-sb").stdout.decode("utf-8", "replace").splitlines()
        if status and "ahead" in status[0]:
            r = git("push", "-q", timeout=120)
            if r.returncode == 0:
                notes.append("GitHub: aktualisiert (gepusht)")
            else:
                notes.append("GitHub: Push fehlgeschlagen: " + (r.stderr or r.stdout).decode("utf-8", "replace").strip().splitlines()[-1][:150])
    except Exception as e:
        log(f"GitHub-Veröffentlichung fehlgeschlagen: {e!r}")
        notes.append("GitHub: Fehler bei der Veröffentlichung (siehe Log)")
    for n in notes:
        log(n)
    return notes


def sync_history(changes):
    """Claude-Verlaeufe (~/.claude/projects/**/*.jsonl) in beide Richtungen: Fehlendes wird kopiert, bei Unterschied gewinnt die
    groessere Datei (Protokolle wachsen nur). Dateien mit Schluesselmustern (Klasse C) werden nie kopiert, nur gemeldet."""
    base = os.path.expanduser("~/.claude/projects")
    srv = json.loads(ssh(SRV_HIST))
    pc = {}
    for root, _d, files in os.walk(base):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, base).replace("\\", "/")
            if f.endswith(".jsonl") and not any(x in rel.split("/")[0] for x in HIST_SKIP):
                pc[rel] = os.path.getsize(full)
    to_srv = [r for r, n in pc.items() if n <= HIST_MAX and n > srv.get(r, 0)]
    to_pc = [r for r, n in srv.items() if n <= HIST_MAX and n > pc.get(r, 0) and not any(x in r.split("/")[0] for x in HIST_SKIP)]
    skipped = []
    if DRY:
        changes.append(f"Verlaeufe: {len(to_srv)} zum Server, {len(to_pc)} zum PC (Trockenlauf)")
        return
    if to_srv:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tf:
            for r in to_srv:
                data = open(os.path.join(base, r.replace("/", os.sep)), "rb").read()
                if SECRET_RE.search(data):
                    skipped.append(r)
                    continue
                ti = tarfile.TarInfo(".claude/projects/" + r); ti.size = len(data); ti.mode = 0o600; ti.mtime = time.time()
                tf.addfile(ti, io.BytesIO(data))
        ssh("mkdir -p ~/.claude/projects && tar -xf - -C ~", data=buf.getvalue(), timeout=600)
    if to_pc:
        data = ssh("tar -cf - -C ~/.claude/projects -T -", data="\n".join("./" + r for r in to_pc).encode(), binary=True, timeout=600)
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            for m in tf.getmembers():
                if not m.isfile() or ".." in m.name.split("/"):
                    continue
                raw = tf.extractfile(m).read()
                if SECRET_RE.search(raw):
                    skipped.append(m.name)
                    continue
                dest = os.path.join(base, (m.name[2:] if m.name.startswith("./") else m.name).replace("/", os.sep))
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                open(dest, "wb").write(raw)
    changes.append(f"Verlaeufe abgeglichen: {len(to_srv)} zum Server, {len(to_pc)} zum PC" + (f"; {len(skipped)} wegen Schluesselmustern uebersprungen" if skipped else ""))


def main():
    try:
        st = json.load(open(STATE, encoding="utf-8"))
    except Exception:
        st = {"base": {}, "last": time.time() - 86400}
    base, changes, conflicts = st.get("base", {}), [], []
    try:
        push_config(changes)
        sync_global(st, changes)
        sync_mcp(changes)
        sync_history(changes)
        srv = json.loads(ssh(SRV_LIST))
    except Exception as e:
        log(f"Server nicht erreichbar: {e}")
        return 0
    pc = pc_files()
    if not base:                                              # erster Lauf: PC ist fuehrend, Server-Stand gilt als Basis
        base = dict(srv)
    pull, push = [], []
    for rel in set(pc) | set(srv):
        p, s, b = pc.get(rel), srv.get(rel), base.get(rel)
        if p == s:
            continue
        if s and (p is None and b is None or p == b):        # nur Server geaendert / neu auf Server
            pull.append(rel)
        elif p and (s == b or s is None):                     # nur PC geaendert / neu auf PC
            push.append(rel)
        elif p and s:                                         # beide geaendert
            conflicts.append(rel)
    if not DRY:
        if push:
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tf:
                for rel in push:
                    tf.add(os.path.join(PC, rel), arcname=rel, recursive=False)
            ssh(f"mkdir -p {SRV} && tar -xf - -C {SRV}", data=buf.getvalue())
        getl = pull + conflicts
        if getl:
            data = ssh(f"tar -cf - -C {SRV} -T -", data="\n".join(getl).encode(), binary=True)
            with tarfile.open(fileobj=io.BytesIO(data)) as tf:
                for m in tf.getmembers():
                    if not m.isfile() or ".." in m.name.split("/"):
                        continue
                    dest = os.path.join(PC, m.name.replace("/", os.sep)) + (".server-konflikt" if m.name in conflicts else "")
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    open(dest, "wb").write(tf.extractfile(m).read())
        new_base = {**{k: v for k, v in pc.items()}, **{k: srv[k] for k in pull}}
        for k in push:
            new_base[k] = pc[k]
        for k in conflicts:
            new_base[k] = base.get(k, "")
        st["base"] = new_base
    try:
        rep = json.loads(ssh(REPORT_CMD % st.get("last", time.time() - 86400)))
    except Exception as e:
        rep = {"fehler": str(e)[:200]}
    if not DRY:
        changes += git_publish(pull)
    if not DRY:
        st["last"] = time.time()
        json.dump(st, open(STATE, "w", encoding="utf-8"))
        write_report(rep, changes, pull, push, conflicts)
    log(f"OK geholt={len(pull)} gesendet={len(push)} konflikte={len(conflicts)} config={len(changes)}")
    print(f"geholt {len(pull)}, gesendet {len(push)}, Konflikte {len(conflicts)}, Regeln {len(changes)}")
    if not DRY:
        try:
            subprocess.run([sys.executable, "-I", os.path.join(os.path.dirname(os.path.abspath(__file__)), "server-spiegel.py")], capture_output=True, timeout=400)
        except Exception as e:
            log(f"Vollspiegel fehlgeschlagen: {e!r}")
        try:                       # committete Staende aufs System bringen (nur wenn die Auto-Deploy-Regel eingerichtet ist)
            subprocess.run([sys.executable, "-I", os.path.join(os.path.dirname(os.path.abspath(__file__)), "deploy.py"), "--quiet"], capture_output=True, timeout=300)
        except Exception as e:
            log(f"Auto-Deploy fehlgeschlagen: {e!r}")
    return 0


def write_report(rep, changes, pull, push, conflicts):
    now = time.strftime("%Y-%m-%d %H:%M")
    lines = [f"## {now}"]
    if rep.get("fehler"):
        lines.append(f"- Bericht fehlgeschlagen: {rep['fehler']}")
    else:
        lines.append(f"- Server: {rep.get('laufzeit','?')}, Dienste (web, agent, claude, docker, backup-timer): {rep.get('dienste','?')}")
        lines.append(f"- Platte: {rep.get('platte','?')}; Backup-Platte: {rep.get('backup_platte','?')}; {rep.get('letztes_backup','')}")
        if rep.get("bibliothek_neu_anzahl"):
            lines.append(f"- Neu/geändert in der Bibliothek: {rep['bibliothek_neu_anzahl']} — " + ", ".join(f"`{x}`" for x in rep["bibliothek_neu"][:15]))
        seen = set()                # gleiche Startsaetze nur einmal (Librarian-Laeufe wiederholen sich)
        for s in rep.get("claude_sitzungen", []):
            if s["start"] in seen or len(seen) >= 3:
                continue
            seen.add(s["start"])
            lines.append(f"- Claude auf dem Server {s['zeit']}: „{s['start'][:60]}“")
    for label, items in (("Vom Server geholt", pull), ("Zum Server gesendet", push)):
        if items:
            more = f" (+{len(items) - 5} weitere)" if len(items) > 5 else ""
            lines.append(f"- {label} ({len(items)}): " + ", ".join(f"`{x}`" for x in items[:5]) + more)
    for x in conflicts:
        lines.append(f"- **Konflikt** (beide geändert): `{x}` → Serverfassung liegt als `.server-konflikt` daneben")
    lines += [f"- {c}" for c in changes]
    if len(lines) == 1:
        lines.append("- Nichts Neues.")
    head = "---\ntyp: abgleich\nquelle: claude-abgleich.py (stündlich)\ndatenklasse: B\n---\n# Server-Abgleich\nÜbergeordnet: [[MA-Server Zentrale]] · [[Verbundene-Dienste]] · [[Index]]\n\n"
    old = ""
    if os.path.exists(VAULT_REPORT):
        old = open(VAULT_REPORT, encoding="utf-8").read()
        old = old.split("\n## ", 1)[1] if "\n## " in old else ""
        old = "## " + old if old else ""
    blocks = ("\n".join(lines) + "\n\n" + old).split("\n## ")
    text = head + "\n## ".join(blocks[:12])
    open(VAULT_REPORT, "w", encoding="utf-8").write(text.rstrip() + "\n")


if __name__ == "__main__":
    sys.exit(main())
