#!/usr/bin/env bash
# Zeigt den Status aller Docker-Container (laufend und gestoppt).
# Exit-Code: 0 = alles ok, 1 = Docker fehlt/nicht erreichbar, 2 = Warnungen (unhealthy/exited/restarting).
set -u

if ! command -v docker >/dev/null 2>&1; then
  echo "FEHLER: docker ist nicht installiert oder nicht im PATH." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "FEHLER: Docker-Daemon nicht erreichbar (läuft er? Rechte für 'docker'?)." >&2
  exit 1
fi

echo "== Container (alle) =="
docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'

total=$(docker ps -aq | wc -l | tr -d ' ')
running=$(docker ps -q | wc -l | tr -d ' ')
echo
echo "== Zusammenfassung =="
echo "Gesamt: $total | Laufend: $running | Nicht laufend: $((total - running))"

warn=0

unhealthy=$(docker ps -a --filter 'health=unhealthy' --format '{{.Names}}')
if [ -n "$unhealthy" ]; then
  echo
  echo "WARNUNG unhealthy:"
  echo "$unhealthy" | sed 's/^/  - /'
  warn=1
fi

bad=$(docker ps -a --filter 'status=exited' --filter 'status=restarting' --filter 'status=dead' \
  --format '{{.Names}} ({{.Status}})')
if [ -n "$bad" ]; then
  echo
  echo "WARNUNG nicht laufend / neu startend:"
  echo "$bad" | sed 's/^/  - /'
  warn=1
fi

[ "$warn" -eq 0 ] && echo "Alles ok." || exit 2
