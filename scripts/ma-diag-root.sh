#!/bin/bash
# MA Home: rein lesende Root-Diagnose. Aendert nichts. Schreibt einen bereinigten Bericht nach ~andrew
# und legt eine Arbeitskopie der NICHT geheimen Web-Dateien daneben (Rechte der produktiven Dateien bleiben unveraendert).
# Aufruf:  sudo bash ma-diag-root.sh
# Geheimnisse (proxy_key, Tokens, Hashes, Passwoerter) werden nicht ausgegeben.
set -uo pipefail
umask 077
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT=/home/andrew/ma-diag-$TS
mkdir -p "$OUT/web"
R="$OUT/report.txt"
redact() { sed -E 's/(X-MA-Key|proxy_key|token|secret|password|passwd|key)([^A-Za-z0-9_]{1,6})[A-Za-z0-9+\/=_.-]{12,}/\1\2<REDACTED>/Ig'; }
sec() { printf '\n===== %s =====\n' "$1" >>"$R"; }

sec "Web-Dateien (sha256, Rechte) und Arbeitskopie"
ls -la /opt/ma-home/web >>"$R" 2>&1
( cd /opt/ma-home/web && sha256sum * ) >>"$R" 2>&1
for f in index.html app.js style.css; do cp /opt/ma-home/web/$f "$OUT/web/$f"; done   # Quelle bleibt unberuehrt (nur lesen)

sec "Portal-/Host-Konfiguration (nur nicht geheime Felder)"
python3 - >>"$R" 2>&1 <<'PY'
import json
p = json.load(open('/etc/ma-home/portal.json'))
print('portal: origin=%s modules=%s users=%s' % (p.get('origin'), json.dumps(p.get('modules')), {u: bool(v.get('admin')) for u, v in p.get('users', {}).items()}))
print('portal keys:', sorted(p))
h = json.load(open('/etc/ma-home/host.json'))
print('host keys:', sorted(h))
for k in ('scanner', 'printer_ready', 'converter_image', 'web_uid'):
    print('host.%s = %s' % (k, h.get(k)))
PY

sec "Docker-Container"
docker ps -a --format '{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' >>"$R" 2>&1
docker stats --no-stream --format '{{.Name}}\tCPU {{.CPUPerc}}\tMEM {{.MemUsage}}' >>"$R" 2>&1

sec "UFW"
ufw status verbose >>"$R" 2>&1

sec "Caddyfile (bereinigt)"
redact </etc/ma-home/Caddyfile >>"$R" 2>&1

sec "Authelia: Zugriffsregeln (bereinigt, ohne Benutzerdatenbank)"
for f in /etc/ma-home/authelia/configuration.yml /etc/ma-home/authelia/configuration.yaml; do
  [ -f "$f" ] && grep -nE 'access_control|default_policy|domain|policy|subject|rules' "$f" | redact >>"$R"
done
ls -la /etc/ma-home/authelia >>"$R" 2>&1

sec "Dienste-Logs (letzte 40 Zeilen, nur Fehler/Warnungen)"
for u in ma-home-web ma-home-agent ma-home-terminal; do echo "--- $u" >>"$R"; journalctl -u $u -p warning -n 40 --no-pager 2>&1 | redact >>"$R"; done
for c in $(docker ps --format '{{.Names}}' 2>/dev/null); do echo "--- docker $c" >>"$R"; docker logs --tail 30 "$c" 2>&1 | grep -iE 'error|fail|denied|refused|panic|warn' | tail -15 | redact >>"$R"; done

sec "Caddy-Zugriffslog: nur Status/Host/Pfad ohne Query, letzte 4xx/5xx"
python3 - >>"$R" 2>&1 <<'PY'
import json, collections
rows = []
try:
    for line in open('/srv/ma-home/caddylogs/access.log', errors='replace').readlines()[-3000:]:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        r = e.get('request', {})
        if e.get('status', 0) >= 400:
            rows.append((e.get('status'), r.get('method'), r.get('host'), r.get('uri', '').split('?')[0][:80]))
except OSError as err:
    print('Log nicht lesbar:', err)
for k, v in collections.Counter(rows).most_common(40):
    print(v, k)
PY

sec "Drucker/Scanner"
lpstat -t >>"$R" 2>&1
sudo -u ma-scan scanimage -L >>"$R" 2>&1

sec "Backup-Hinweise (nur Vorhandensein)"
ls -la /srv/ma-home/backups /etc/ma-home/backup.json /srv/ma-home/backup-status.json >>"$R" 2>&1
ls -la /root/ma-backups >>"$R" 2>&1

chown -R andrew:andrew "$OUT"
chmod -R u+rwX,go-rwx "$OUT"
echo "Fertig: $OUT (report.txt, web/). Produktive Rechte wurden nicht veraendert."
