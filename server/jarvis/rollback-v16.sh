#!/bin/bash
# JARVIS V16 zurücknehmen - ohne sudo. Daten (Aufträge, Ergebnisse, Gelerntes) bleiben IMMER erhalten.
#   bash rollback-v16.sh               vorherigen Release aktivieren
#   bash rollback-v16.sh --to NAME     bestimmten Release aktivieren (Ordnername unter ~/.local/share/ma-jarvis/releases)
#   bash rollback-v16.sh --stop        JARVIS anhalten: Cron-Takt entfernen + globaler Not-Aus (KILL-Datei)
#   bash rollback-v16.sh --start       Cron-Takt wieder eintragen und Not-Aus aufheben (über install-v16.sh --skip-tests)
set -Eeuo pipefail
BASE="$HOME/.local/share/ma-jarvis"; CFG="$HOME/.config/ma-jarvis/jarvis.json"; DATA="/srv/ma-home/library/.jarvis/v16"
case "${1:-}" in
  --stop)
    ( crontab -l 2>/dev/null | grep -v 'ma-jarvis/current/brain-runtime/jarvis_cli.py' || true ) | crontab -
    date '+%F %T Not-Aus durch rollback-v16.sh --stop' > "$DATA/KILL"
    echo "JARVIS angehalten (Cron entfernt, $DATA/KILL gesetzt). Laufende Schritte enden spätestens nach ihrem Zeitlimit."; exit 0;;
  --start)
    rm -f "$DATA/KILL"; exec bash "$HOME/MA-Server/server/jarvis/install-v16.sh" --skip-tests;;
  --to)
    TARGET="$BASE/releases/${2:?Release-Name fehlt}";;
  "")
    CUR="$(readlink -f "$BASE/current")"
    TARGET="$(ls -1d "$BASE/releases/"*/ | sed 's:/$::' | grep -v -x "$CUR" | tail -1)";;
  *) echo "Unbekannte Option"; exit 2;;
esac
[ -d "$TARGET" ] || { echo "Kein Release $TARGET"; exit 1; }
ln -sfn "$TARGET" "$BASE/current.new" && mv -T "$BASE/current.new" "$BASE/current"
echo "Aktiv: $(readlink "$BASE/current")"
python3 "$BASE/current/brain-runtime/jarvis_cli.py" --config "$CFG" doctor | python3 -c "import json,sys; d=json.load(sys.stdin); print('doctor ok:', d['ok'])"
