#!/bin/bash
# Auf dem MA-Server, EINMAL:  sudo bash ~/MA-Server/server/term-bridge/sudo-erlauben.sh [--user-regel]
# Erlaubt "sudo" im Portal-Terminal (Reiter Terminal), ohne Passwort, aber NUR dort:
#   - Gruppe ma-sudo mit Regel "%ma-sudo ALL=(root) NOPASSWD: ALL" (/etc/sudoers.d/ma-term-sudo, mit visudo geprueft)
#   - nur der Dienst ma-term-bridge bekommt die Gruppe (SupplementaryGroups) und darf neue Rechte erlangen (NoNewPrivileges=no, System beschreibbar)
#   - NICHT andrew selbst: SSH-Sitzungen, der Claude-Chat (ma-claude-bridge, NoNewPrivileges) und alle anderen Dienste koennen weiter kein sudo
# Schutz im Portal: Terminal nur fuer Admin (Authelia), jeder Befehl steht in .jarvis/term.log, "sudo ..." fragt im Portal erst beim zweiten Absenden.
# Pruefung am Ende: ein Befehl mit nur der Gruppe ma-sudo muss "sudo -n true" schaffen, andrew ohne Gruppe nicht.
# --user-regel: Falls deine sudo-Version die Gruppe nicht auswertet, legt das stattdessen "andrew ALL=(root) NOPASSWD: ALL" an (breiter: jeder Prozess von andrew
#   ohne NoNewPrivileges, auch SSH-Sitzungen, haette dann Root ohne Passwort). Nur wenn die Gruppenregel nachweislich nicht greift.
# Rueckgaengig: sudo rm /etc/sudoers.d/ma-term-sudo && sudo bash ~/MA-Server/server/term-bridge/install.sh   (stellt die eingeschraenkte Unit wieder her)
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
LOG=/var/log/ma-sudo-erlauben.log            # lesbar fuer andrew/Claude, damit der Lauf ohne Abtippen ausgewertet werden kann
touch "$LOG"; chmod 644 "$LOG"
exec > >(tee -a "$LOG") 2>&1
echo "==== $(date '+%F %T') sudo-erlauben.sh $* ===="
D="$(cd "$(dirname "$0")" && pwd)"
F=/etc/sudoers.d/ma-term-sudo
getent group ma-sudo >/dev/null || groupadd --system ma-sudo
if [ "${1:-}" = "--user-regel" ]; then
  RULE='andrew ALL=(root) NOPASSWD: ALL'
else
  RULE='%ma-sudo ALL=(root) NOPASSWD: ALL'
fi
T="$(mktemp)"
printf '# MA Home: sudo ohne Passwort fuer das Portal-Terminal (Gruppe ma-sudo, nur der Dienst ma-term-bridge). Angelegt von sudo-erlauben.sh\n%s\n' "$RULE" > "$T"
if ! VOUT=$(visudo -cf "$T" 2>&1); then echo "Sudoers-Regel ungueltig, nichts geaendert: $VOUT"; rm -f "$T"; exit 1; fi
echo "visudo: $VOUT"
install -m 440 -o root -g root "$T" "$F"; rm -f "$T"
bash "$D/install.sh"
echo "== Pruefung =="
GID_SUDO="$(getent group ma-sudo | cut -d: -f3)"
# Prozess "wie die Terminal-Bruecke": Benutzer andrew mit genau diesen Gruppen (andrew + ma-web + ma-sudo), danach darf sudo ohne Passwort laufen
as_term() { setpriv --reuid=andrew --regid=andrew --groups="$(id -g andrew),$(getent group ma-web | cut -d: -f3),$GID_SUDO" -- "$@"; }
as_plain() { setpriv --reuid=andrew --regid=andrew --init-groups -- "$@"; }
if [ "${1:-}" = "--user-regel" ]; then
  echo "Benutzerregel aktiv (breiter). Pruefung der Gruppe entfaellt."
else
  if OUT=$(as_term sudo -n true 2>&1); then echo "OK: Prozess mit Gruppe ma-sudo darf sudo."; else
    echo "FEHLER: Prozess mit Gruppe ma-sudo darf kein sudo. Meldung von sudo: $OUT"
    echo "Gruppen im Pruefprozess: $(as_term id 2>&1)"
    echo "Rueckbau. Alternative: mit --user-regel die breitere Regel setzen (siehe Kopfzeilen)."; rm -f "$F"; bash "$D/install.sh"; exit 1; fi
  if OUT=$(as_plain sudo -n true 2>&1); then echo "WARNUNG: andrew ohne Gruppe darf ebenfalls sudo (hat schon eine eigene Regel?)."; else echo "OK: andrew ohne Gruppe darf weiterhin kein sudo ohne Passwort ($OUT)."; fi
fi
sleep 1
systemctl is-active ma-term-bridge
echo "Fertig. Im Portal: Reiter Terminal, z. B. 'sudo systemctl status ssh' (zweimal absenden zum Bestaetigen)."
