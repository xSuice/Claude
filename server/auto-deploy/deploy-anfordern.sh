#!/bin/bash
# Ohne sudo als andrew (auch fuer Claude): fordert die Auto-Einspielung an und zeigt das Ergebnis.
#   bash ~/MA-Server/server/auto-deploy/deploy-anfordern.sh
# Voraussetzung: einmalig von Philipp installiert (server/auto-deploy/install.sh).
Q=/srv/ma-home/deploy
[ -d "$Q" ] && systemctl is-active --quiet ma-deploy.path 2>/dev/null || { echo "Auto-Einspielung ist nicht installiert (sudo bash ~/MA-Server/server/auto-deploy/install.sh)."; exit 1; }
before=$(stat -c %Y "$Q/status.txt" 2>/dev/null || echo 0)
touch "$Q/request"
for i in $(seq 1 60); do
  sleep 2
  now=$(stat -c %Y "$Q/status.txt" 2>/dev/null || echo 0)
  if [ ! -e "$Q/request" ] && [ "$now" -gt "$before" ]; then cat "$Q/status.txt"; exit 0; fi
done
echo "Keine Rueckmeldung nach 2 Minuten. Siehe /var/log/ma-deploy.log"
exit 1
