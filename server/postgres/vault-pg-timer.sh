#!/usr/bin/env bash
# Timer fuer den Vault-Index in PostgreSQL: alle 10 Minuten "vault-pg.py sync" als Benutzer andrew (inkrementell, ca. 0,4 s).
# Start ueber die Sudo-Bruecke oder: sudo bash ~/MA-Server/server/postgres/vault-pg-timer.sh
# Rueckweg: sudo systemctl disable --now ma-vault-pg-sync.timer; sudo rm /etc/systemd/system/ma-vault-pg-sync.{service,timer}
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Bitte mit sudo starten."; exit 1; }
cat > /etc/systemd/system/ma-vault-pg-sync.service <<'EOF'
[Unit]
Description=Vault-Index (PostgreSQL) abgleichen
After=postgresql.service

[Service]
Type=oneshot
User=andrew
Group=ma-web
ExecStart=/usr/bin/python3 /home/andrew/MA-Server/scripts/vault-pg.py sync
Nice=10
EOF
cat > /etc/systemd/system/ma-vault-pg-sync.timer <<'EOF'
[Unit]
Description=Vault-Index (PostgreSQL) alle 10 Minuten abgleichen

[Timer]
OnBootSec=3min
OnUnitActiveSec=10min
Persistent=true

[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now ma-vault-pg-sync.timer
systemctl start ma-vault-pg-sync.service
systemctl status ma-vault-pg-sync.service --no-pager | head -8 || true
systemctl list-timers ma-vault-pg-sync.timer --no-pager
