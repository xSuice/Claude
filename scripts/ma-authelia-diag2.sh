#!/bin/bash
# MA Home: rein lesende Authelia-Diagnose Teil 2 (Struktur der Konfiguration, ohne Werte von Geheimnissen). Aendert nichts.
# Aufruf:  sudo bash ma-authelia-diag2.sh      Ausgabe: /home/andrew/ma-authelia-diag2.txt
set -uo pipefail
umask 077
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
OUT=/home/andrew/ma-authelia-diag2.txt
D=/etc/ma-home/authelia
{
  echo "== Dateien =="; ls -la "$D"
  echo; echo "== Container-Kommando =="
  docker inspect ma-home-authelia-1 --format '{{json .Config.Cmd}} {{json .Config.Entrypoint}}'
  for f in "$D"/*.yml "$D"/*.yaml; do
    [ -f "$f" ] || continue
    echo; echo "== Struktur $f (Werte bei secret/password/hash/key/salt geschwaerzt) =="
    sed -E 's/^([[:space:]]*-?[[:space:]]*"?[A-Za-z_]*(secret|password|hash|key|salt|token)[A-Za-z_]*"?:).*/\1 <REDACTED>/I' "$f" | grep -vE '^[[:space:]]*(#|$)'
  done
} >"$OUT" 2>&1
chown andrew:andrew "$OUT"
echo "Fertig: $OUT"
