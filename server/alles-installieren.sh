#!/bin/bash
# Auf dem MA-Server, EIN Aufruf:  sudo bash ~/MA-Server/server/alles-installieren.sh [--ohne-musik]
# Optionen: --ohne-musik (Musik-Server ueberspringen), --ohne-master (Server NICHT zur Hauptkopie des Vaults machen)
# Installiert/aktualisiert der Reihe nach:
#   1. Auto-Einspielung + Meldung "Claude fertig" aufs Handy   (server/auto-deploy/install.sh)
#   2. Claude-Bruecke (Weiterlaufen im Hintergrund), Terminal-Bruecke, Portal-Patches, Oberflaeche   (server/alles-einspielen.sh)
#   3. Musik-Server Navidrome (nur lokal, 127.0.0.1:4533)   (server/musik/install.sh, mit --ohne-musik ueberspringen)
#   4. Jarvis-Zeitplan: Lern-Impuls abends, Morgenbrief/Fristen falls noch nicht geplant   (server/jarvis/install.sh)
# Bricht ab, wenn gerade ein Claude-Auftrag laeuft. Jeder Teil legt vorher Sicherungen an (siehe die Kopfzeilen der Teil-Skripte).
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
D="$(cd "$(dirname "$0")" && pwd)"
if pgrep -u andrew -f 'claude.* -p .*stream-json' >/dev/null 2>&1; then
  echo "Abbruch: Es laeuft gerade ein Claude-Auftrag. Bitte warten oder im Portal abbrechen, dann erneut starten."
  exit 1
fi
for f in auto-deploy/install.sh alles-einspielen.sh musik/install.sh jarvis/install.sh; do bash -n "$D/$f" || { echo "Syntaxfehler in $f"; exit 1; }; done
echo "== 1/3 Auto-Einspielung und Meldung =="
bash "$D/auto-deploy/install.sh"
echo "== 2/3 Bruecken, Portal, Oberflaeche =="
bash "$D/alles-einspielen.sh"
case " $* " in *" --ohne-musik "*) NO_MUSIK=1 ;; esac
case " $* " in *" --ohne-master "*) NO_MASTER=1 ;; esac
if [ -z "${NO_MUSIK:-}" ]; then
  echo "== 3/3 Musik-Server =="
  bash "$D/musik/install.sh" || echo "Musik-Server nicht eingerichtet (siehe Meldung oben); der Rest ist fertig."
fi
echo "== 4/4 Jarvis-Zeitplan (Lern-Impuls, Morgenbrief, Fristen) =="
bash "$D/jarvis/install.sh" || echo "Jarvis-Zeitplan nicht eingerichtet (siehe Meldung oben); der Rest ist fertig."
if [ -z "${NO_MASTER:-}" ]; then
  echo "== Server wird Hauptkopie des Vaults =="
  F=/srv/ma-home/library/.jarvis/server-master
  install -d -o andrew -g andrew -m 700 /srv/ma-home/library/.jarvis
  if [ ! -f "$F" ]; then
    printf '{"seit": "%s", "hinweis": "PC-Abgleich: Loeschungen vom Server nachziehen, Serverstand nie ueberschreiben"}\n' "$(date -Is)" > "$F"
    chown andrew:andrew "$F"; chmod 644 "$F"
  fi
  echo "Flag gesetzt ($F). Die PC-Skripte (vault-to-server.py, server-to-vault.py) beachten es beim naechsten Lauf."
fi
echo
echo "== Pruefung =="
systemctl is-active ma-claude-bridge ma-term-bridge ma-home-web ma-deploy.path ma-job-notify.path || true
curl -s -o /dev/null -w "Portal intern: HTTP %{http_code}\n" http://127.0.0.1:18765/healthz || true
[ -f /srv/ma-home/deploy/status.txt ] && { echo "Letzter Einspiel-Status:"; cat /srv/ma-home/deploy/status.txt; }
echo
echo "Fertig. Im Portal neu laden; im Seitenkopf steht die neue Version (v2026-10-12-14)."
echo "Noch offen: App am PC neu bauen (app/android/build.ps1); Meldung aufs Handy braucht ma-notify mit Token (scripts/server-sync/ntfy-einrichten.sh);"
echo "Musik: Dateien nach /srv/ma-home/library/media/musik, Caddy-Eintrag laut server/musik/caddy-beispiel.txt."
