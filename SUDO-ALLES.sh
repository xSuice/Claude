#!/bin/bash
# EINE Datei fuer alles, was Sudo braucht. Auf dem MA-Server, ein Aufruf:
#     sudo bash ~/MA-Server/SUDO-ALLES.sh
# Optionen werden an alles-installieren.sh weitergereicht (--ohne-musik, --ohne-master).
# Reihenfolge:
#   1. Web-Terminal reparieren (SSH-Schluessel fuer ttyd)        server/tools/terminal-reparieren.sh
#   2. Alles installieren: Auto-Einspielung, Bruecke, Terminal-Bruecke, Portal inkl. Reiter "Neu",
#      Musik-Server, Jarvis-Zeitplan inkl. Statusbericht, Server = Hauptkopie des Vaults   server/alles-installieren.sh
#   3. Sudo im Portal-Terminal erlauben (nur dieser Dienst, Gruppe ma-sudo)   server/term-bridge/sudo-erlauben.sh
#      Auslassen mit:  OHNE_TERMINAL_SUDO=1 sudo -E bash ~/MA-Server/SUDO-ALLES.sh
#   4. Statusbericht einmal erzeugen (als andrew), damit der Reiter "Neu" sofort Daten hat
# Jeder Teil legt vorher Sicherungen an; ein Fehler in Teil 1 stoppt Teil 2 nicht.
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren:  sudo bash ~/MA-Server/SUDO-ALLES.sh"; exit 1; }
D="$(cd "$(dirname "$0")" && pwd)/server"
for f in tools/terminal-reparieren.sh alles-installieren.sh term-bridge/sudo-erlauben.sh; do bash -n "$D/$f" || { echo "Syntaxfehler in $f"; exit 1; }; done

echo "=== 1/4 Web-Terminal reparieren ==="
bash "$D/tools/terminal-reparieren.sh" || echo "Web-Terminal: siehe Meldung oben (der Rest laeuft weiter)."

echo "=== 2/4 Alles installieren ==="
bash "$D/alles-installieren.sh" "$@" || { echo "alles-installieren.sh meldete einen Fehler (siehe oben)."; RC=1; }

echo "=== 3/4 Sudo im Portal-Terminal ==="
if [ "${OHNE_TERMINAL_SUDO:-0}" = 1 ]; then echo "uebersprungen (OHNE_TERMINAL_SUDO=1)"; else
  bash "$D/term-bridge/sudo-erlauben.sh" || echo "Terminal-Sudo: siehe Meldung oben (der Rest laeuft weiter)."
fi

echo "=== 4/4 Statusbericht erzeugen ==="
runuser -u andrew -- python3 -I "$D/../scripts/server-sync/status-bericht.py" || echo "Statusbericht: Fehler (siehe oben)."

echo
echo "Fertig. Pruefen: Portal neu laden (Version 2026-10-12-20 oben), Reiter Neu, Reiter Claude."
echo "Danach NICHT vergessen: passwd (Sudo-Passwort wurde im Chat genannt)."
exit "${RC:-0}"
