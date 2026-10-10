#!/bin/bash
# Richtet die USB-Platte als Backupziel ein (ext4, fester Mount, restic-Repo) und fuehrt das erste Backup aus.
# Sicherheitsabfrage: formatiert NUR /dev/sdb, wenn es USB, 250-350 GB gross ist und das FAT-Label UBUNTU-SERV traegt.
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
D=/dev/sdb
[ "$(lsblk -dno TRAN $D)" = "usb" ] || { echo "ABBRUCH: $D ist nicht USB"; exit 1; }
SZ=$(lsblk -dbno SIZE $D); [ "$SZ" -gt 250000000000 ] && [ "$SZ" -lt 350000000000 ] || { echo "ABBRUCH: Groesse passt nicht"; exit 1; }
[ "$(lsblk -no LABEL ${D}1)" = "UBUNTU-SERV" ] || { echo "ABBRUCH: Label passt nicht"; exit 1; }
mountpoint -q /mnt/usbcheck && umount /mnt/usbcheck || true
umount ${D}1 2>/dev/null || true
echo "--- formatiere $D (ext4, Label MA-BACKUP) ---"
wipefs -a $D >/dev/null
parted -s $D mklabel gpt mkpart backup ext4 1MiB 100%
sleep 2; partprobe $D; sleep 2
mkfs.ext4 -F -L MA-BACKUP -m 1 ${D}1
UUID=$(blkid -s UUID -o value ${D}1)
mkdir -p /mnt/ma-backup
grep -q "$UUID" /etc/fstab || echo "UUID=$UUID /mnt/ma-backup ext4 defaults,nofail,x-systemd.device-timeout=5 0 2" >> /etc/fstab
systemctl daemon-reload
mount /mnt/ma-backup
install -d -m 700 /mnt/ma-backup/restic-repo
install -d -m 700 /etc/ma-home
if [ ! -f /etc/ma-home/backup.pass ]; then
  umask 077; head -c 32 /dev/urandom | base64 > /etc/ma-home/backup.pass
fi
cat > /etc/ma-home/backup.env <<EOT
RESTIC_REPOSITORY=/mnt/ma-backup/restic-repo
RESTIC_PASSWORD_FILE=/etc/ma-home/backup.pass
EOT
chmod 600 /etc/ma-home/backup.env /etc/ma-home/backup.pass
set -a; . /etc/ma-home/backup.env; set +a
restic cat config >/dev/null 2>&1 || restic init
echo "--- erstes Backup ---"
bash /home/andrew/ma-backup.sh run
echo "--- Restore-Test ---"
bash /home/andrew/ma-backup.sh restore-test
echo "--- Timer ---"
systemctl cat ma-home-backup.service | grep -E '^(ExecStart|User)' || true
systemctl list-timers ma-home-backup.timer --no-pager || true
df -h /mnt/ma-backup | tail -1
echo "WICHTIG: Backup-Passwort sichern (sonst nicht wiederherstellbar): sudo cat /etc/ma-home/backup.pass"
