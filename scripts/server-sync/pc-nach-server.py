#!/usr/bin/env python3
"""Alles vom PC zusaetzlich auf den MA-Server (nur senden, nie loeschen):
 1. Vault-Dateien ausser Notizen (PDF, Bilder, Videos, Archive ...) -> /srv/ma-home/library/vault-dateien/<gleicher Pfad>
 2. Extras -> /srv/ma-home/library/pc-kopie/<Name>: MA-Automation (ohne logs/state/backups), VaultBackup-Protokolle, Claude-Skills/Einstellungen (ohne Schluessel)
Inkrementell (Groesse+Zeit), Pakete von ca. 400 MB, Sperrdatei gegen doppelten Lauf. Log: ~/.claude/state/pc-nach-server.log
Aufruf: python pc-nach-server.py [--dry]"""
import json
import os
import subprocess
import sys
import tarfile
import time

HOST = "ma-server"
VAULT = r"C:\Users\andre\Documents\Obsidian Vault"
DEST_V = "/srv/ma-home/library/vault-dateien"
DEST_X = "/srv/ma-home/library/pc-kopie"
STATE = os.path.expanduser("~/.claude/state/pc-nach-server.json")
LOCK = os.path.expanduser("~/.claude/state/pc-nach-server.lock")
LOG = os.path.expanduser("~/.claude/state/pc-nach-server.log")
SKIP_DIRS = {".obsidian", ".smart-connections", ".smart-env", ".trash", ".git", "node_modules", "__pycache__"}
NOTE_EXT = (".md", ".base", ".canvas")
SECRET_HINT = ("token", "passwort", "password", "apikey", "api-key", "secret", ".key", ".pem", ".env", "credential", "recovery_codes")
BATCH = 400 * 1024 * 1024
DRY = "--dry" in sys.argv

EXTRAS = [  # (Name, Wurzel, Ausschluss-Ordner)
    ("MA-Automation", r"C:\Users\andre\MA-Automation", {"logs", "state", "backups", "staging"}),
    ("Claude-Skills", r"C:\Users\andre\.claude\skills", set()),
]


def log(m):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "a", encoding="utf-8").write(time.strftime("%Y-%m-%d %H:%M:%S ") + m + "\n")


def scan(root, skip, vault=False):
    out = {}
    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and d not in skip]
        for f in files:
            low = f.lower()
            if (vault and low.endswith(NOTE_EXT)) or any(h in low for h in SECRET_HINT):
                continue
            p = os.path.join(r, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            out[p] = (int(st.st_mtime), st.st_size)
    return out


def send(base_local, base_remote, paths):
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST, f"mkdir -p '{base_remote}' && tar -xf - -C '{base_remote}'"]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        with tarfile.open(fileobj=p.stdin, mode="w|", format=tarfile.PAX_FORMAT, encoding="utf-8") as tf:
            for path in paths:
                try:
                    tf.add(path, arcname=os.path.relpath(path, base_local).replace("\\", "/"), recursive=False)
                except (OSError, ValueError):
                    pass
        p.stdin.close()
        err = p.stderr.read().decode("utf-8", "replace")
        return p.wait() == 0, err[:200]
    except Exception as e:
        return False, repr(e)


def main():
    if os.path.exists(LOCK) and time.time() - os.path.getmtime(LOCK) < 6 * 3600:
        log("laeuft schon, uebersprungen")
        return 0
    open(LOCK, "w").write(str(os.getpid()))
    try:
        try:
            state = json.load(open(STATE, encoding="utf-8"))
        except Exception:
            state = {}
        jobs = [("vault", VAULT, DEST_V, set(), True)] + [(n, r, f"{DEST_X}/{n}", s, False) for n, r, s in EXTRAS if os.path.isdir(r)]
        total_sent = 0
        for name, root, remote, skip, vault in jobs:
            cur = scan(root, skip, vault)
            seen = state.setdefault(name, {})
            todo = [p for p, v in cur.items() if seen.get(p) != list(v)]
            print(f"{name}: {len(cur)} Dateien, {len(todo)} neu/geaendert, {sum(cur[p][1] for p in todo) / 1e9:.2f} GB")
            if DRY or not todo:
                continue
            batch, size = [], 0
            groups = []
            for p in sorted(todo):
                batch.append(p); size += cur[p][1]
                if size >= BATCH or len(batch) >= 4000:
                    groups.append(batch); batch, size = [], 0
            if batch:
                groups.append(batch)
            for g in groups:
                open(LOCK, "w").write(str(os.getpid()))
                ok, err = send(root, remote, g)
                if not ok:
                    log(f"FEHLER {name}: {err}")
                    json.dump(state, open(STATE, "w", encoding="utf-8"))
                    return 1
                for p in g:
                    seen[p] = list(cur[p])
                total_sent += len(g)
                json.dump(state, open(STATE, "w", encoding="utf-8"))
        log(f"OK {total_sent} Dateien gesendet")
        return 0
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
