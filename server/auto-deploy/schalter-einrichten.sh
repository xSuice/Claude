#!/bin/bash
# Auf dem MA-Server, EINMAL:  sudo bash ~/MA-Server/server/auto-deploy/schalter-einrichten.sh
# Richtet den Admin-Schalter "Auto-Einspielung erlauben" ein (Checkbox im Portal-Chat, nur fuer Admins):
#   1. Ordner /srv/ma-home/deploy-schalter (root:ma-web, 0775): nur das Portal und root koennen die Schalter-Datei anlegen/loeschen
#   2. Route /api/deploy/switch in portal.py (patch-portal-deployswitch.py, mit Sicherung)
#   3. ma-deploy.sh neu installieren: spielt nur ein, wenn der Schalter an ist (Voreinstellung: AUS)
# Rueckweg: Sicherung /opt/ma-home/portal.py.bak-<Zeit> zurueckkopieren und ma-home-web neu starten; ma-deploy.sh: alte Fassung aus git.
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
D="$(cd "$(dirname "$0")" && pwd)"
bash -n "$D/ma-deploy.sh"
python3 -I -m py_compile "$D/patch-portal-deployswitch.py"
install -d -m 0775 -o root -g ma-web /srv/ma-home/deploy-schalter
# Falls der Portal-Dienst Schreibzugriffe einschraenkt (ProtectSystem): Ordner freigeben ('-' = ohne Fehler, wenn nicht noetig)
install -d /etc/systemd/system/ma-home-web.service.d
printf '[Service]\nReadWritePaths=-/srv/ma-home/deploy-schalter\n' > /etc/systemd/system/ma-home-web.service.d/deploy-schalter.conf
systemctl daemon-reload
python3 -I "$D/patch-portal-deployswitch.py"
install -m 755 -o root -g root "$D/ma-deploy.sh" /usr/local/lib/ma-deploy.sh
systemctl restart ma-home-web; sleep 2
systemctl is-active ma-home-web
echo "Fertig. Schalter ist AUS. Portal neu laden (Strg+F5), Chat oeffnen, Haken bei 'Auto-Einspielung erlauben' setzen (nur Admin)."
