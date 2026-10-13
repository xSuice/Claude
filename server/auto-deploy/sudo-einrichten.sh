#!/bin/bash
# Auf dem MA-Server, EINMAL:  sudo bash ~/MA-Server/server/auto-deploy/sudo-einrichten.sh
# Richtet die Sudo-Freigabe ein (Entscheidung Philipp 2026-10-13: pauschaler Haken, damit Claude Sudo-Skripte selbst ausfuehren kann):
#   1. Ordner /srv/ma-home/deploy-sudo (root:andrew, 1775): hier legt Claude Skript + "request" ab; Ergebnis steht in ergebnis.txt (root-eigen)
#   2. Root-Dienst ma-sudo (ma-sudo.path wartet auf request), Skript /usr/local/lib/ma-sudo-run.sh, Protokoll /var/log/ma-sudo/
#   3. Route /api/deploy/sudo-switch in portal.py (patch-portal-sudoswitch.py); Voraussetzung: schalter-einrichten.sh lief schon
#   4. Voreinstellung: Schalter AUS. Der Haken "Sudo-Skripte erlauben (Root)" sitzt im Portal-Chat neben dem Haken der Auto-Einspielung.
# ACHTUNG: Mit gesetztem Haken laeuft jedes Skript, das andrew ablegt, als root. Haken weg oder  sudo systemctl disable --now ma-sudo.path
# Rueckweg: sudo systemctl disable --now ma-sudo.path; sudo rm /etc/systemd/system/ma-sudo.* /usr/local/lib/ma-sudo-run.sh;
#           portal.py aus Sicherung /opt/ma-home/portal.py.bak-<Zeit> zurueckkopieren und ma-home-web neu starten.
# Hinweis: Damit die Claude-Bruecke in /srv/ma-home/deploy-sudo schreiben darf (ProtectSystem=strict), wird ein Drop-in angelegt. Es gilt
# erst nach dem naechsten Neustart der Bruecke (beendet laufende Chats), z. B. beim naechsten update-bridge.sh. Dieses Skript startet sie NICHT neu.
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
D="$(cd "$(dirname "$0")" && pwd)"
[ -d /srv/ma-home/deploy-schalter ] || { echo "Zuerst: sudo bash $D/schalter-einrichten.sh"; exit 1; }
bash -n "$D/ma-sudo-run.sh"
python3 -I -m py_compile "$D/patch-portal-sudoswitch.py"
install -m 755 -o root -g root "$D/ma-sudo-run.sh" /usr/local/lib/ma-sudo-run.sh
install -d -m 1775 -o root -g andrew /srv/ma-home/deploy-sudo
install -d -m 0750 -o root -g root /var/log/ma-sudo
cat > /etc/systemd/system/ma-sudo.service <<'UNIT'
[Unit]
Description=MA Home Sudo-Freigabe (Skripte von Claude als root, nur bei gesetztem Admin-Haken)
[Service]
Type=oneshot
TimeoutStartSec=1800
ExecStart=/usr/local/lib/ma-sudo-run.sh
UNIT
cat > /etc/systemd/system/ma-sudo.path <<'UNIT'
[Unit]
Description=Wartet auf /srv/ma-home/deploy-sudo/request
[Path]
PathExists=/srv/ma-home/deploy-sudo/request
Unit=ma-sudo.service
[Install]
WantedBy=multi-user.target
UNIT
install -d /etc/systemd/system/ma-claude-bridge.service.d
printf '[Service]\nReadWritePaths=-/srv/ma-home/deploy-sudo\n' > /etc/systemd/system/ma-claude-bridge.service.d/sudo.conf
systemctl daemon-reload
python3 -I "$D/patch-portal-sudoswitch.py"
systemctl restart ma-home-web; sleep 2
systemctl is-active ma-home-web
systemctl enable --now ma-sudo.path
systemctl is-active ma-sudo.path
echo "Fertig. Schalter ist AUS. Portal neu laden (Strg+F5), Haken 'Sudo-Skripte erlauben (Root)' setzen (nur Admin; Oberflaeche dafuer: deploy-ui.sh)."
echo "Claude nutzt:  bash ~/MA-Server/server/auto-deploy/sudo-anfordern.sh /pfad/skript.sh   (nach Neustart der Bruecke)."
