#!/bin/bash
# Auf dem Server:  sudo bash ~/ntfy-einrichten.sh
# Richtet "ma-notify" ein: Meldungen aufs Handy (ntfy), und eine Meldung wenn das Backup fehlschlaegt.
# Voraussetzung (macht Philipp selbst): Token-Datei /etc/ma-home/ntfy.token (root 600) mit einem ntfy-Zugriffstoken,
#   z.B.  sudo sh -c 'umask 077; read -rs T; echo "$T" > /etc/ma-home/ntfy.token'   (Token einfuegen, Enter)
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
cat > /usr/local/sbin/ma-notify <<'EOT'
#!/bin/bash
# Aufruf: ma-notify "Titel" "Text" [prio 1-5]
TOK=/etc/ma-home/ntfy.token
[ -r "$TOK" ] || { echo "ma-notify: Token fehlt ($TOK)" >&2; exit 1; }
curl -sS -m 15 -H "Authorization: Bearer $(cat $TOK)" -H "Title: ${1:-MA Home}" -H "Priority: ${3:-3}" \
  -d "${2:-}" https://ntfy.ma-server.duckdns.org/ma-home >/dev/null
EOT
chmod 755 /usr/local/sbin/ma-notify
cat > /etc/systemd/system/ma-notify-fail@.service <<'EOT'
[Unit]
Description=Meldung bei Fehler von %i
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/ma-notify "Fehler: %i" "Der Dienst %i ist fehlgeschlagen. Auf dem Server pruefen." 5
EOT
install -d /etc/systemd/system/ma-usb-backup.service.d
cat > /etc/systemd/system/ma-usb-backup.service.d/notify.conf <<'EOT'
[Unit]
OnFailure=ma-notify-fail@%n.service
EOT
systemctl daemon-reload
echo "Fertig. Test (nach dem Token): sudo ma-notify Test 'Hallo vom Server'"
