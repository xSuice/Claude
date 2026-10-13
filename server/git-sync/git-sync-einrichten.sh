#!/usr/bin/env bash
# Deploy-Key fuer GitHub erzeugen (als andrew, kein Sudo) und den OEFFENTLICHEN Teil anzeigen.
# Der private Schluessel bleibt in ~/.config/ma-github und kommt nie ins Repo (.gitignore: *.key; Pruefung in git-sync.py).
# Danach: Repo-Adresse eintragen:  echo 'git@github.com:BENUTZER/REPO.git' > ~/.config/ma-github/repo
# Rueckweg: rm -r ~/.config/ma-github und den Deploy-Key in GitHub loeschen.
set -euo pipefail
D="$HOME/.config/ma-github"
install -d -m 0700 "$D"
if [ ! -f "$D/deploy_ed25519" ]; then
  ssh-keygen -t ed25519 -N '' -C "ma-server deploy $(date +%F)" -f "$D/deploy_ed25519" >/dev/null
  echo "Schluessel erzeugt."
else
  echo "Schluessel gab es schon (unveraendert)."
fi
echo "--- OEFFENTLICHER Schluessel (in GitHub: Repo > Settings > Deploy keys > Add, 'Allow write access' anhaken) ---"
cat "$D/deploy_ed25519.pub"
