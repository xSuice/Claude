#!/usr/bin/env bash
# Prüft die Abschottung von jarvis-server-run.sh OHNE Modell: statt hermes läuft eine Prüf-Shell an derselben Stelle.
# Erwartung: im Auftragsordner schreiben ja; außerhalb nein; sudo nein; Schlüssel/SSH/Portal-Schlüssel unsichtbar;
# eigene config.yaml nicht änderbar; Netz zu Nexum ja.
set -u
W=$(mktemp -d ~/sbx-test.XXXX); OUT=~/sbx-outside-$$; ok=0; bad=0
sed "s#\"\$H/.local/bin/hermes\" -p jarvis-server \"\$@\"#/bin/bash -c \"\$*\"#" ~/hermes-server/jarvis-server-run.sh > /tmp/sbx-run.sh
chk() { if [ "$2" = "$3" ]; then echo "  ✅ $1"; ok=$((ok+1)); else echo "  ❌ $1 (erwartet $3, war $2)"; bad=$((bad+1)); fi; }
run() { bash /tmp/sbx-run.sh "$W" -- "$1" >/dev/null 2>&1 && echo ja || echo nein; }
chk "schreiben im Auftragsordner"            "$(run "echo x > $W/f.txt")" ja
chk "schreiben außerhalb (Home)"             "$(run "echo x > $OUT")" nein
chk "schreiben in /opt/ma-home"              "$(run "touch /opt/ma-home/sbx")" nein
chk "sudo -n systemctl status (Rechte)"      "$(run "sudo -n true")" nein
chk "Nexum-Schlüsseldatei lesbar"            "$(run "cat ~/.config/ma-jarvis/keys/nexum.key")" nein
chk "SSH-Schlüssel lesbar"                   "$(run "ls ~/.ssh/id_* ~/.ssh/github_deploy")" nein
chk "Portal-Schlüssel lesbar"                "$(run "cat /etc/ma-home/portal.json")" nein
chk "Profil-.env änderbar"                 "$(run "echo X=1 >> ~/.hermes/profiles/jarvis-server/.env")" nein
chk "eigene config.yaml änderbar"            "$(run "echo '#' >> ~/.hermes/profiles/jarvis-server/config.yaml")" nein
chk "eigene SOUL.md änderbar"                "$(run "echo '#' >> ~/.hermes/profiles/jarvis-server/SOUL.md")" nein
chk "Sitzungsspeicher beschreibbar"          "$(run "touch ~/.hermes/profiles/jarvis-server/sessions-probe && rm ~/.hermes/profiles/jarvis-server/sessions-probe")" ja
chk "Netz zu Nexum"                          "$(run "curl -s -m 10 -o /dev/null https://dialagram.me/")" ja
chk "Engine-Daten (Brain) änderbar"          "$(run "touch /srv/ma-home/library/.jarvis/sbx")" nein
chk "Hermes-Code (hermes-agent) änderbar"    "$(run "touch ~/.hermes/hermes-agent/sbx")" nein
chk "Haupt-config.yaml änderbar"             "$(run "echo '#' >> ~/.hermes/config.yaml")" nein
chk "Hooks anlegbar (Code außerhalb)"        "$(run "touch ~/.hermes/hooks/sbx")" nein
chk "Haupt-.env lesbar"                      "$(run "grep -q = ~/.hermes/.env")" nein
chk "Gateway-Logs beschreibbar"              "$(run "touch ~/.hermes/logs/sbx && rm ~/.hermes/logs/sbx")" ja
run "echo x > ~/.hermes/installs/sbx-probe" >/dev/null; chk "Hermes-Programmcode dauerhaft änderbar" "$([ -e ~/.hermes/installs/sbx-probe ] && echo ja || echo nein)" nein
[ -e "$OUT" ] && rm -f "$OUT"; rm -rf "$W"
echo "Ergebnis: $ok bestanden, $bad fehlgeschlagen"
