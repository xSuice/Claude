#!/bin/bash
# Auf dem Server:  sudo bash ~/automatik/ssh-haerten.sh
# Haertet SSH: nur Schluessel-Anmeldung, kein Root-Login. Erreichbar bleibt SSH wie bisher nur aus dem Heimnetz (ufw).
# VORHER pruefen: Dein Schluessel-Login vom PC funktioniert (ssh ma-server). Lass dieses Fenster/diese Sitzung offen und teste danach
# in einem ZWEITEN Fenster, dass du dich noch anmelden kannst. Andere Geraete, die per Passwort anmelden (z. B. Handy), brauchen dann einen Schluessel.
# Rueckgaengig: sudo rm /etc/ssh/sshd_config.d/10-ma-haertung.conf && sudo systemctl reload ssh
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
[ -s /home/andrew/.ssh/authorized_keys ] || { echo "Abbruch: andrew hat keinen Schluessel in authorized_keys, sonst waerst du ausgesperrt."; exit 1; }
F=/etc/ssh/sshd_config.d/10-ma-haertung.conf
[ -f "$F" ] && cp -a "$F" "$F.bak"
cat > "$F" <<'EOT'
# MA Home: Haertung (Datei 10- gewinnt vor 50-cloud-init.conf, es zaehlt der erste Wert)
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
MaxAuthTries 3
EOT
if ! sshd -t; then echo "sshd-Konfiguration fehlerhaft, Aenderung zurueckgenommen."; if [ -f "$F.bak" ]; then mv "$F.bak" "$F"; else rm -f "$F"; fi; exit 1; fi
systemctl reload ssh 2>/dev/null || systemctl reload sshd
sshd -T | grep -E '^(passwordauthentication|permitrootlogin|kbdinteractiveauthentication|maxauthtries) '
echo "Fertig. Teste JETZT in einem zweiten Fenster:  ssh ma-server   (muss ohne Passwort klappen)."
