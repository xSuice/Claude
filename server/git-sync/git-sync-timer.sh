#!/usr/bin/env bash
# Timer: alle 15 Minuten "git-sync.py run" als andrew (committet Serveraenderungen auf den Zweig server-live und pusht ihn).
# Erst starten, wenn "git-sync.py status" Repo, Remote und Schluessel als vorhanden zeigt.
# Start ueber die Sudo-Bruecke oder: sudo bash ~/MA-Server/server/git-sync/git-sync-timer.sh
# Rueckweg: sudo systemctl disable --now ma-git-sync.timer; sudo rm /etc/systemd/system/ma-git-sync.{service,timer}
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Bitte mit sudo starten."; exit 1; }
cat > /etc/systemd/system/ma-git-sync.service <<'EOF'
[Unit]
Description=MA-Server nach GitHub (Zweig server-live)
After=network-online.target

[Service]
Type=oneshot
User=andrew
Group=ma-web
ExecStart=/usr/bin/python3 /home/andrew/MA-Server/scripts/server-sync/git-sync.py run
Nice=10
EOF
cat > /etc/systemd/system/ma-git-sync.timer <<'EOF'
[Unit]
Description=MA-Server nach GitHub alle 15 Minuten

[Timer]
OnBootSec=5min
OnUnitActiveSec=15min
Persistent=true

[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now ma-git-sync.timer
systemctl start ma-git-sync.service || true
systemctl status ma-git-sync.service --no-pager | head -8 || true
