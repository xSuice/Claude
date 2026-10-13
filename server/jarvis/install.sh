#!/bin/bash
# Auf dem MA-Server:  sudo bash ~/MA-Server/server/jarvis/install.sh
# Richtet den Zeitplan fuer Jarvis ein (als Benutzer andrew, ohne Root-Rechte der Jobs), in /etc/cron.d/ma-jarvis:
#   18:30 taeglich  Lern-Impuls   (scripts/server-sync/lern-impuls.py: drei Lernfragen aus deinen Notizen, Haiku, ohne Werkzeuge)
#   06:50 taeglich  Fristen als Kalenderdatei (scripts/server-sync/fristen-ics.py -> Bibliothek/fristen.ics)
# Morgenbrief (06:55) und Fristen-Erinnerung (07:30, 17:30) werden nur ergaenzt, wenn sie nicht schon in der Crontab von andrew stehen.
# Rueckgaengig: sudo rm /etc/cron.d/ma-jarvis
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
P=/home/andrew/MA-Server
A="$P/scripts/automations.py"
# Die Zeitplaene kommen aus server/automations.json (eine Quelle fuer PC und Server); Pruefung der Liste, dann Cron-Zeilen daraus erzeugen.
python3 -I "$A" validate
EXIST="$(crontab -u andrew -l 2>/dev/null || true)"
SKIP=none
while IFS=$'\t' read -r id base; do                                  # schon in der Crontab von andrew vorhanden -> nicht doppelt anlegen
  echo "$EXIST" | grep -qF "$base" && SKIP="$SKIP,$id"
done < <(python3 -I "$A" skripte)
{
  echo '# MA Home Jarvis (siehe server/jarvis/install.sh, Quelle: server/automations.json). Jobs laufen als andrew.'
  echo 'SHELL=/bin/bash'
  echo 'PATH=/usr/local/bin:/usr/bin:/bin'
  python3 -I "$A" cron --user andrew --skip "$SKIP"
} > /etc/cron.d/ma-jarvis.tmp
chmod 644 /etc/cron.d/ma-jarvis.tmp
mv /etc/cron.d/ma-jarvis.tmp /etc/cron.d/ma-jarvis
echo "Eingetragen:"; grep -v '^#' /etc/cron.d/ma-jarvis | grep -v -E '^(SHELL|PATH)='
echo "Bereits in der Crontab von andrew (nicht doppelt eingetragen): ${SKIP#none,}"
echo "Push aufs Handy braucht eine Datei ~/.ntfy-token (nur der ntfy-Token, chmod 600). Ohne sie schreiben die Jobs nur in den Vault."
