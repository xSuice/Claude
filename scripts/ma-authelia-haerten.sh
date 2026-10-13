#!/bin/bash
# MA Home: Authelia haerten. Zwei getrennte Schritte, beide mit Sicherung und Pruefung vor dem Neustart.
#   sudo bash ma-authelia-haerten.sh passkey   Passkey-Login (WebAuthn) einschalten
#   sudo bash ma-authelia-haerten.sh rotate    Session- und Reset-Schluessel neu, optional neue Passwoerter
# Nicht geaendert: storage.encryption_key (Wechsel braucht eine Migration der Datenbank).
# Rueckweg: Sicherung zurueckkopieren (Pfad steht in der Ausgabe), dann docker restart ma-home-authelia-1.
# Ungeprueft: Die Schluessel unter webauthn (enable_passkey_login, selection_criteria) stammen aus dem Gedaechtnis fuer
# Authelia v4.39; 'authelia validate-config' faengt falsche Schluessel ab und das Skript stellt dann die Sicherung wieder her.
set -euo pipefail
umask 027
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
D=/etc/ma-home/authelia
C=ma-home-authelia-1
CFG=$D/configuration.yml
TS=$(date +%Y%m%d-%H%M%S)

backup() { cp -p "$1" "$1.bak-$TS"; echo "Sicherung: $1.bak-$TS"; }
pruefen() {   # Konfiguration vom Container pruefen lassen; bei Fehler Sicherung zurueck
  if ! docker exec "$C" authelia validate-config --config /config/configuration.yml; then
    echo "Pruefung fehlgeschlagen, stelle Sicherung wieder her."
    cp -p "$CFG.bak-$TS" "$CFG"
    exit 1
  fi
}
neustart() {
  docker restart "$C" >/dev/null
  sleep 5
  docker ps --filter "name=$C" --format '{{.Names}}  {{.Status}}'
}

case "${1:-}" in
passkey)
  backup "$CFG"
  python3 - "$CFG" <<'PY'
import json, sys
p = sys.argv[1]
c = json.load(open(p, encoding="utf-8"))
c["webauthn"] = {
    "disable": False,
    "display_name": "MA Home",
    "attestation_conveyance_preference": "indirect",
    "timeout": "60s",
    "enable_passkey_login": True,
    "selection_criteria": {"discoverability": "preferred", "user_verification": "preferred"},
}
json.dump(c, open(p, "w", encoding="utf-8"), indent=2)
PY
  pruefen
  neustart
  echo "Fertig. Passkey anlegen: anmelden, dann https://ma-server.duckdns.org/auth/settings, Passkey hinzufuegen."
  ;;
rotate)
  backup "$CFG"; backup "$D/users.yml"
  python3 - "$CFG" <<'PY'
import json, secrets, sys
p = sys.argv[1]
c = json.load(open(p, encoding="utf-8"))
c["session"]["secret"] = secrets.token_hex(32)
c["identity_validation"]["reset_password"]["jwt_secret"] = secrets.token_hex(32)
json.dump(c, open(p, "w", encoding="utf-8"), indent=2)
PY
  pruefen
  for u in andrew andrew-app; do
    [ "${2:-}" = ohne-passwort ] && break      # nicht interaktiv (Sudo-Bruecke): Passwoerter spaeter selbst
    echo
    [ "$u" = andrew-app ] && echo "Achtung: andrew-app wird von Apps (Sync, ntfy) genutzt; dort danach das Passwort ebenfalls eintragen."
    read -rsp "Neues Passwort fuer $u (leer = nicht aendern): " pw; echo
    [ -n "$pw" ] || continue
    h=$(docker exec "$C" authelia crypto hash generate argon2 --password "$pw" | sed -n 's/^Digest: //p')
    [ -n "$h" ] || { echo "Hash konnte nicht erzeugt werden fuer $u, ueberspringe."; continue; }
    python3 - "$D/users.yml" "$u" "$h" <<'PY'
import json, sys
p, u, h = sys.argv[1:4]
d = json.load(open(p, encoding="utf-8"))
d["users"][u]["password"] = h
json.dump(d, open(p, "w", encoding="utf-8"), indent=2)
PY
    echo "Passwort fuer $u gesetzt."
  done
  chown ma-auth:ma-auth "$CFG" "$D/users.yml"
  neustart
  echo "Fertig. Alle Sitzungen sind beendet, bitte neu anmelden."
  ;;
*)
  echo "Aufruf: sudo bash $0 passkey|rotate"; exit 1 ;;
esac
