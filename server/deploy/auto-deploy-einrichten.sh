#!/bin/bash
# Einmalig auf dem Server:  sudo bash ~/deploy-staging/auto-deploy-einrichten.sh
# Installiert /usr/local/sbin/ma-deploy (root-eigen, andrew kann ihn nicht aendern) und erlaubt andrew genau diesen einen Befehl ohne Passwort.
# Rueckgaengig: sudo rm /etc/sudoers.d/ma-deploy /usr/local/sbin/ma-deploy
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
D="$(cd "$(dirname "$0")" && pwd)"
[ -f "$D/ma-deploy" ] && [ ! -L "$D/ma-deploy" ] || { echo "ma-deploy fehlt neben diesem Skript."; exit 1; }
install -m 755 -o root -g root "$D/ma-deploy" /usr/local/sbin/ma-deploy
T=$(mktemp); echo 'andrew ALL=(root) NOPASSWD: /usr/local/sbin/ma-deploy' > "$T"
visudo -cf "$T" >/dev/null || { echo "sudoers-Regel ungueltig, abgebrochen."; rm -f "$T"; exit 1; }
install -m 440 -o root -g root "$T" /etc/sudoers.d/ma-deploy; rm -f "$T"
visudo -c >/dev/null && echo "Fertig: andrew darf 'sudo /usr/local/sbin/ma-deploy' ohne Passwort. Mehr nicht."
