#!/bin/bash
# JARVIS V16 zurücknehmen - ohne sudo. Daten (Aufträge, Ergebnisse, Gelerntes) bleiben IMMER erhalten.
#   bash rollback-v16.sh               vorherigen GETESTETEN Release aktivieren (.release-status = tests-ok)
#   bash rollback-v16.sh --to NAME     bestimmten Release aktivieren (Ordnername unter ~/.local/share/ma-jarvis/releases);
#                                      nur tests-ok, sonst zusätzlich --force
#   bash rollback-v16.sh --stop        JARVIS anhalten: Cron-Takt entfernen + globaler Not-Aus (KILL-Datei)
#   bash rollback-v16.sh --start       Cron-Takt wieder eintragen und Not-Aus aufheben (install-v16.sh --cron-only)
set -Eeuo pipefail
BASE="$HOME/.local/share/ma-jarvis"; CFG="$HOME/.config/ma-jarvis/jarvis.json"; DATA="/srv/ma-home/library/.jarvis/v16"
case "${1:-}" in
  --stop)
    ( crontab -l 2>/dev/null | grep -v 'ma-jarvis/current/brain-runtime/jarvis_cli.py' || true ) | crontab -
    date '+%F %T Not-Aus durch rollback-v16.sh --stop' > "$DATA/KILL"
    echo "JARVIS angehalten (Cron entfernt, $DATA/KILL gesetzt). Laufende Schritte enden spätestens nach ihrem Zeitlimit."; exit 0;;
  --start)
    rm -f "$DATA/KILL"; D="$(cd "$(dirname "$0")" && pwd)"; exec bash "$D/install-v16.sh" --cron-only;;
  --to)
    TARGET="$BASE/releases/${2:?Release-Name fehlt}"
    st="$(cut -d' ' -f1 "$TARGET/.release-status" 2>/dev/null || echo unbekannt)"
    if [ "$st" != tests-ok ] && [ "${3:-}" != --force ]; then
      echo "Release $2 hat Status '$st' (nicht tests-ok) - abgelehnt. Nur mit --force."; exit 1
    fi;;
  "")
    CUR="$(readlink -f "$BASE/current")"; TARGET=""
    for r in $(ls -1d "$BASE/releases/"*/ | sed 's:/$::' | sort -r); do
      [ "$r" = "$CUR" ] && continue
      [ "$(cut -d' ' -f1 "$r/.release-status" 2>/dev/null)" = tests-ok ] && { TARGET="$r"; break; }
    done
    [ -n "$TARGET" ] || { echo "Kein anderer getesteter Release (tests-ok) vorhanden."; exit 1; };;
  *) echo "Unbekannte Option"; exit 2;;
esac
[ -d "$TARGET" ] || { echo "Kein Release $TARGET"; exit 1; }
ln -sfn "$TARGET" "$BASE/current.new" && mv -T "$BASE/current.new" "$BASE/current"
echo "Aktiv: $(readlink "$BASE/current") ($(cat "$BASE/current/.release-status" 2>/dev/null || echo 'ohne Status'))"
python3 "$BASE/current/brain-runtime/jarvis_cli.py" --config "$CFG" doctor | python3 -c "import json,sys; d=json.load(sys.stdin); print('doctor ok:', d['ok'])"
