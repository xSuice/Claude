#!/bin/bash
# Auf dem MA-Server:  sudo bash ~/MA-Server/server/tools/install-office-tools.sh
# Installiert Werkzeuge, mit denen Claude im Portal Dokumente, Praesentationen, Tabellen, PDFs, Bilder und Videos erzeugen kann.
# Pakete aus den Ubuntu-Quellen; nur python-pptx (fehlt in Ubuntu 26.04) kommt per pip aus PyPI in eine eigene Umgebung
# (~/.venvs/office, Benutzer andrew, mit Zugriff auf die System-Pakete). Platz: ca. 1,5 GB. Kein Dienst wird geaendert.
# Rueckgaengig: sudo apt-get remove --purge -y libreoffice-writer libreoffice-impress libreoffice-calc pandoc ffmpeg imagemagick \
#   python3-docx python3-openpyxl python3-reportlab python3-pypdf python3-matplotlib fonts-liberation fonts-dejavu-core \
#   && sudo apt-get autoremove -y && rm -rf ~/.venvs/office
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends \
  libreoffice-writer libreoffice-impress libreoffice-calc pandoc ffmpeg imagemagick \
  python3-venv python3-pip python3-docx python3-openpyxl python3-reportlab python3-pypdf python3-matplotlib \
  fonts-liberation fonts-dejavu-core
sudo -u andrew bash -c 'python3 -m venv --system-site-packages ~/.venvs/office && ~/.venvs/office/bin/pip install --quiet python-pptx'
mkdir -p /srv/ma-home/library/erzeugt
chown andrew:andrew /srv/ma-home/library/erzeugt
echo "== Pruefung =="
for t in soffice pandoc ffmpeg convert; do printf '%s: ' "$t"; command -v "$t" || echo FEHLT; done
sudo -u andrew /home/andrew/.venvs/office/bin/python - <<'EOF'
for m in ("pptx", "docx", "openpyxl", "reportlab", "pypdf", "matplotlib", "PIL"):
    try:
        __import__(m); print(m, "ok")
    except Exception as e:
        print(m, "FEHLT", e)
EOF
echo "Hinweis: Chromium/Playwright (Webseiten-Screenshots) ist hier bewusst nicht dabei (Snap, viel RAM bei 3 GB)."
