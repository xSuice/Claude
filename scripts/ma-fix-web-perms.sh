#!/bin/bash
# MA Home: gezielte Reparatur der Zugriffsrechte unter /opt/ma-home/web.
# Aufruf (interaktiv, Passwort nur im Terminal):  sudo bash ma-fix-web-perms.sh
# Aendert NUR Eigentuemer/Modus (und einen vorhandenen benannten ACL-Eintrag des Dienstkontos)
# von /opt/ma-home/web und der dort direkt liegenden regulaeren Dateien.
# Nicht rekursiv, kein Dienst-Neustart, keine Auth-/Caddy-Aenderung. proxy_key wird nie ausgegeben
# und nie als Prozessargument uebergeben.
# MA_TEST=1 erlaubt Probelauf als normaler Benutzer in einem Testordner (siehe Variablen unten).
set -Eeuo pipefail
set +x
umask 077

TEST=${MA_TEST:-0}
if [ "$TEST" = 1 ]; then
  WEB=${MA_WEB:?}; BKROOT=${MA_BK_ROOT:?}; OWNER=$(id -un); SVC_USER=${MA_SVC_USER:?}; SVC_GROUP=$(id -gn)
else
  WEB=/opt/ma-home/web; BKROOT=/root/ma-backups; OWNER=root; SVC_USER=ma-web; SVC_GROUP=ma-web
  [ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
fi
TS=$(date -u +%Y%m%dT%H%M%SZ)
BK=$BKROOT/web-perms-$TS
CHANGED=0

on_error() {
  rc=$?
  trap - ERR
  echo "FEHLER (Exit $rc, Zeile ${BASH_LINENO[0]})." >&2
  if [ "$CHANGED" = 1 ]; then
    echo "Rechte wurden bereits geaendert -> automatischer Rueckweg." >&2
    bash "$BK/rollback.sh" >&2 || echo "ROLLBACK FEHLGESCHLAGEN. Manuell: sudo bash $BK/rollback.sh" >&2
  else
    echo "Es wurde noch nichts geaendert." >&2
  fi
  exit "$rc"
}
trap on_error ERR

[ -d "$WEB" ] && [ ! -L "$WEB" ] || { echo "FEHLER: $WEB fehlt oder ist ein Link."; exit 1; }
id "$SVC_USER" >/dev/null
for c in getfacl setfacl sha256sum runuser; do command -v "$c" >/dev/null || { echo "FEHLER: $c fehlt."; exit 1; }; done

# Alle Eintraege sortiert und damit reproduzierbar: Grundlage fuer Sicherung und Rollback-Vergleich.
acl_dump() { find "$WEB" -print0 | sort -z | xargs -0 getfacl -p; }

echo "== 1. Pruefung des Inhalts (nur lesen)"
find "$WEB" -printf '%y %u:%g %m links=%n %p\n'
if [ -n "$(find "$WEB" -mindepth 1 ! -type f -print -quit)" ]; then
  echo "ABBRUCH: Unterverzeichnis, Link oder Spezialdatei gefunden. Nichts geaendert."; exit 2
fi
if [ -n "$(find "$WEB" -mindepth 1 -type f -links +1 -print -quit)" ]; then
  echo "ABBRUCH: Datei mit mehreren Hardlinks gefunden (chmod wuerde auch das Ziel aendern). Nichts geaendert."; exit 2
fi
if [ -n "$(find "$WEB" -mindepth 1 -type f -name '*[|"\\]*' -print -quit)" ]; then
  echo "ABBRUCH: ungewoehnliche Dateinamen. Nichts geaendert."; exit 2
fi
N=$(find "$WEB" | wc -l)
echo "-- Erweiterte ACL-Eintraege (benannt oder default), sonst keine:"
acl_dump | grep -E '^(user|group|default):[^:]*:|^default:' | grep -vE '^(user|group)::' || echo "(keine)"

echo "== 2. Sicherung nach $BK"
install -d -m 700 "$BKROOT"
chmod 700 "$BKROOT"
mkdir -m 700 "$BK"
printf '%s\n' "$WEB" >"$BK/webpath.txt"
find "$WEB" -printf '%p\0%u\0%g\0%m\0' >"$BK/owners.bin"
find "$WEB" -printf '%y %u:%g %m %p\n' >"$BK/owners.txt"
acl_dump >"$BK/web.acl"
find "$WEB" -mindepth 1 -type f -print0 | xargs -0 -r sha256sum >"$BK/hashes.sha256"
cat >"$BK/rollback.sh" <<'EOF'
#!/bin/bash
# Stellt Eigentuemer, Modus und ACLs aus der Sicherung wieder her und prueft das Ergebnis.
# Aufruf: sudo bash rollback.sh
set -Eeuo pipefail
cd "$(dirname "$0")"
[ "$(id -u)" -eq 0 ] || [ "${MA_TEST:-0}" = 1 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
WEB=$(cat webpath.txt)
while IFS= read -r -d '' path && IFS= read -r -d '' user && IFS= read -r -d '' group && IFS= read -r -d '' mode; do
  [ -e "$path" ] || { echo "WARNUNG: $path fehlt, uebersprungen"; continue; }
  chown -h "$user:$group" "$path"
  chmod "$mode" "$path"
done <owners.bin
setfacl --restore=web.acl
BAD=0
while IFS= read -r -d '' path && IFS= read -r -d '' user && IFS= read -r -d '' group && IFS= read -r -d '' mode; do
  now=$(stat -c '%U|%G|%a' "$path")
  [ "$now" = "$user|$group|$mode" ] || { echo "ABWEICHUNG $path: ist $now, soll $user|$group|$mode"; BAD=1; }
done <owners.bin
# Vollstaendiger ACL-Vergleich (alle Eintraege, Mask, Default-ACLs) gegen die Sicherung
if find "$WEB" -print0 | sort -z | xargs -0 getfacl -p | diff -u web.acl - >acl-rollback.diff; then
  rm -f acl-rollback.diff
else
  echo "ABWEICHUNG bei ACLs, Unterschiede in $(pwd)/acl-rollback.diff"; BAD=1
fi
if [ "$BAD" = 0 ]; then echo "Rollback OK: Eigentuemer, Gruppe, Modi und vollstaendige ACLs entsprechen der Sicherung ($(pwd))."; else echo "Rollback UNVOLLSTAENDIG"; exit 1; fi
EOF
chmod 700 "$BK/rollback.sh"
bash -n "$BK/rollback.sh"
[ "$(tr -cd '\0' <"$BK/owners.bin" | wc -c)" -eq $((N*4)) ] || { echo "Sicherung unvollstaendig (owners.bin)"; exit 1; }
[ "$(grep -c '^# file: ' "$BK/web.acl")" -eq "$N" ] || { echo "Sicherung unvollstaendig (web.acl)"; exit 1; }
[ "$(wc -l <"$BK/hashes.sha256")" -eq $((N-1)) ] || { echo "Sicherung unvollstaendig (hashes)"; exit 1; }
sync
echo "Sicherung geprueft: $N Eintraege. Rueckweg: sudo bash $BK/rollback.sh"

portal_code() {  # $1 Pfad, $2 1=mit Schluessel; Schluessel nur ueber stdin an curl (nicht in argv)
  if [ "$2" = 1 ]; then
    printf 'header = "X-MA-Key: %s"\nheader = "Remote-User: %s"\n' "$KEY" "$USERNAME" |
      curl -s -m 8 -K - -o /dev/null -w '%{http_code} %{content_type} %{size_download}' "http://127.0.0.1:18765$1" || true
  else
    curl -s -m 8 -o /dev/null -w '%{http_code} %{content_type} %{size_download}' "http://127.0.0.1:18765$1" || true
  fi
}
# Fuehrt einen Befehl als Dienstkonto aus (im Testmodus als aktueller Benutzer).
as_svc() { if [ "$TEST" = 1 ]; then "$@"; else runuser -u "$SVC_USER" -- "$@"; fi; }
can_read() { as_svc head -c1 "$1" >/dev/null 2>&1; }
can_enter() { as_svc test -x "$1" && as_svc test -r "$1"; }

if [ "$TEST" != 1 ]; then
  KEY=$(python3 -c 'import json;print(json.load(open("/etc/ma-home/portal.json"))["proxy_key"])')
  USERNAME=$(python3 -c 'import json;print(next(iter(json.load(open("/etc/ma-home/portal.json"))["users"])))')
  case "$KEY$USERNAME" in *[\"\\]*|'') echo "Unerwartetes Zeichen in Konfiguration, Abbruch (nichts geaendert)."; exit 1;; esac
fi

echo "== 3. Vorher: Zugriff als $SVC_USER (Messung, noch keine Bewertung)"
if can_enter "$WEB" && can_read "$WEB/index.html"; then BEFORE_FS=lesbar; else BEFORE_FS="NICHT lesbar"; fi
echo "Dateizugriff index.html: $BEFORE_FS"
BEFORE_PORTAL=n/a
if [ "$TEST" != 1 ]; then BEFORE_PORTAL=$(portal_code / 1); echo "Portal / mit Schluessel: $BEFORE_PORTAL"; fi

echo "== 4. Aenderung (Verzeichnis 750, Dateien 640, Gruppe $SVC_GROUP)"
CHANGED=1
chown "$OWNER:$SVC_GROUP" "$WEB"
chmod 750 "$WEB"
find "$WEB" -mindepth 1 -maxdepth 1 -type f -exec chown -h "$OWNER:$SVC_GROUP" {} + -exec chmod 640 {} +
# Ein benannter ACL-Eintrag fuer das Dienstkonto hat Vorrang vor Gruppenrechten und wird von chown/chmod
# nicht geaendert. Nur dann und nur dieser Eintrag wird angepasst; -n laesst die Mask unveraendert.
fix_named() {  # $1 Pfad, $2 Rechte
  if getfacl -p "$1" | grep "^user:$SVC_USER:" >/dev/null; then   # ohne -q: kein SIGPIPE/pipefail
    setfacl -n -m "u:$SVC_USER:$2" "$1"
    echo "benannter ACL-Eintrag fuer $SVC_USER an $1 auf $2 gesetzt"
  fi
}
fix_named "$WEB" r-x
for f in "$WEB"/*; do [ -f "$f" ] && fix_named "$f" r--; done
sha256sum -c --quiet "$BK/hashes.sha256"   # Inhalt unveraendert
CHANGED=0   # Ab hier kein automatischer Rollback; Pruefergebnisse entscheiden.

echo "== 5. Nachher: Zugriff als $SVC_USER"
FAIL=0
if can_enter "$WEB"; then echo "OK   Verzeichnis durchsuchbar"; else echo "FEHLT: Verzeichnis nicht durchsuchbar"; FAIL=1; fi
for f in index.html app.js style.css; do
  if can_read "$WEB/$f"; then echo "OK   $f lesbar"; else echo "FEHLT/NICHT LESBAR: $f"; FAIL=1; fi
done
# Wirksame Rechte eines benannten Eintrags (Eintrag UND Mask) zusaetzlich ausweisen
getfacl -p "$WEB" | grep -E "^user:$SVC_USER:" || true
if [ "$TEST" != 1 ]; then
  echo "== 6. Portal lokal (Statuscodes gemaess portal.py)"
  chk() { r=$(portal_code "$1" "$2"); echo "$1 key=$2 -> $r (erwartet $3)"; case "$r" in "$3"*) ;; *) FAIL=1;; esac; }
  chk /                 1 "200 text/html"
  chk /assets/app.js    1 "200"
  chk /assets/style.css 1 "200 text/css"
  chk /api/me           1 "200 application/json"
  chk /                 0 "401"
  chk /healthz          0 "200"
  unset KEY
  echo "Vergleich /: vorher '$BEFORE_PORTAL' -> nachher (siehe oben). Ursache gilt erst mit diesem Vergleich und erfolgreichem Browserablauf als belegt."
fi
echo
if [ "$FAIL" = 0 ]; then echo "ERGEBNIS: OK. Rueckweg: sudo bash $BK/rollback.sh"; else echo "ERGEBNIS: PRUEFUNG FEHLGESCHLAGEN (Rechte bleiben geaendert). Rueckweg: sudo bash $BK/rollback.sh"; exit 3; fi
