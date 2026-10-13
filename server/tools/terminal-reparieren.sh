#!/bin/bash
# Auf dem MA-Server, EINMAL:  sudo bash ~/MA-Server/server/tools/terminal-reparieren.sh
# Repariert das Web-Terminal (https://ma-server.duckdns.org/terminal/, ttyd -> ssh andrew@127.0.0.1).
# Ursache: Der SSH-Server erlaubt seit der Haertung nur Schluessel (PasswordAuthentication no), das Terminal laeuft aber als
# Benutzer ma-web ohne Schluessel -> "Permission denied (publickey)".
# Loesung: Passwort-Anmeldung NUR fuer Verbindungen von diesem Rechner (127.0.0.1 / ::1). Von aussen bleibt alles wie gehaertet.
# Ergebnis: Authelia (mit 2. Faktor) UND danach das Passwort von andrew im Browser-Terminal = zwei Huerden.
# Sicherheitsnetz: Syntaxpruefung, Pruefung der WIRKSAMEN Einstellung fuer lokal (ja) und extern (nein) vor dem Neuladen; sonst Rueckbau.
# Rueckgaengig: sudo rm /etc/ssh/sshd_config.d/99-ma-terminal.conf && sudo systemctl reload ssh
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
F=/etc/ssh/sshd_config.d/99-ma-terminal.conf
SVC=ssh; systemctl cat ssh >/dev/null 2>&1 || SVC=sshd
cat > "$F" <<'EOF'
# MA Home: Web-Terminal (ttyd) meldet sich per Passwort an, aber NUR von diesem Rechner.
Match Address 127.0.0.1,::1
    PasswordAuthentication yes
    MaxAuthTries 3
EOF
chmod 644 "$F"
undo() { rm -f "$F"; echo "Zurueckgebaut: $F entfernt, nichts geaendert."; exit 1; }
sshd -t || { echo "sshd-Konfiguration fehlerhaft."; undo; }
LOCAL="$(sshd -T -C user=andrew,host=localhost,addr=127.0.0.1 | awk '$1=="passwordauthentication"{print $2}')"
EXTERN="$(sshd -T -C user=andrew,host=example.org,addr=203.0.113.9 | awk '$1=="passwordauthentication"{print $2}')"
echo "Wirksam: lokal (127.0.0.1) passwordauthentication=$LOCAL, extern passwordauthentication=$EXTERN"
[ "$LOCAL" = "yes" ] && [ "$EXTERN" = "no" ] || { echo "Wirkung nicht wie erwartet (lokal ja, extern nein)."; undo; }
systemctl reload "$SVC"
sleep 1
systemctl is-active "$SVC"
if ssh-keygen -F 127.0.0.1 -f /etc/ma-home/ssh_known_hosts >/dev/null 2>&1; then echo "known_hosts: Eintrag fuer 127.0.0.1 vorhanden."; else echo "Hinweis: /etc/ma-home/ssh_known_hosts hat keinen Eintrag fuer 127.0.0.1 (Terminal meldet dann einen Host-Key-Fehler, nicht diese Meldung)."; fi
cat <<'TXT'

Fertig. Test:
 1. https://ma-server.duckdns.org/terminal/ im Browser oeffnen, bei Authelia anmelden.
 2. Das Terminal fragt jetzt nach dem Passwort von andrew (Eingabe wird nicht angezeigt).
 3. Danach laeuft dort z. B.:  sudo bash ~/MA-Server/server/alles-installieren.sh
Aendert sich der Host-Key des Servers, muss /etc/ma-home/ssh_known_hosts erneuert werden.
TXT
