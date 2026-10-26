#!/bin/bash
# Backup-Platte in Filebrowser sichtbar machen (nur lesen), per Bind-Mount in den Filebrowser-Ordner.
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
T=/srv/ma-home/files/Backup-USB
mountpoint -q /mnt/ma-backup || { echo "ABBRUCH: /mnt/ma-backup nicht eingehaengt"; exit 1; }
install -d -o ma-web -g ma-web -m 750 "$T"
grep -q " $T " /etc/fstab || echo "/mnt/ma-backup $T none bind,nofail 0 0" >> /etc/fstab
systemctl daemon-reload
mountpoint -q "$T" || mount "$T"
mount -o remount,bind,ro "$T"
findmnt "$T" -no TARGET,OPTIONS
docker ps --format '{{.Names}}' | grep -i filebrowser
docker restart $(docker ps --format '{{.Names}}' | grep -i filebrowser | head -1)
sleep 5
docker exec $(docker ps --format '{{.Names}}' | grep -i filebrowser | head -1) sh -c 'ls /srv 2>/dev/null; find / -maxdepth 3 -name Backup-USB 2>/dev/null; df -h 2>/dev/null | grep -E "Backup|data|srv" | head'
