#!/bin/bash
# Einmalig auf dem Server:  sudo bash ~/automatik/automatik-einrichten.sh
# Installiert Wachhund (alle 5 Min) und Sicherheitsbericht (woechentlich) als root-eigene Skripte mit systemd-Timern.
# Die Skripte liegen unter /usr/local/sbin (root:root) und werden nicht aus dem Staging nachgeladen.
# Rueckgaengig: sudo systemctl disable --now ma-watchdog.timer ma-sicherheitsbericht.timer; sudo rm /usr/local/sbin/ma-watchdog /usr/local/sbin/ma-sicherheitsbericht /etc/systemd/system/ma-watchdog.* /etc/systemd/system/ma-sicherheitsbericht.*
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
D="$(cd "$(dirname "$0")" && pwd)"
for f in ma-watchdog ma-sicherheitsbericht; do
  [ -f "$D/$f" ] && [ ! -L "$D/$f" ] || { echo "$f fehlt neben diesem Skript."; exit 1; }
  bash -n "$D/$f"
  install -m 755 -o root -g root "$D/$f" /usr/local/sbin/$f
done
install -d -m 755 /var/lib/ma-watchdog
cat > /etc/systemd/system/ma-watchdog.service <<'EOT'
[Unit]
Description=MA Home Wachhund (Dienste, Container, Backup, Platte)
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/ma-watchdog
EOT
cat > /etc/systemd/system/ma-watchdog.timer <<'EOT'
[Unit]
Description=MA Home Wachhund alle 5 Minuten
[Timer]
OnBootSec=3min
OnUnitActiveSec=5min
AccuracySec=30s
[Install]
WantedBy=timers.target
EOT
cat > /etc/systemd/system/ma-sicherheitsbericht.service <<'EOT'
[Unit]
Description=MA Home Sicherheitsbericht (nur lesen)
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/ma-sicherheitsbericht
EOT
cat > /etc/systemd/system/ma-sicherheitsbericht.timer <<'EOT'
[Unit]
Description=MA Home Sicherheitsbericht woechentlich
[Timer]
OnCalendar=Sun 05:00
Persistent=true
[Install]
WantedBy=timers.target
EOT
# Optimierung ohne Leistungsverlust: Dienste aus, die ein Headless-Server nicht braucht (weniger RAM und Angriffsflaeche).
# Bleibt an: cups (Drucken aus dem Portal), avahi (LAN-Erkennung), snapd, docker, fwupd.
# Rueckgaengig: sudo systemctl enable --now bluetooth ModemManager apport motd-news.timer ua-timer.timer update-notifier-motd.timer
for u in bluetooth.service ModemManager.service apport.service motd-news.timer ua-timer.timer update-notifier-motd.timer; do
  systemctl disable --now "$u" 2>/dev/null || true
done
systemctl daemon-reload
systemctl enable --now ma-watchdog.timer ma-sicherheitsbericht.timer
systemctl start ma-sicherheitsbericht.service
systemctl start ma-watchdog.service
echo "--- Wachhund ---"; cat /var/lib/ma-watchdog/status.txt
echo "--- Sicherheitsbericht (Ergebnis) ---"; sed -n '/## Ergebnis/,$p' /var/lib/ma-watchdog/sicherheit.md
