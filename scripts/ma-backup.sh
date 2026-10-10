#!/bin/bash
# MA Home: verschluesseltes Backup (restic) auf ein EXTERNES Ziel. Kein Ziel eingebaut.
# Voraussetzung: /etc/ma-home/backup.env (root:root 600) mit
#   RESTIC_REPOSITORY=<externes Ziel>      RESTIC_PASSWORD_FILE=/etc/ma-home/backup.pass
# Aufruf:  sudo ma-backup.sh run | check | restore-test
# Ein Repository auf demselben Datentraeger wie / oder /srv gilt NICHT als Backup und wird abgelehnt.
set -Eeuo pipefail
umask 077
ENV=/etc/ma-home/backup.env
STATUS=/srv/ma-home/backup-status.json
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
[ -r "$ENV" ] || { echo "Kein Backupziel konfiguriert ($ENV fehlt). Siehe BACKUP-RESTORE.md."; exit 1; }
set -a; . "$ENV"; set +a
: "${RESTIC_REPOSITORY:?Ziel fehlt}" "${RESTIC_PASSWORD_FILE:?Passwortdatei fehlt}"
[ -r "$RESTIC_PASSWORD_FILE" ] || { echo "Passwortdatei nicht lesbar"; exit 1; }

status() { printf '{"state": "%s", "time": "%s"}\n' "$1" "$(date -u +%FT%TZ)" >"$STATUS"; }
trap 'status "FEHLGESCHLAGEN: ${BASH_COMMAND:0:60}"; echo "Backup fehlgeschlagen." >&2' ERR

disk_of() { lsblk -no PKNAME "$(findmnt -no SOURCE -T "$1")" 2>/dev/null | head -1; }
case "$RESTIC_REPOSITORY" in
  /*)  # lokaler Pfad: muss auf anderem physischem Datentraeger liegen
       if [ "$(disk_of "$RESTIC_REPOSITORY")" = "$(disk_of /srv/ma-home)" ]; then
         echo "ABGELEHNT: Ziel liegt auf demselben Datentraeger wie die Daten (kein Schutz vor Plattenausfall)."; exit 1
       fi ;;
esac

DUMP=/srv/ma-home/backup-dumps
case "${1:-}" in
  run)
    rm -rf "$DUMP"; install -d -m 700 "$DUMP"
    # Konsistente SQLite-Kopien (Online-Backup-API), statt laufende WAL-Dateien zu kopieren
    python3 - "$DUMP" <<'PY'
import sqlite3, sys, pathlib
dump = pathlib.Path(sys.argv[1])
root = pathlib.Path('/srv/ma-home')
for src in list(root.glob('*/*.sqlite*')) + list(root.glob('*/*.db')):
    if 'backup-dumps' in src.parts: continue
    try:
        con = sqlite3.connect(f'file:{src}?mode=ro', uri=True)
        out = sqlite3.connect(dump / (src.parent.name + '__' + src.name))
        con.backup(out); out.close(); con.close()
        print('dump', src)
    except sqlite3.Error as e:
        print('WARNUNG', src, e)
PY
    restic backup --tag ma-home --one-file-system \
      --exclude /srv/ma-home/previews --exclude /srv/ma-home/jobs --exclude /srv/ma-home/backups \
      /srv/ma-home /etc/ma-home
    restic forget --tag ma-home --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune
    rm -rf "$DUMP"
    restic check --read-data-subset=2%
    status "OK (Backup + Stichproben-Check)"
    echo "Backup OK. Wiederherstellbarkeit erst nach 'restore-test' belegt." ;;
  check)
    restic check --read-data-subset=10% && status "OK (Check)" ;;
  restore-test)
    T=$(mktemp -d /tmp/ma-restore.XXXXXX); trap 'rm -rf "$T"' EXIT
    restic restore latest --tag ma-home --target "$T" --include /etc/ma-home/host.json --include /srv/ma-home/backup-dumps
    [ -s "$T/etc/ma-home/host.json" ] && echo "host.json wiederhergestellt"
    for db in "$T"/srv/ma-home/backup-dumps/*; do
      [ -e "$db" ] && python3 -c 'import sqlite3,sys;print(sys.argv[1].split("/")[-1], sqlite3.connect(sys.argv[1]).execute("pragma integrity_check").fetchone())' "$db"
    done
    echo "Restore-Test beendet (Zielordner wird geloescht; Produktivdaten unberuehrt)." ;;
  *) echo "Aufruf: $0 run|check|restore-test"; exit 1 ;;
esac
