#!/bin/bash
# Einmal auf dem MA-Server:  sudo bash ~/speicher-erweitern.sh
# Vergroessert das Root-Dateisystem von 100 GB auf die ganze Platte (online, ext4, keine Daten gehen verloren).
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
echo "--- vorher ---"; vgs; lvs; df -h /
lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv
echo "--- nachher ---"; vgs; lvs; df -h /
