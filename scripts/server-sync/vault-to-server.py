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
ATT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".pdf")   # Anhaenge fuer die Vault-Ansicht im Portal (nur PC -> Server, bis 8 MB je Datei)
ATT_MAX = 8 * 1024 * 1024
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
            if not low.endswith(EXT + ATT) or any(h in low for h in SECRET_HINT):
                continue
            p = os.path.join(root, n)
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_size > MAXSIZE or (low.endswith(ATT) and st.st_size > ATT_MAX):
                continue
            out[os.path.relpath(p, VAULT).replace("\\", "/")] = [int(st.st_mtime), st.st_size]
    return out


FLAG = "/srv/ma-home/library/.jarvis/server-master"      # Datei auf dem Server: der Server ist die Hauptkopie des Vaults


def ssh_out(cmd):
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST, cmd], capture_output=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace")[:200])
    return r.stdout.decode("utf-8", "replace")


def master_on():
    try:
        return ssh_out(f"[ -f '{FLAG}' ] && echo 1 || echo 0").strip() == "1"
    except Exception:
        return False


def server_listing():
    out = {}
    for line in ssh_out(f"[ -d '{DEST}' ] && find '{DEST}' -type f -printf '%P\\t%T@\\t%s\\n' || true").splitlines():
        try:
            p, t, s = line.split("\t")
            out[p] = (int(float(t)), int(s))
        except ValueError:
            pass
    return out


def divert(todo, old, srv):
    """Hauptkopie-Modus: Textnotizen, die auf dem Server seit dem letzten Abgleich geaendert wurden, werden hier NICHT ueberschrieben.
    Rueckgabe: (normal senden, als Kopie in 00 Inbox/Review auf den Server legen)."""
    send, copies = [], []
    for k in todo:
        s, b = srv.get(k), old.get(k)
        changed_on_server = bool(s and b and not (s[0] <= b[0] + 2 and s[1] == b[1]))
        (copies if changed_on_server and k.lower().endswith(EXT) else send).append(k)
    return send, copies


def main():
    full = "--full" in sys.argv
    dry = "--dry" in sys.argv
    try:
        old = {} if full else json.load(open(STATE, encoding="utf-8"))
    except Exception:
        old = {}
    cur = scan()
    todo = [k for k, v in cur.items() if old.get(k) != v]
    copies = []
    if todo and not dry and master_on():
        try:
            todo, copies = divert(todo, old, server_listing())
        except Exception as e:
            log(f"Hauptkopie-Pruefung fehlgeschlagen, nichts gesendet: {e}")
            return 1
    print(f"{len(cur)} Dateien, {len(todo)} neu/geaendert, {len(copies)} als PC-Aenderung nach Review")
    if dry or not (todo or copies):
        if not (todo or copies):
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
            for k in copies:                               # PC-Fassung als Kopie in den Review-Ordner des Servers, die Serverfassung bleibt
                n, e = os.path.splitext(os.path.basename(k))
                tf.add(os.path.join(VAULT, k), arcname="00 Inbox/Review/" + n + " (PC-Änderung)" + e, recursive=False)
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
