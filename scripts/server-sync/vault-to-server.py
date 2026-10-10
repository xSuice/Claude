#!/usr/bin/env python3
"""Vault-Notizen (nur Textnotizen) einseitig auf den MA-Server spiegeln: PC -> Server.
Ziel: /srv/ma-home/library/vault-notizen. Nur geaenderte Dateien (mtime/size), nichts wird auf dem Server geloescht.
Woechentlicher Snapshot (tgz, 4 Stueck) in /srv/ma-home/library/vault-snapshots. Log: ~/.claude/state/server-sync.log
Aufruf: python vault-to-server.py [--full] [--dry]"""
import os, sys, json, subprocess, time, tarfile, io

VAULT = r"C:\Users\andre\Documents\Obsidian Vault"
STATE = os.path.expanduser("~/.claude/state/server-sync.json")
LOG = os.path.expanduser("~/.claude/state/server-sync.log")
HOST = "ma-server"
DEST = "/srv/ma-home/library/vault-notizen"
SNAP = "/srv/ma-home/library/vault-snapshots"
SKIP_DIRS = {".obsidian", ".smart-connections", ".smart-env", ".trash"}
EXT = (".md", ".base", ".canvas")
MAXSIZE = 20 * 1024 * 1024
SECRET_HINT = ("token", "passwort", "password", "apikey", "api-key", "secret", ".key", ".env")


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


def scan():
    out = {}
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for n in files:
            low = n.lower()
            if not low.endswith(EXT) or any(h in low for h in SECRET_HINT):
                continue
            p = os.path.join(root, n)
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_size > MAXSIZE:
                continue
            out[os.path.relpath(p, VAULT).replace("\\", "/")] = [int(st.st_mtime), st.st_size]
    return out


def main():
    full = "--full" in sys.argv
    dry = "--dry" in sys.argv
    try:
        old = {} if full else json.load(open(STATE, encoding="utf-8"))
    except Exception:
        old = {}
    cur = scan()
    todo = [k for k, v in cur.items() if old.get(k) != v]
    print(f"{len(cur)} Dateien, {len(todo)} neu/geaendert")
    if dry or not todo:
        if not todo:
            log("keine Aenderungen")
        return 0
    # Tar-Strom in den ssh-Prozess schreiben (UTF-8-Namen, POSIX-Format)
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST,
           f"mkdir -p '{DEST}' '{SNAP}' && tar -xf - -C '{DEST}'"]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        with tarfile.open(fileobj=p.stdin, mode="w|", format=tarfile.PAX_FORMAT, encoding="utf-8") as tf:
            for k in todo:
                tf.add(os.path.join(VAULT, k), arcname=k, recursive=False)
        p.stdin.close()
        err = p.stderr.read().decode("utf-8", "replace")
        rc = p.wait()
    except Exception as e:
        log(f"FEHLER beim Senden: {e!r}")
        return 1
    if rc != 0:
        log(f"FEHLER ssh/tar rc={rc}: {err[:200]}")
        return 1
    json.dump(cur, open(STATE, "w", encoding="utf-8"))
    log(f"OK {len(todo)} Dateien uebertragen (gesamt {len(cur)})")
    # Wochen-Snapshot, 4 behalten
    wk = time.strftime("%G-W%V")
    snap = (f"[ -f '{SNAP}/vault-{wk}.tgz' ] || (tar -czf '{SNAP}/vault-{wk}.tgz' -C '{DEST}' . "
            f"&& ls -1t '{SNAP}'/vault-*.tgz | tail -n +5 | xargs -r rm --)")
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, snap], capture_output=True, text=True)
    log("Snapshot " + ("ok" if r.returncode == 0 else "FEHLER " + r.stderr[:150]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
