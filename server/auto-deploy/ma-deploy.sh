#!/bin/bash
# Root-Teil der Auto-Einspielung (Dienst ma-deploy, ausgeloest durch die Datei /srv/ma-home/deploy/request).
# Installiert wird dieses Skript von Philipp nach /usr/local/lib/ma-deploy.sh (root-eigen). Aenderungen daran: nur per Sudo durch Philipp.
# Es spielt NUR diese festen Dateien aus ~/MA-Server ein, nach Pruefung und mit Sicherung und Rueckfall:
#   Oberflaeche:  portal-ui/web/{index.html,app.js,style.css,sw.js,manifest.webmanifest}  -> /opt/ma-home/web
#   Bruecken:     server/claude-bridge/ma-claude-bridge.py, server/term-bridge/ma-term-bridge.py -> /usr/local/lib (+ Dienst-Neustart)
# NICHT enthalten (bleibt manuell per Sudo): portal.py-Patches, systemd-Dateien, Docker, Firewall, alles andere.
set -Eeuo pipefail
SRC=/home/andrew/MA-Server
Q=/srv/ma-home/deploy
WEB=/opt/ma-home/web
LOG=/var/log/ma-deploy.log
exec >>"$LOG" 2>&1
T=$(mktemp -d /run/ma-deploy.XXXXXX)
trap 'rm -rf "$T"; rm -f "$Q/request"' EXIT
say() { echo "$(date '+%F %T') $*"; }
report() {                                   # Status fuer Claude/Philipp: root-eigen, im Sticky-Ordner nicht von andrew ersetzbar
  rm -f "$Q/status.txt"
  ( set -C; printf '%s\n%s\n' "$(date '+%F %T')" "$1" > "$Q/status.txt" ); chmod 644 "$Q/status.txt"
  say "$1"
}
fail() { report "FEHLER: $1"; exit 1; }
[ -f "$Q/request" ] && [ ! -L "$Q/request" ] || exit 0
say "Anforderung erhalten"

