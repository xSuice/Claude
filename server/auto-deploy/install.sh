#!/bin/bash
# Auf dem MA-Server, EINMAL:  sudo bash ~/MA-Server/server/auto-deploy/install.sh
# Richtet die Auto-Einspielung ein: Wenn Claude (oder du) die Datei /srv/ma-home/deploy/request anlegt, spielt ein Root-Dienst
# die feste Dateiliste aus ~/MA-Server ein (Oberflaeche + Claude-/Terminal-Bruecke), mit Pruefung, Sicherung und Rueckfall.
# Status steht danach in /srv/ma-home/deploy/status.txt, Protokoll in /var/log/ma-deploy.log.
# ACHTUNG (Sicherheit): Wer Dateien in ~/MA-Server aendern kann (also auch Claude), kann damit den Code von Portal-Oberflaeche und
# Bruecken tauschen. Root-Rechte bekommt er dadurch nicht (feste Dateiliste, kein portal.py, keine Systemdateien).
# Abschalten:  sudo systemctl disable --now ma-deploy.path
# Entfernen:   sudo systemctl disable --now ma-deploy.path; sudo rm /etc/systemd/system/ma-deploy.* /usr/local/lib/ma-deploy.sh
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
D="$(cd "$(dirname "$0")" && pwd)"
bash -n "$D/ma-deploy.sh"
install -m 755 -o root -g root "$D/ma-deploy.sh" /usr/local/lib/ma-deploy.sh
install -d -m 1775 -o root -g andrew /srv/ma-home/deploy        # Sticky: andrew legt "request" an, kann aber root-eigene Dateien nicht ersetzen
touch /var/log/ma-deploy.log; chmod 644 /var/log/ma-deploy.log
cat > /etc/systemd/system/ma-deploy.service <<'UNIT'
[Unit]
Description=MA Home Auto-Einspielung (Oberflaeche und Bruecken aus ~/MA-Server)
[Service]
Type=oneshot
ExecStart=/usr/local/lib/ma-deploy.sh
UNIT
cat > /etc/systemd/system/ma-deploy.path <<'UNIT'
[Unit]
Description=Wartet auf /srv/ma-home/deploy/request
[Path]
PathExists=/srv/ma-home/deploy/request
Unit=ma-deploy.service
[Install]
WantedBy=multi-user.target
UNIT
# Meldung aufs Handy, wenn ein langer Claude-Auftrag fertig ist (braucht ma-notify + Token, siehe scripts/server-sync/ntfy-einrichten.sh)
bash -n "$D/ma-job-notify.sh"
install -m 755 -o root -g root "$D/ma-job-notify.sh" /usr/local/lib/ma-job-notify.sh
install -d -m 1775 -o root -g andrew /srv/ma-home/deploy/notify
cat > /etc/systemd/system/ma-job-notify.service <<'UNIT'
[Unit]
Description=MA Home Meldung: Claude-Auftrag fertig
[Service]
Type=oneshot
ExecStart=/usr/local/lib/ma-job-notify.sh
UNIT
cat > /etc/systemd/system/ma-job-notify.path <<'UNIT'
[Unit]
Description=Wartet auf Meldungen der Claude-Bruecke
[Path]
PathExistsGlob=/srv/ma-home/deploy/notify/*.msg
Unit=ma-job-notify.service
[Install]
WantedBy=multi-user.target
UNIT
# Die Bruecke laeuft mit ProtectSystem=strict und darf nur in diesen Ordner zusaetzlich schreiben (die Datei "request" fuer deploy-anfordern.sh
# und die Meldungen in notify/; der Ordner ist sticky und root-eigen, andrew kann dort root-eigene Dateien wie status.txt nicht ersetzen):
install -d /etc/systemd/system/ma-claude-bridge.service.d
printf '[Service]\nReadWritePaths=-/srv/ma-home/deploy\n' > /etc/systemd/system/ma-claude-bridge.service.d/notify.conf
systemctl daemon-reload
systemctl enable --now ma-job-notify.path
systemctl enable --now ma-deploy.path
systemctl is-active ma-deploy.path
# Erster Lauf gleich jetzt: spielt den aktuellen Stand ein (v2026-10-12-2)
sudo -u andrew touch /srv/ma-home/deploy/request
for i in $(seq 1 45); do sleep 2; [ -e /srv/ma-home/deploy/request ] || break; done
cat /srv/ma-home/deploy/status.txt 2>/dev/null || echo "Noch kein Status; siehe /var/log/ma-deploy.log"
echo
echo "Fertig. Ab jetzt kann Claude mit  bash ~/MA-Server/server/auto-deploy/deploy-anfordern.sh  selbst einspielen."
echo "Nicht enthalten bleibt: portal.py-Patches (Terminal-/attach-Route) -> einmalig:  sudo bash ~/MA-Server/server/alles-einspielen.sh"
