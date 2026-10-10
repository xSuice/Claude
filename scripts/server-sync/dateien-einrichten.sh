#!/bin/bash
# Auf dem Server:  sudo bash ~/dateien-einrichten.sh
# Macht in der Portal-Seite "Dateien" sichtbar: Bibliothek (inkl. Vault-Notizen-Spiegel), Backup-USB (nur lesen).
# Das Portal zeigt nur /srv/ma-home/files/<Benutzer>/ ohne Symlinks, daher Bind-Mounts (fstab, nofail).
# Ergebnis wird auch nach /home/andrew/dateien-einrichten.log geschrieben.
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
exec > >(tee /home/andrew/dateien-einrichten.log) 2>&1
echo "== Portal-Benutzer =="
USERS=$(python3 -c 'import json;d=json.load(open("/etc/ma-home/portal.json"))["users"];print(" ".join(u for u,v in d.items() if v.get("admin")))')
echo "Admins: $USERS"
echo "== files-Ordner (vorher) =="; ls -la /srv/ma-home/files | head -20
# ma-web darf die Bibliothek lesen: Gruppe andrew (Verzeichnisse sind 750 andrew:andrew)
id -nG ma-web | grep -qw andrew || usermod -aG andrew ma-web
chmod -R g+rX /srv/ma-home/library
for u in $USERS; do
  D=/srv/ma-home/files/$u
  install -d -o ma-web -g ma-web -m 750 "$D" "$D/Bibliothek" "$D/Backup-USB"
  grep -q " $D/Bibliothek " /etc/fstab || echo "/srv/ma-home/library $D/Bibliothek none bind,nofail 0 0" >> /etc/fstab
  grep -q " $D/Backup-USB " /etc/fstab || echo "/mnt/ma-backup $D/Backup-USB none bind,nofail 0 0" >> /etc/fstab
  systemctl daemon-reload
  mountpoint -q "$D/Bibliothek" || mount "$D/Bibliothek"
  mount -o remount,bind,ro "$D/Bibliothek"
  if mountpoint -q /mnt/ma-backup; then mountpoint -q "$D/Backup-USB" || mount "$D/Backup-USB"; mount -o remount,bind,ro "$D/Backup-USB"; fi
  echo "== $u: Inhalt =="; ls -la "$D" | head -20
done
systemctl restart ma-home-web
sleep 2
curl -s -o /dev/null -w "Portal intern: HTTP %{http_code}\n" http://127.0.0.1:18765/healthz
sudo -u ma-web ls /srv/ma-home/library/vault-notizen | head -3 && echo "ma-web kann die Bibliothek lesen"
echo "Fertig. Seite 'Dateien' im Portal neu laden."
