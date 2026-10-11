#!/usr/bin/env python3
"""Spiegelt ALLES Lesbare vom MA-Server auf den PC (nur holen, nichts wird auf dem Server geaendert):
 home/        Skripte und Diagnosen aus ~ (ohne Schluessel), crontab.txt
 bibliothek/  /srv/ma-home/library ohne vault-notizen/vault-snapshots/vault-dateien (laufen ueber eigene Abgleiche, vault-dateien stammt vom PC, 61 GB)
 system/      /etc/systemd/system/ma-*, /usr/local/{sbin,lib}/ma-*, /opt/ma-home/*.py, Dockerfile, /etc/fstab, /etc/udev/rules.d/99-ma-*
 claude-sitzungen/  Sitzungsprotokolle von Claude auf dem Server
Ziel: C:\\Users\\andre\\ServerKopie (ausserhalb des Git-Repos). Geheimnisse (Schluessel, .credentials, /etc/ma-home) werden nie kopiert.
Aufruf: python server-spiegel.py"""
import io
import os
import subprocess
import sys
import tarfile
import time

DEST = r"C:\Users\andre\ServerKopie"
HOST = "ma-server"
LOG = os.path.expanduser("~/.claude/state/server-spiegel.log")

PACK = r"""set -e
T=$(mktemp -d -p /var/tmp); trap 'rm -rf "$T"' EXIT
mkdir -p "$T/home" "$T/bibliothek" "$T/system" "$T/claude-sitzungen"
cp -a ~/*.sh ~/*.py "$T/home/" 2>/dev/null || true
cp -a ~/ma-diag-* ~/rr "$T/home/" 2>/dev/null || true
crontab -l > "$T/home/crontab.txt" 2>/dev/null || true
( cd /srv/ma-home/library && tar -cf - --exclude=./vault-notizen --exclude=./vault-snapshots --exclude=./vault-dateien --exclude=./vault-graph.json . ) | tar -xf - -C "$T/bibliothek" 2>/dev/null || true
for f in /etc/systemd/system/ma-* /usr/local/sbin/ma-* /usr/local/lib/ma-* /opt/ma-home/*.py /opt/ma-home/Dockerfile /etc/fstab /etc/udev/rules.d/99-ma-*; do
  [ -f "$f" ] && [ -r "$f" ] && { mkdir -p "$T/system$(dirname "$f")"; cp -a "$f" "$T/system$f"; }
done
find ~/.claude/projects -name '*.jsonl' -size -20M -exec cp --parents -t "$T/claude-sitzungen" {} + 2>/dev/null || true
find "$T" \( -name '*.key' -o -name '*.pass' -o -name '.credentials*' -o -name '.env*' -o -name '*token*' \) -delete 2>/dev/null || true
tar -cf - -C "$T" .
"""


def log(m):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "a", encoding="utf-8").write(time.strftime("%Y-%m-%d %H:%M:%S ") + m + "\n")


def main():
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST, "bash -s"], input=PACK.encode(), capture_output=True, timeout=300)
    if r.returncode != 0 or not r.stdout:
        log("FEHLER " + r.stderr.decode("utf-8", "replace")[:200])
        return 1
    n = 0
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tf:
        for m in tf.getmembers():
            name = m.name.lstrip("./")
            if not name or ".." in name.split("/") or not (m.isfile() or m.isdir()):
                continue
            target = os.path.join(DEST, name.replace("/", os.sep))
            if m.isdir():
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            data = tf.extractfile(m).read()
            if os.path.exists(target) and open(target, "rb").read() == data:
                continue
            open(target, "wb").write(data)
            n += 1
    log(f"OK {n} Dateien neu/geaendert")
    print(n, "Dateien neu/geändert")
    return 0


if __name__ == "__main__":
    sys.exit(main())
