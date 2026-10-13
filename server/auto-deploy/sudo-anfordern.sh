#!/bin/bash
# Ohne sudo als andrew (auch fuer Claude): fuehrt ein Skript als root aus, wenn der Admin-Schalter "Sudo-Skripte erlauben (Root)" an ist.
#   bash ~/MA-Server/server/auto-deploy/sudo-anfordern.sh /pfad/zum/skript.sh
# Voraussetzung: einmalig von Philipp installiert (server/auto-deploy/sudo-einrichten.sh). Ergebnis steht in /srv/ma-home/deploy-sudo/ergebnis.txt.
Q=/srv/ma-home/deploy-sudo
S="${1:-}"
[ -n "$S" ] && [ -f "$S" ] || { echo "Aufruf: sudo-anfordern.sh /pfad/zum/skript.sh"; exit 2; }
[ -d "$Q" ] && systemctl is-active --quiet ma-sudo.path 2>/dev/null || { echo "Sudo-Freigabe ist nicht installiert (sudo bash ~/MA-Server/server/auto-deploy/sudo-einrichten.sh)."; exit 1; }
NAME=$(basename "$S")
case "$NAME" in *[!A-Za-z0-9._-]*|.*|'') echo "Dateiname nur A-Z a-z 0-9 . _ - erlaubt."; exit 2 ;; esac
case "$NAME" in *.sh) ;; *) echo "Nur *.sh."; exit 2 ;; esac
before=$(stat -c %Y "$Q/ergebnis.txt" 2>/dev/null || echo 0)
cp -f "$S" "$Q/$NAME" || { echo "Kann $Q/$NAME nicht schreiben (Bruecke neu starten? ReadWritePaths)."; exit 1; }
printf '%s\n' "$NAME" > "$Q/request" || { echo "Kann request nicht anlegen."; exit 1; }
for i in $(seq 1 900); do
  sleep 2
  now=$(stat -c %Y "$Q/ergebnis.txt" 2>/dev/null || echo 0)
  if [ ! -e "$Q/request" ] && [ "$now" -gt "$before" ]; then cat "$Q/ergebnis.txt"; exit 0; fi
done
echo "Keine Rueckmeldung nach 30 Minuten. Siehe /var/log/ma-sudo/ma-sudo.log"
exit 1
