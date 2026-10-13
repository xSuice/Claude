#!/usr/bin/env bash
# Wrapper fuer die Sudo-Bruecke: ma-sudo-run.sh kopiert nur ein einzelnes Skript nach /run/ma-sudo.*, deploy-ui.sh braucht aber den Ordner web/ neben sich.
# Start: bash ~/MA-Server/server/auto-deploy/sudo-anfordern.sh ~/MA-Server/server/auto-deploy/deploy-ui-bruecke.sh
set -euo pipefail
exec bash /home/andrew/MA-Server/portal-ui/deploy-ui.sh
