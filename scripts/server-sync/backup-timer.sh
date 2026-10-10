#!/bin/bash
# Taeglich 04:15 Backup auf die USB-Platte mit dem geprueften Skript (root-eigene Kopie).
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
install -m 755 -o root -g root /home/andrew/ma-backup.sh /usr/local/sbin/ma-usb-backup
cat > /etc/systemd/system/ma-usb-backup.service <<'EOT'
[Unit]
Description=MA Home Backup auf USB-Platte (restic)
RequiresMountsFor=/mnt/ma-backup
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/ma-usb-backup run
Nice=10
IOSchedulingClass=idle
EOT
cat > /etc/systemd/system/ma-usb-backup.timer <<'EOT'
[Unit]
Description=Taegliches MA Home Backup
[Timer]
OnCalendar=*-*-* 04:15:00 Europe/Berlin
Persistent=true
[Install]
WantedBy=timers.target
EOT
systemctl daemon-reload
systemctl enable --now ma-usb-backup.timer
systemctl list-timers ma-usb-backup.timer --no-pager
