#!/bin/bash
# Auf dem Server:  sudo bash ~/automatik/performance-einrichten.sh
# Performance ohne Einschraenkung der Funktion:
#  1. Hintergrundjobs (USB-Backup, Wartung, Wachhund, Sicherheitsbericht) laufen mit niedriger CPU- und Platten-Prioritaet,
#     damit Portal, Claude und Home Assistant nie auf sie warten. Die Jobs werden dadurch nicht abgebrochen, nur nachrangig bedient.
#  2. earlyoom: bei echtem Speichermangel wird der groesste Verursacher gezielt beendet, bevor der ganze Server (3,3 GB RAM) haengt.
#     Geschuetzt: dockerd, sshd, caddy, authelia, systemd.
# Rueckgaengig: sudo rm /etc/systemd/system/ma-*.service.d/prio.conf && sudo systemctl daemon-reload; sudo apt-get remove earlyoom
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
for u in ma-usb-backup ma-home-maintenance ma-watchdog ma-sicherheitsbericht; do
  [ -f "/etc/systemd/system/$u.service" ] || [ -f "/lib/systemd/system/$u.service" ] || continue
  install -d "/etc/systemd/system/$u.service.d"
  cat > "/etc/systemd/system/$u.service.d/prio.conf" <<'EOT'
[Service]
Nice=10
IOSchedulingClass=idle
CPUWeight=20
EOT
done
systemctl daemon-reload
if ! command -v earlyoom >/dev/null; then DEBIAN_FRONTEND=noninteractive apt-get install -y earlyoom; fi
install -d /etc/default
if [ -f /etc/default/earlyoom ] && ! grep -q 'ma-home' /etc/default/earlyoom; then cp -a /etc/default/earlyoom /etc/default/earlyoom.bak; fi
cat > /etc/default/earlyoom <<'EOT'
# ma-home: bei weniger als 5 % freiem RAM und Swap handeln, wichtige Dienste schuetzen
EARLYOOM_ARGS="-r 3600 -m 5 -s 10 --avoid '(^|/)(dockerd|containerd|sshd|caddy|authelia|systemd|ma-home|fail2ban)' --prefer '(^|/)(claude|node|chromium)$'"
EOT
systemctl enable --now earlyoom
systemctl restart earlyoom
echo "--- Pruefung ---"
systemctl is-active earlyoom
for u in ma-usb-backup ma-home-maintenance; do systemctl show "$u.service" -p Nice -p IOSchedulingClass 2>/dev/null | paste -sd' '; done
