#!/usr/bin/env python3
"""Neues vom MA-Server in den Obsidian-Vault holen (ohne Modell, kein Claude):
 1. Aenderungen an Notizen im Server-Spiegel (/srv/ma-home/library/vault-notizen) -> Vault, nur wenn lokal seit dem letzten Abgleich unveraendert.
    Sonst Konflikt: Serverfassung landet als "<Name> (Server-Konflikt).md" in 00 Inbox/Review, nichts wird ueberschrieben.
 2. Neue Textdateien (.md .txt) im Server-Eingang (/srv/ma-home/library/inbox) -> 00 Inbox/Server-Eingang (Autopflege sortiert sie dann).
    Andere Dateien im Eingang werden nur in 00 Inbox/Server-Eingang/Server-Eingang.md aufgelistet und bleiben auf dem Server.
Log: ~/.claude/state/server-sync.log   Aufruf: python server-to-vault.py [--dry]"""
import os, sys, json, subprocess, time, tarfile, io, re

VAULT = r"C:\Users\andre\Documents\Obsidian Vault"
STATE = os.path.expanduser("~/.claude/state/server-sync.json")      # von vault-to-server.py: {rel: [mtime,size]} des zuletzt gesendeten Standes
PULL = os.path.expanduser("~/.claude/state/server-pull.json")
LOG = os.path.expanduser("~/.claude/state/server-sync.log")
HOST = "ma-server"
NOTES = "/srv/ma-home/library/vault-notizen"
INBOX = "/srv/ma-home/library/inbox"
EXT = (".md", ".base", ".canvas")
SKIP_TOP = (".obsidian", ".smart-connections", ".smart-env", ".trash")
MAXSIZE = 20 * 1024 * 1024


def log(m):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "a", encoding="utf-8").write(time.strftime("%Y-%m-%d %H:%M:%S ") + "[pull] " + m + "\n")


def ssh(cmd, binary=False, timeout=120):
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST, cmd], capture_output=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace")[:200])
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def listing(d):
    out = {}
    for line in ssh(f"[ -d '{d}' ] && find '{d}' -type f -printf '%P\\t%T@\\t%s\\n' || true").splitlines():
        try:
            p, t, s = line.split("\t")
            out[p] = (int(float(t)), int(s))
        except ValueError:
            pass
    return out


def fetch(base, names):
    if not names:
        return {}
    data = ssh("tar -cf - -C '%s' -T -  <<'EOL'\n%s\nEOL" % (base, "\n".join(names)), binary=True)
    files = {}
    with tarfile.open(fileobj=io.BytesIO(data)) as tf:
        for m in tf.getmembers():
            if m.isfile():
                files[m.name] = tf.extractfile(m).read()
    return files


def safe(name):
    return re.sub(r'[<>:"|?*]', "_", name)


def main():
    dry = "--dry" in sys.argv
    try:
        sent = json.load(open(STATE, encoding="utf-8"))
    except Exception:
        sent = {}
    try:
        pulled = json.load(open(PULL, encoding="utf-8"))
    except Exception:
        pulled = {}
    try:
        srv = listing(NOTES)
        inbox = listing(INBOX)
    except Exception as e:
        log(f"Server nicht erreichbar: {e}")
        return 0
    take, conflicts = [], []
    for rel, (mt, sz) in srv.items():
        if not rel.lower().endswith(EXT) or rel.split("/")[0] in SKIP_TOP or sz > MAXSIZE:
            continue
        base = sent.get(rel)
        if base and mt <= base[0] + 2 and sz == base[1]:
            continue                               # Server == zuletzt gesendeter Stand
        if pulled.get(rel) == [mt, sz]:
            continue                               # schon geholt
        loc = os.path.join(VAULT, rel.replace("/", os.sep))
        if not os.path.exists(loc):
            take.append(rel); continue
        lst = os.stat(loc)
        if base and int(lst.st_mtime) == base[0] and lst.st_size == base[1]:
            take.append(rel)                       # lokal unveraendert -> Server gewinnt
        else:
            conflicts.append(rel)
    new_in = [r for r, (mt, sz) in inbox.items() if r.lower().endswith((".md", ".txt")) and sz <= MAXSIZE and mt < time.time() - 60]
    other_in = [r for r in inbox if r not in new_in]
    print(f"Notizen vom Server: {len(take)} neu/geaendert, {len(conflicts)} Konflikte; Eingang: {len(new_in)} Text, {len(other_in)} andere")
    if dry:
        return 0
    got = fetch(NOTES, take + conflicts)
    for rel in take:
        if rel in got:
            loc = os.path.join(VAULT, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(loc), exist_ok=True)
            open(loc, "wb").write(got[rel])
            os.utime(loc, (srv[rel][0], srv[rel][0]))
            st = os.stat(loc)
            sent[rel] = [int(st.st_mtime), st.st_size]   # damit vault-to-server es nicht zurueckschickt
            pulled[rel] = [srv[rel][0], srv[rel][1]]
    rev = os.path.join(VAULT, "00 Inbox", "Review")
    for rel in conflicts:
        if rel in got:
            os.makedirs(rev, exist_ok=True)
            n = os.path.splitext(os.path.basename(rel))[0]
            open(os.path.join(rev, safe(n) + " (Server-Konflikt).md"), "wb").write(got[rel])
            pulled[rel] = [srv[rel][0], srv[rel][1]]
    ein = os.path.join(VAULT, "00 Inbox", "Server-Eingang")
    if new_in:
        os.makedirs(ein, exist_ok=True)
        gi = fetch(INBOX, new_in)
        for rel in new_in:
            if rel in gi:
                tgt = os.path.join(ein, safe(os.path.basename(rel)))
                if os.path.exists(tgt):
                    b, e = os.path.splitext(tgt); tgt = f"{b} ({time.strftime('%Y%m%d-%H%M')}){e}"
                open(tgt, "wb").write(gi[rel])
                ssh(f"mkdir -p '{INBOX}/../archive/vom-vault-geholt' && mv -n '{INBOX}/{rel}' '{INBOX}/../archive/vom-vault-geholt/'")
    if other_in:
        os.makedirs(ein, exist_ok=True)
        lines = ["---", "typ: liste", "quelle: MA-Server Eingang", "---", "# Server-Eingang (nicht übernommene Dateien)",
                 "Übergeordnet: [[MA-Server Zentrale]] · [[Übersicht]]", "",
                 f"Stand {time.strftime('%Y-%m-%d %H:%M')}. Diese Dateien liegen im Server-Eingang `{INBOX}` und werden nicht in den Vault kopiert (kein Text).", ""]
        lines += [f"- `{r}` ({inbox[r][1]//1024} KB)" for r in sorted(other_in)]
        open(os.path.join(ein, "Server-Eingang.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump(sent, open(STATE, "w", encoding="utf-8"))
    json.dump(pulled, open(PULL, "w", encoding="utf-8"))
    log(f"OK geholt={len(take)} konflikte={len(conflicts)} eingang_text={len(new_in)} eingang_andere={len(other_in)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
