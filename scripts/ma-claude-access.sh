#!/bin/bash
# MA Home: einmalige Einrichtung fuer selbststaendiges Arbeiten (Aufruf mit sudo, Passwort nur im Terminal).
# Es wird KEIN NOPASSWD eingerichtet. Ein mit Passwort bestaetigtes sudo-Ticket von andrew gilt 8 Stunden
# (Standard 15 Min). Ubuntu 26.04 nutzt sudo-rs: Ticket gilt nur im Terminal, in dem das Passwort eingegeben
# wurde (tty_tickets existiert dort nicht). Deshalb wird danach ein tmux-Terminal "ma-root" geoeffnet.
#  - Ticket liegt in /run, verschwindet beim Reboot und laeuft von selbst ab.
#  - Sofort beenden: 'ssh ma-server "tmux kill-session -t ma-root; sudo -k"'.
#  - Komplett entfernen: sudo rm /etc/sudoers.d/zz-ma-claude
# Danach wird die rein lesende Diagnose ma-diag-root.sh ausgefuehrt (aendert nichts).
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
F=/etc/sudoers.d/zz-ma-claude
umask 077
printf '%s\n' \
  '# MA Home: sudo-Ticket von andrew gilt 8 Stunden (kein NOPASSWD). sudo-rs: Ticket je Terminal.' \
  'Defaults:andrew timestamp_timeout=480' >"$F.tmp"
chmod 440 "$F.tmp"
if visudo -cf "$F.tmp" >/dev/null; then mv "$F.tmp" "$F"; echo "sudoers-Datei $F gesetzt (syntaxgeprueft)."; else rm -f "$F.tmp"; echo "visudo-Pruefung fehlgeschlagen, nichts geaendert."; exit 1; fi
visudo -c >/dev/null && echo "Gesamte sudoers-Konfiguration gueltig."
[ -f /home/andrew/ma-diag-root.sh ] && bash /home/andrew/ma-diag-root.sh
