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
    }
    have = json.loads(ssh(HAVE_CMD % json.dumps(list(want))))
    send = {p: b for p, b in want.items() if hashlib.sha1(b).hexdigest() != have.get(p)}
    if send and not DRY:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tf:
            for p, b in send.items():
                ti = tarfile.TarInfo(p); ti.size = len(b); ti.mode = 0o755 if p.endswith(".py") else 0o644; ti.mtime = time.time()
                tf.addfile(ti, io.BytesIO(b))
        ssh("mkdir -p ~/.claude/hooks && tar -xf - -C ~", data=buf.getvalue())
    changes += [f"Regeln/Einstellung zum Server: {p}" for p in send]


def main():
    try:
        st = json.load(open(STATE, encoding="utf-8"))
    except Exception:
        st = {"base": {}, "last": time.time() - 86400}
    base, changes, conflicts = st.get("base", {}), [], []
    try:
        push_config(changes)
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
    if pull and not DRY:
        subprocess.run(["git", "-C", PC, "add", "-A"], capture_output=True)
        r = subprocess.run(["git", "-C", PC, "-c", "core.safecrlf=false", "commit", "-q", "-m", "Automatischer Abgleich: Aenderungen vom Server"], capture_output=True)
        if r.returncode == 0:
            subprocess.run(["git", "-C", PC, "push", "-q"], capture_output=True, timeout=120)
    if not DRY:
        st["last"] = time.time()
        json.dump(st, open(STATE, "w", encoding="utf-8"))
        write_report(rep, changes, pull, push, conflicts)
    log(f"OK geholt={len(pull)} gesendet={len(push)} konflikte={len(conflicts)} config={len(changes)}")
    print(f"geholt {len(pull)}, gesendet {len(push)}, Konflikte {len(conflicts)}, Regeln {len(changes)}")
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
        for s in rep.get("claude_sitzungen", [])[:8]:
            lines.append(f"- Claude auf dem Server {s['zeit']}: „{s['start']}“")
    for x in pull:
        lines.append(f"- Vom Server geholt: `{x}`")
    for x in push:
        lines.append(f"- Zum Server gesendet: `{x}`")
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
    text = head + "\n## ".join(blocks[:48])
    open(VAULT_REPORT, "w", encoding="utf-8").write(text.rstrip() + "\n")


if __name__ == "__main__":
    sys.exit(main())
