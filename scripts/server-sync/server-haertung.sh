#!/bin/bash
# Einmal auf dem MA-Server ausfuehren:  sudo bash server-haertung.sh
# Zweck: Laptop-Server laeuft bei zugeklapptem Deckel weiter, schlaeft nie, startet nach Stromausfall (soweit BIOS es kann).
# Rueckgängig: sudo rm /etc/systemd/logind.conf.d/lid.conf; sudo systemctl unmask sleep.target suspend.target hibernate.target hybrid-sleep.target; sudo systemctl restart systemd-logind
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
mkdir -p /etc/systemd/logind.conf.d
cat >/etc/systemd/logind.conf.d/lid.conf <<'EOF'
[Login]
HandleLidSwitch=ignore
HandleLidSwitchExternalPower=ignore
HandleLidSwitchDocked=ignore
IdleAction=ignore
EOF
systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
systemctl restart systemd-logind
echo "--- Pruefung ---"
systemd-analyze cat-config systemd/logind.conf | grep -E '^(HandleLidSwitch|IdleAction)'
systemctl is-enabled sleep.target || true
echo "Akku: $(cat /sys/class/power_supply/BAT1/status 2>/dev/null) $(cat /sys/class/power_supply/BAT1/capacity 2>/dev/null)%"
echo "Fertig. Deckel zuklappen und per SSH von aussen testen."
