#!/bin/bash
# Installiert Automount fuer weitere USB-Laufwerke -> Filebrowser-Ordner "USB" (nosuid,nodev,noexec). Backup-Platte ausgenommen.
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
cat > /usr/local/sbin/ma-usb-automount <<'EOF'
#!/bin/bash
# Aufruf: ma-usb-automount add|remove <kernelname, z.B. sdc1>
set -u
act="$1"; dev="/dev/$2"; base=/srv/ma-home/files/USB
fbrestart() { c=$(docker ps --format '{{.Names}}' | grep -i filebrowser | head -1); [ -n "$c" ] && docker restart "$c" >/dev/null; }
label=$(blkid -s LABEL -o value "$dev" 2>/dev/null || true)
fs=$(blkid -s TYPE -o value "$dev" 2>/dev/null || true)
name=$(printf '%s' "${label:-$2}" | tr -c 'A-Za-z0-9._-' '_')
dir="$base/$name"
case "$act" in
 add)
  [ "$label" = "MA-BACKUP" ] && exit 0
  findmnt -rn -S "$dev" >/dev/null && exit 0
  install -d -o ma-web -g ma-web -m 750 "$base" "$dir"
  opts=nosuid,nodev,noexec
  case "$fs" in vfat|exfat|ntfs|ntfs3) opts="$opts,uid=$(id -u ma-web),gid=$(id -g ma-web),umask=007" ;; esac
  mount -o "$opts" "$dev" "$dir" || { rmdir "$dir" 2>/dev/null; exit 1; }
  case "$fs" in ext2|ext3|ext4|xfs|btrfs) chown ma-web:ma-web "$dir" ;; esac
  fbrestart ;;
 remove)
  d=$(findmnt -rn -S "$dev" -o TARGET | head -1); [ -z "$d" ] && d="$dir"
  umount -l "$d" 2>/dev/null; rmdir "$d" 2>/dev/null; fbrestart ;;
esac
exit 0
EOF
chmod 755 /usr/local/sbin/ma-usb-automount
cat > /etc/systemd/system/ma-usb-automount@.service <<'EOF'
[Unit]
Description=USB-Laufwerk %I fuer Filebrowser einhaengen
BindsTo=dev-%i.device
After=dev-%i.device
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/sbin/ma-usb-automount add %I
ExecStop=/usr/local/sbin/ma-usb-automount remove %I
EOF
cat > /etc/udev/rules.d/99-ma-usb.rules <<'EOF'
ACTION=="add", SUBSYSTEM=="block", ENV{ID_BUS}=="usb", ENV{DEVTYPE}=="partition", ENV{ID_FS_USAGE}=="filesystem", ENV{ID_FS_LABEL}!="MA-BACKUP", TAG+="systemd", ENV{SYSTEMD_WANTS}+="ma-usb-automount@%k.service"
EOF
systemctl daemon-reload
udevadm control --reload
echo "Fertig. Zum Testen einen zweiten USB-Stick anstecken (Ordner USB/<Name> in Filebrowser)."
