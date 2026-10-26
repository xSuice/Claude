#!/bin/bash
# Auf dem MA-Server:  sudo bash ~/MA-Server/server/alles-einspielen.sh
# Spielt alles ein: Claude-Bruecke (Weiterlaufen im Hintergrund), Terminal-Bruecke, Portal-Oberflaeche (v2026-10-12-2).
# Bricht ab, wenn gerade ein Claude-Auftrag laeuft (der Neustart der Bruecke wuerde ihn beenden); dann spaeter erneut starten.
# Rueckgaengig: Sicherungen /opt/ma-home/portal.py.bak-<Zeit> und /opt/ma-home/web.bak-<Zeit> zurueckkopieren, dann: systemctl restart ma-home-web
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
D="$(cd "$(dirname "$0")/.." && pwd)"
if pgrep -u andrew -f 'claude.* -p .*stream-json' >/dev/null 2>&1; then
  echo "Abbruch: Es laeuft gerade ein Claude-Auftrag. Bitte warten oder im Portal abbrechen, dann erneut starten."
  exit 1
fi
echo "== 1/3 Claude-Bruecke =="
bash "$D/server/claude-bridge/update-bridge.sh"
echo "== 2/3 Terminal-Bruecke =="
bash "$D/server/term-bridge/install.sh"
echo "== 3/3 Oberflaeche =="
bash "$D/portal-ui/deploy-ui.sh"
echo
echo "Fertig. Im Portal neu laden; im Seitenkopf steht jetzt v2026-10-12-2."
echo "Noch offen (am PC): App mit app/android/build.ps1 neu bauen und installieren (Druckansicht)."
