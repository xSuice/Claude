#!/bin/bash
# Root-Dienst ma-job-notify: schickt die von der Claude-Bruecke abgelegten Meldungen (/srv/ma-home/deploy/notify/*.msg)
# per ma-notify (ntfy) aufs Handy und loescht sie. Zeile 1 = Titel, Zeile 2 = kurzer Auszug der Anfrage.
# Nur normale Dateien, Steuerzeichen entfernt (kein Header-Einschleusen), feste Laengen. Ohne ma-notify/Token passiert nichts ausser Aufraeumen.
D=/srv/ma-home/deploy/notify
for f in "$D"/*.msg; do
  [ -e "$f" ] || continue
  if [ -f "$f" ] && [ ! -L "$f" ]; then
    t=$(sed -n 1p "$f" | head -c 60 | tr -d '\000-\037')
    m=$(sed -n 2p "$f" | head -c 100 | tr -d '\000-\037')
    [ -x /usr/local/sbin/ma-notify ] && /usr/local/sbin/ma-notify "${t:-Claude}" "$m" 3 || true
  fi
  rm -f "$f"
done
exit 0
