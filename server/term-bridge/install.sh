#!/bin/bash
# Auf dem MA-Server:  sudo bash ~/MA-Server/server/term-bridge/install.sh
# Installiert die Terminal-Bruecke (Dienst ma-term-bridge als andrew, ohne sudo-Rechte) und baut /api/term ins Portal ein (nur Admin).
# Rueckgaengig: sudo systemctl disable --now ma-term-bridge; sudo cp /opt/ma-home/portal.py.bak-<Zeit> /opt/ma-home/portal.py; sudo systemctl restart ma-home-web
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
D="$(cd "$(dirname "$0")" && pwd)"
install -m 755 -o root -g root "$D/ma-term-bridge.py" /usr/local/lib/ma-term-bridge.py
# Mit Sudo-Freigabe (sudo-erlauben.sh hat /etc/sudoers.d/ma-term-sudo angelegt) bekommt NUR dieser Dienst die Gruppe ma-sudo und darf neue Rechte erlangen;
# ohne Freigabe bleibt er stark eingeschraenkt (kein sudo, schreibgeschuetztes System).
if [ -f /etc/sudoers.d/ma-term-sudo ]; then
  SEC='NoNewPrivileges=no
SupplementaryGroups=ma-sudo
ProtectSystem=no'
else
  SEC='NoNewPrivileges=yes
ProtectSystem=strict
ReadWritePaths=/home/andrew /srv/ma-home/library
CapabilityBoundingSet='
fi
cat > /etc/systemd/system/ma-term-bridge.service <<UNIT
[Unit]
Description=MA Home Terminal-Bruecke (Portal -> bash als andrew)
After=network.target
[Service]
User=andrew
Group=ma-web
RuntimeDirectory=ma-term
RuntimeDirectoryMode=0750
ExecStart=/usr/bin/python3 /usr/local/lib/ma-term-bridge.py
Restart=on-failure
PrivateTmp=yes
Environment=HOME=/home/andrew
$SEC
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable ma-term-bridge
systemctl restart ma-term-bridge
sleep 2
systemctl is-active ma-term-bridge
ls -l /run/ma-term/
python3 "$D/patch-portal-term.py"
systemctl restart ma-home-web
sleep 3
curl -s -o /dev/null -w "Portal intern: HTTP %{http_code}\n" http://127.0.0.1:18765/healthz
echo "Fertig. Jetzt noch die Oberflaeche einspielen: sudo bash ~/MA-Server/portal-ui/deploy-ui.sh"
