#!/bin/bash
# Auf dem MA-Server:  sudo bash ~/MA-Server/server/musik/install.sh
# Richtet "Musik" ein: Navidrome (freie Musik-Streaming-Software, Subsonic-kompatibel) als Docker-Container.
#   Musik:   /srv/ma-home/library/media/musik   (nur lesend eingebunden; dort legst du DEINE Musikdateien ab)
#   Daten:   /srv/ma-home/navidrome/data        (Datenbank, Cache; im Backup mitnehmen)
#   Zugriff: nur 127.0.0.1:4533 – von aussen erst nach einem Caddy-Eintrag mit Authelia (siehe caddy-beispiel.txt)
# Sicherheit: laeuft als andrew (nicht root), alle Capabilities entfernt, Dateisystem schreibgeschuetzt (ausser /data), 512 MB / 1 CPU,
#   Transcoding-Konfiguration per Weboberflaeche AUS (dort koennte man sonst Befehle einschleusen), Teilen AUS, Gravatar AUS.
#   Das Image wird nach dem Herunterladen per Digest festgenagelt (wie bei den anderen Diensten).
# Rueckgaengig: cd /srv/ma-home/navidrome && sudo docker compose down   (Daten bleiben; Ordner loeschen nur nach Rueckfrage)
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
command -v docker >/dev/null || { echo "Docker fehlt."; exit 1; }
BASE=/srv/ma-home/navidrome
MUSIC=/srv/ma-home/library/media/musik
UIDG="$(id -u andrew):$(id -g andrew)"
install -d -o andrew -g andrew -m 755 "$MUSIC"
install -d -o andrew -g andrew -m 750 "$BASE" "$BASE/data"
if [ ! -f "$BASE/compose.yml" ]; then
cat > "$BASE/compose.yml" <<EOF
services:
  navidrome:
    image: deluan/navidrome:latest
    container_name: navidrome
    restart: unless-stopped
    user: "$UIDG"
    ports:
      - "127.0.0.1:4533:4533"
    environment:
      ND_MUSICFOLDER: /music
      ND_DATAFOLDER: /data
      ND_SCANSCHEDULE: 1h
      ND_LOGLEVEL: info
      ND_SESSIONTIMEOUT: 24h
      ND_ENABLETRANSCODINGCONFIG: "false"
      ND_ENABLESHARING: "false"
      ND_ENABLEGRAVATAR: "false"
    volumes:
      - $BASE/data:/data
      - $MUSIC:/music:ro
    mem_limit: 512m
    cpus: 1.0
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    read_only: true
    tmpfs:
      - /tmp
EOF
fi
docker compose -f "$BASE/compose.yml" pull
DIG="$(docker image inspect deluan/navidrome:latest --format '{{index .RepoDigests 0}}' 2>/dev/null || true)"
if [ -n "$DIG" ] && grep -q 'image: deluan/navidrome:latest' "$BASE/compose.yml"; then
  sed -i "s#image: deluan/navidrome:latest#image: $DIG#" "$BASE/compose.yml"
  echo "Image festgenagelt: $DIG"
fi
docker compose -f "$BASE/compose.yml" up -d
sleep 5
docker ps --filter name=navidrome --format 'Container: {{.Names}} {{.Status}}'
curl -s -o /dev/null -w "Navidrome intern: HTTP %{http_code}\n" http://127.0.0.1:4533/ || true
cat <<'TXT'

Fertig. Naechste Schritte:
 1. Musik ablegen: /srv/ma-home/library/media/musik  (z. B. per scp, Filebrowser oder USB). Nur eigene Dateien
    (CDs, Kaeufe wie Bandcamp, freie Musik wie Jamendo oder Free Music Archive). Navidrome liest sie stuendlich ein.
 2. Von aussen erreichbar machen: Block aus caddy-beispiel.txt in die Caddy-Konfiguration uebernehmen (Authelia davor), Caddy neu laden.
 3. Beim ERSTEN Aufruf legt Navidrome den Administrator an: das darf nur jemand tun, der durch Authelia kommt. Also erst Schritt 2, dann aufrufen.
 4. Handy-Apps (Subsonic-kompatibel): z. B. Symfonium (einmal kostenpflichtig), Substreamer oder Tempo (kostenlos). Server-Adresse = deine Musik-Adresse.
TXT
