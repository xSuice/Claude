#!/bin/bash
# Auf dem MA-Server:  sudo bash ~/MA-Server/server/tools/install-office-tools.sh
# Installiert Werkzeuge, mit denen Claude im Portal Dokumente, Praesentationen, Tabellen, PDFs, Bilder und Videos erzeugen kann.
# Nur Pakete aus den Ubuntu-Quellen (kein pip aus dem Netz). Platz: ca. 1,5 GB. Kein Dienst wird geaendert.
# Rueckgaengig: sudo apt-get remove --purge -y libreoffice-writer libreoffice-impress libreoffice-calc pandoc ffmpeg imagemagick \
#   python3-pptx python3-docx python3-openpyxl python3-reportlab python3-pypdf python3-matplotlib fonts-liberation fonts-dejavu-core \
#   && sudo apt-get autoremove -y
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends \
  libreoffice-writer libreoffice-impress libreoffice-calc pandoc ffmpeg imagemagick \
  python3-pptx python3-docx python3-openpyxl python3-reportlab python3-pypdf python3-matplotlib \
  fonts-liberation fonts-dejavu-core
mkdir -p /srv/ma-home/library/erzeugt
chown andrew:andrew /srv/ma-home/library/erzeugt
echo "== Pruefung =="
for t in soffice pandoc ffmpeg convert; do printf '%s: ' "$t"; command -v "$t" || echo FEHLT; done
sudo -u andrew python3 - <<'EOF'
for m in ("pptx", "docx", "openpyxl", "reportlab", "pypdf", "matplotlib", "PIL"):
    try:
        __import__(m); print(m, "ok")
    except Exception as e:
        print(m, "FEHLT", e)
EOF
echo "Hinweis: Chromium/Playwright (Webseiten-Screenshots) ist hier bewusst nicht dabei (Snap, viel RAM bei 3 GB)."
