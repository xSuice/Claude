#!/bin/bash
# Root-Teil der Sudo-Freigabe (Dienst ma-sudo, ausgeloest durch die Datei /srv/ma-home/deploy-sudo/request).
# Installiert wird dieses Skript von Philipp nach /usr/local/lib/ma-sudo-run.sh (root-eigen). Aenderungen daran: nur per Sudo durch Philipp.
# Ablauf: Claude legt ein Skript NAME.sh in /srv/ma-home/deploy-sudo/ ab und schreibt NAME.sh in die Datei "request".
# Ist der Admin-Schalter "Sudo-Skripte erlauben (Root)" im Portal an (Datei /srv/ma-home/deploy-schalter/sudo-erlaubt), kopiert dieses
# Skript NAME.sh zuerst in ein root-eigenes Verzeichnis (spaeteres Aendern wirkt nicht mehr), archiviert es mit Pruefsumme und fuehrt es
# als root aus. Ausgabe und Ergebnis: /srv/ma-home/deploy-sudo/ergebnis.txt, Archiv und Protokoll: /var/log/ma-sudo/.
# ACHTUNG: Mit gesetztem Schalter bekommt jedes Skript, das Claude (andrew) ablegt, Root-Rechte. Das ist gewollt (Entscheidung Philipp,
# 2026-10-13), aber nur so lange der Haken gesetzt ist. Haken weg = nichts wird ausgefuehrt.
# Abschalten sofort: Haken im Portal entfernen, oder  sudo systemctl disable --now ma-sudo.path
set -Eeuo pipefail
Q=/srv/ma-home/deploy-sudo
SW=/srv/ma-home/deploy-schalter/sudo-erlaubt
LOGD=/var/log/ma-sudo
MAXSEC=1700
install -d -m 0750 -o root -g root "$LOGD"
T=$(mktemp -d /run/ma-sudo.XXXXXX)
trap 'rm -rf "$T"; rm -f "$Q/request"' EXIT
say() { echo "$(date '+%F %T') $*" >>"$LOGD/ma-sudo.log"; }
report() {                                   # Ergebnis fuer Claude/Philipp: root-eigen, im Sticky-Ordner nicht von andrew ersetzbar
  rm -f "$Q/ergebnis.txt"
  ( set -C; { printf '%s\n%s\n' "$(date '+%F %T')" "$1"; [ -s "${2:-/dev/null}" ] && { echo '--- Ausgabe (letzte 200 Zeilen) ---'; tail -n 200 "$2"; }; } > "$Q/ergebnis.txt" ); chmod 644 "$Q/ergebnis.txt"
  say "$1"
}
[ -f "$Q/request" ] && [ ! -L "$Q/request" ] || exit 0
if [ ! -f "$SW" ] || [ -L "$SW" ]; then report "AUS: Sudo-Freigabe ist ausgeschaltet (Admin-Schalter im Portal). Nichts ausgefuehrt."; exit 0; fi

NAME=$(head -c 200 "$Q/request" | head -n 1 | tr -d '\r')
case "$NAME" in *[!A-Za-z0-9._-]*|''|.*) report "FEHLER: ungueltiger Skriptname in request"; exit 0 ;; esac
case "$NAME" in *.sh) ;; *) report "FEHLER: nur *.sh erlaubt: $NAME"; exit 0 ;; esac
P="$Q/$NAME"
[ -f "$P" ] && [ ! -L "$P" ] || { report "FEHLER: Skript fehlt oder ist keine normale Datei: $NAME"; exit 0; }
[ "$(stat -c %u "$P")" = "$(id -u andrew)" ] || { report "FEHLER: Skript gehoert nicht andrew: $NAME"; exit 0; }
[ "$(stat -c %s "$P")" -le 1000000 ] || { report "FEHLER: Skript zu gross: $NAME"; exit 0; }

cp --no-dereference --no-preserve=all "$P" "$T/run.sh"
[ -f "$T/run.sh" ] && [ ! -L "$T/run.sh" ] || { report "FEHLER: Kopie ungueltig"; exit 0; }
bash -n "$T/run.sh" 2>"$T/syntax.txt" || { report "FEHLER: Syntaxfehler in $NAME" "$T/syntax.txt"; exit 0; }
SUM=$(sha256sum "$T/run.sh" | cut -d' ' -f1)
ARCH="$LOGD/$(date +%Y%m%d-%H%M%S)-$NAME"
install -m 0640 -o root -g root "$T/run.sh" "$ARCH"
say "Start: $NAME sha256=$SUM Archiv=$ARCH"

set +e
( cd /root && timeout "$MAXSEC" bash "$T/run.sh" ) >"$T/out.txt" 2>&1
RC=$?
set -e
cp "$T/out.txt" "$ARCH.out"; chmod 640 "$ARCH.out"
if [ "$RC" = 0 ]; then report "OK: $NAME ausgefuehrt (sha256 ${SUM:0:12})" "$T/out.txt"
elif [ "$RC" = 124 ]; then report "FEHLER: $NAME nach ${MAXSEC}s abgebrochen" "$T/out.txt"
else report "FEHLER: $NAME endete mit Code $RC" "$T/out.txt"; fi
ls "$LOGD"/*-*.sh 2>/dev/null | head -n -50 | xargs -r rm -f      # nur die letzten 50 Skripte behalten
