#!/bin/bash
# Auf dem Server:  sudo bash ~/MA-Server/server/tools/install-bluetooth.sh
# Installiert bluez (bluetoothctl, rfkill) und startet den Bluetooth-Dienst, damit Claude Geraete per Bluetooth ansteuern kann.
# Doku: docs/netzwerk-inventar.md. Es werden keine Geraete gekoppelt; das macht Philipp bewusst mit `bluetoothctl`.
# Rueckgaengig: sudo systemctl disable --now bluetooth && sudo apt-get remove --purge -y bluez rfkill && sudo apt-get autoremove -y
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends bluez rfkill
systemctl enable --now bluetooth
rfkill unblock bluetooth || true
sleep 2
echo "== Pruefung =="
systemctl is-active bluetooth
rfkill list bluetooth || true
bluetoothctl show | head -6 || echo "Kein Bluetooth-Adapter gefunden (Hardware oder Treiber)."
