#!/bin/bash
# MA Home: rein lesende Authelia-Diagnose (Version, WebAuthn/Passkey-Konfiguration). Aendert nichts.
# Aufruf:  sudo bash ma-authelia-diag.sh
# Ausgabe: /home/andrew/ma-authelia-diag.txt (Geheimnisse, Hashes, Schluessel werden geschwaerzt)
set -uo pipefail
umask 077
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
OUT=/home/andrew/ma-authelia-diag.txt
redact() { sed -E 's/(secret|password|passwd|key|token|hash|salt)([^A-Za-z0-9_]{1,6})[^ ]{8,}/\1\2<REDACTED>/Ig'; }
{
  echo "== Container =="
  docker ps --filter name=authelia --format '{{.Names}}  {{.Image}}  {{.Status}}'
  echo; echo "== Version =="
  docker exec authelia authelia --version 2>&1 || docker exec authelia authelia build-info 2>&1
  echo; echo "== Konfig-Pfade (Mounts) =="
  docker inspect authelia --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
  echo; echo "== webauthn / totp / session / access_control (geschwaerzt) =="
  CFG=$(docker inspect authelia --format '{{range .Mounts}}{{if eq .Destination "/config"}}{{.Source}}{{end}}{{end}}')
  for f in "$CFG"/configuration.yml "$CFG"/configuration.yaml; do
    [ -f "$f" ] || continue
    echo "-- $f"
    grep -nEi -A12 '^(webauthn|totp|session|access_control|identity_validation):' "$f" | redact
  done
} >"$OUT" 2>&1
chown andrew:andrew "$OUT"
echo "Fertig: $OUT"
