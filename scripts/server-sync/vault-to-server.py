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
    """Prueft ob der Server die fuehrende Kopie ist (server-master-Flag).

    Drei-Zustands-Rueckgabe (Sicherheitsluecke 1, 2026-10-20):
    - True: Flag existiert definitiv.
    - False: Flag existiert definitiv NICHT (Verbindung stand, kein Flag).
    - None: UNBEKANNT (Verbindungsfehler -- Flag-Status konnte nicht
      ermittelt werden). Der Aufrufer MUSS dann abbrechen, NICHT in den
      Mirror-Modus zurueckfallen (sonst werden veraenderte Serverdateien
      still ueberschrieben -- der Grund fuer diese Luecke).
    """
    try:
        out = ssh_out(f"[ -f '{FLAG}' ] && echo 1 || echo 0").strip()
        return {"0": False, "1": True}.get(out)
    except Exception:
        return None  # UNBEKANNT, nicht False (Verbindungsfehler != Flag fehlt).


def server_listing():
    out = {}
    # Do not mask find/permission failures as a successful partial listing.
    for line in ssh_out(f"if [ -d '{DEST}' ]; then find '{DEST}' -type f -printf '%P\\t%T@\\t%s\\n'; else exit 1; fi").splitlines():
        p, t, s = line.split("\t")
        if (not p or p in out or "\\" in p or ":" in p
                or any(part in ("", ".", "..") for part in p.split("/"))
                or any(ord(c) < 32 for c in p)):
            raise ValueError("Invalid or duplicate listing path")
        mt, size = int(float(t)), int(s)
        if size < 0:
            raise ValueError("Negative listing size")
        out[p] = (mt, size)
    return out


def divert(todo, old, srv):
    """Hauptkopie-Modus: Textnotizen, die auf dem Server seit dem letzten Abgleich geaendert wurden, werden hier NICHT ueberschrieben.
    Sicherheitsluecke 2 (2026-10-20): eine Datei die auf dem Server existiert
    aber NICHT im alten STATE steht (neu/unbekannt), wird ebenfalls NICHT
    ueberschrieben -- sie geht nach Review als '(PC-Änderung)', damit die
    Serverfassung erhalten bleibt. Vorher: wurde die Serverfassung still
    ueberschrieben, weil `changed_on_server` nur Dateien schuetzte die im
    STATE bekannt waren.
    Rueckgabe: (normal senden, als Kopie in 00 Inbox/Review auf den Server legen)."""
    send, copies = [], []
    for k in todo:
        s, b = srv.get(k), old.get(k)
        # Geaendert auf dem Server seit letztem STATE?
        changed_on_server = bool(s and b and not (s[0] <= b[0] + 2 and s[1] == b[1]))
        # NEU (Luecke 2): existiert auf dem Server, ist aber NICHT im STATE
        # (unbekannte neue Datei) -> ebenfalls schuetzen, nicht ueberschreiben.
        new_on_both_sides = bool(s and not b)
        if (changed_on_server or new_on_both_sides) and k.lower().endswith(EXT):
            copies.append(k)
        else:
            send.append(k)
    return send, copies


def main():
    full = "--full" in sys.argv
    dry = "--dry" in sys.argv
    try:
        with open(STATE, encoding="utf-8") as fh:
            old = json.load(fh)
    except Exception:
        old = {}
    cur = scan()
    todo = [k for k, v in cur.items() if full or old.get(k) != v]
    copies = []
    if todo and not dry:
        master = master_on()
        if master is None:
            # SICHERHEITSLUECKE 1 (2026-10-20): Verbindungsfehler bei der
            # Flag-Pruefung -> UNBEKANNT, nicht False. Frueher wurde still in
            # den Mirror-Modus zurueckgefallen und veraenderte Serverdateien
            # wurden ueberschrieben. Jetzt: hart abbrechen, nichts gesendet.
            log("Hauptkopie-Pruefung fehlgeschlagen (Verbindungsfehler), NICHTS gesendet: Flag-Status unbekannt, kein Mirror-Modus-Fallback.")
            print("FEHLER: server-master-Flag konnte nicht geprueft werden (Verbindungsfehler). Abbruch, nichts gesendet.")
            return 1
        if master:
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
    # Review copies did not update the original remote path. Keep its old
    # baseline (also in --full), never acknowledge the unsent local edit.
    synced = dict(cur)
    for k in copies:
        if k in old:
            synced[k] = old[k]
        else:
            synced.pop(k, None)
    with open(STATE, "w", encoding="utf-8") as state_file:
        json.dump(synced, state_file)
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