SRCR=$(realpath "$SRC")
grab() {                                     # grab <relpfad>: kopiert nur normale Dateien innerhalb von SRC in das Temp-Verzeichnis
  local p="$SRC/$1" r; r=$(realpath "$p" 2>/dev/null) || fail "Datei fehlt: $1"
  case "$r" in "$SRCR"/*) ;; *) fail "Pfad ausserhalb des Projekts: $1" ;; esac
  [ -f "$r" ] && [ ! -L "$p" ] || fail "Keine normale Datei: $1"
  [ "$(stat -c %s "$r")" -le 3000000 ] || fail "Datei zu gross: $1"
  cp --no-dereference --no-preserve=all "$r" "$T/$(basename "$1")"
  [ -f "$T/$(basename "$1")" ] && [ ! -L "$T/$(basename "$1")" ] || fail "Kopie ungueltig: $1"
}
syntax_py() { python3 -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$1" 2>/dev/null || fail "Python-Syntaxfehler: $(basename "$1")"; }
ver() { grep -o "VERSION = '[^']*'" "$1" | head -1; }

# ---- 1. Oberflaeche ----
WEBFILES="index.html app.js style.css sw.js manifest.webmanifest"
for f in $WEBFILES; do grab "portal-ui/web/$f"; done
[ -n "$(ver "$T/app.js")" ] && [ "$(ver "$T/app.js")" = "$(ver "$T/sw.js")" ] || fail "VERSION in app.js und sw.js fehlt oder ist verschieden"
WEBCHANGED=0
for f in $WEBFILES; do cmp -s "$T/$f" "$WEB/$f" || WEBCHANGED=1; done
# Vorab-Test: geaenderte Oberflaeche wird nur eingespielt, wenn der Browser-Rauchtest besteht. Der Test laeuft mit den Rechten von andrew (nie als root).
RUNNER=/home/andrew/.ma-browsertest/bin/python
TESTFILE="$SRCR/tests/portal_smoke.py"
TESTED=""
if [ $WEBCHANGED = 1 ] && [ -x "$RUNNER" ] && [ -f "$TESTFILE" ]; then
  if ! TOUT=$(runuser -u andrew -- env HOME=/home/andrew LD_LIBRARY_PATH=/home/andrew/.ma-browsertest/libs/usr/lib/x86_64-linux-gnu timeout 170 "$RUNNER" "$TESTFILE" 2>&1); then
    FAILS=$(printf '%s\n' "$TOUT" | grep -E '^FAIL|Traceback|Error' | head -3 | tr '\n' ' ')
    fail "Browser-Test fehlgeschlagen, Oberflaeche NICHT eingespielt: ${FAILS:-siehe Testausgabe}"
  fi
  TESTED="Browser-Test bestanden. "
  say "Browser-Test bestanden"
fi

# ---- 2. Bruecken ----
BR_CLAUDE=0; BR_TERM=0
grab server/claude-bridge/ma-claude-bridge.py; syntax_py "$T/ma-claude-bridge.py"
cmp -s "$T/ma-claude-bridge.py" /usr/local/lib/ma-claude-bridge.py || BR_CLAUDE=1
if [ -f /usr/local/lib/ma-term-bridge.py ]; then
  grab server/term-bridge/ma-term-bridge.py; syntax_py "$T/ma-term-bridge.py"
  cmp -s "$T/ma-term-bridge.py" /usr/local/lib/ma-term-bridge.py || BR_TERM=1
fi

if [ $WEBCHANGED = 0 ] && [ $BR_CLAUDE = 0 ] && [ $BR_TERM = 0 ]; then report "Nichts zu tun: alles ist bereits aktuell ($(ver "$T/app.js"))"; exit 0; fi
MSG=""

if [ $WEBCHANGED = 1 ]; then
  B=$WEB.bak-$(date +%Y%m%d-%H%M%S); cp -a "$WEB" "$B"
  for f in $WEBFILES; do install -m 640 -o root -g ma-web "$T/$f" "$WEB/$f"; done
  ( cd "$WEB" && for f in index.html app.js style.css sw.js manifest.webmanifest; do echo "$(tr -d '\r' < "$f" | sha256sum | cut -d' ' -f1)  $f"; done ) > /opt/ma-home/DEPLOYED-UI.sha256
  chmod 644 /opt/ma-home/DEPLOYED-UI.sha256
  if curl -sf -o /dev/null http://127.0.0.1:18765/healthz && [ "$(curl -s http://127.0.0.1:18765/assets/sw.js | grep -o "VERSION = '[^']*'" | head -1)" = "$(ver "$T/sw.js")" ]; then
    MSG="${TESTED}Oberflaeche eingespielt ($(ver "$T/sw.js")). "
  else
    rm -rf "$WEB"; cp -a "$B" "$WEB"; fail "Portal antwortet nach dem Einspielen nicht richtig; Oberflaeche zurueckgesetzt (Sicherung $B)"
  fi
  ls -d "$WEB".bak-* 2>/dev/null | head -n -10 | xargs -r rm -rf      # nur die letzten 10 Sicherungen behalten
fi

if [ $BR_CLAUDE = 1 ] || [ $BR_TERM = 1 ]; then
  if pgrep -u andrew -f 'claude.* -p .*stream-json' >/dev/null 2>&1; then
    MSG="${MSG}Bruecken NICHT neu gestartet: ein Claude-Auftrag laeuft (Neustart wuerde ihn beenden). Nach dem Auftrag erneut anfordern."
  else
    if [ $BR_CLAUDE = 1 ]; then
      cp -a /usr/local/lib/ma-claude-bridge.py /usr/local/lib/ma-claude-bridge.py.bak
      install -m 755 -o root -g root "$T/ma-claude-bridge.py" /usr/local/lib/ma-claude-bridge.py
      systemctl restart ma-claude-bridge; sleep 2
      if ! systemctl is-active --quiet ma-claude-bridge; then
        install -m 755 -o root -g root /usr/local/lib/ma-claude-bridge.py.bak /usr/local/lib/ma-claude-bridge.py; systemctl restart ma-claude-bridge
        fail "Claude-Bruecke startet nicht; alte Version wiederhergestellt"
      fi
      MSG="${MSG}Claude-Bruecke aktualisiert. "
    fi
    if [ $BR_TERM = 1 ]; then
      cp -a /usr/local/lib/ma-term-bridge.py /usr/local/lib/ma-term-bridge.py.bak
      install -m 755 -o root -g root "$T/ma-term-bridge.py" /usr/local/lib/ma-term-bridge.py
      systemctl restart ma-term-bridge; sleep 2
      if ! systemctl is-active --quiet ma-term-bridge; then
        install -m 755 -o root -g root /usr/local/lib/ma-term-bridge.py.bak /usr/local/lib/ma-term-bridge.py; systemctl restart ma-term-bridge
        fail "Terminal-Bruecke startet nicht; alte Version wiederhergestellt"
      fi
      MSG="${MSG}Terminal-Bruecke aktualisiert. "
    fi
  fi
fi
report "OK: $MSG"
