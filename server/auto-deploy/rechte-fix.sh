#!/usr/bin/env bash
# Rechte-Fix für die Sudo-Brücke. Start durch Philipp: sudo bash ~/MA-Server/server/auto-deploy/rechte-fix.sh
# Ursache: Der Chat-Prozess läuft als andrew mit Hauptgruppe ma-web (nicht andrew).
# /srv/ma-home/deploy-sudo ist root:andrew 1775, daher scheitert das Ablegen von Skripten.
# Rückweg: sudo chgrp andrew /srv/ma-home/deploy-sudo && sudo chmod 1775 /srv/ma-home/deploy-sudo
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo starten."; exit 1; }

D=/srv/ma-home/deploy-sudo
S=/srv/ma-home/deploy-schalter

echo "== Vorher =="
ls -ld "$D" "$S" /srv/ma-home/deploy 2>&1 || true
ls -l "$S" 2>&1 || true

# Ablage-Ordner für Sudo-Skripte: Gruppe ma-web darf schreiben (Sticky-Bit schützt fremde Dateien).
chgrp ma-web "$D"
chmod 1775 "$D"

# Sicherheitsfund: $S ist für ma-web beschreibbar, der Chat könnte die Admin-Haken selbst setzen.
# Wird hier NICHT geändert, weil unklar ist, welcher Dienst die Haken im Portal schreibt.
echo
echo "== Laufende MA-Dienste (wer schreibt die Haken?) =="
systemctl list-units --type=service --state=running --no-legend 2>/dev/null | grep -iE 'ma-|portal' || true

echo
echo "== Nachher =="
ls -ld "$D"
echo "Fertig. Im Chat 'weiter' schreiben, dann teste ich sudo-anfordern.sh."
