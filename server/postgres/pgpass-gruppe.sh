#!/usr/bin/env bash
# Passwortdatei des Vault-Index fuer die Gruppe ma-web lesbar machen (Chat-Prozess ist andrew mit Hauptgruppe ma-web).
# Start ueber die Sudo-Bruecke oder: sudo bash ~/MA-Server/server/postgres/pgpass-gruppe.sh
# Rueckweg: chgrp andrew /etc/ma-home /etc/ma-home/vaultq.pgpass
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Bitte mit sudo starten."; exit 1; }
chgrp ma-web /etc/ma-home /etc/ma-home/vaultq.pgpass
chmod 0750 /etc/ma-home
chmod 0640 /etc/ma-home/vaultq.pgpass
ls -ld /etc/ma-home /etc/ma-home/vaultq.pgpass
