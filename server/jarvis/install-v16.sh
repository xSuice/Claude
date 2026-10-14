#!/bin/bash
# JARVIS V16 installieren oder aktualisieren - OHNE sudo, als andrew, am MA-Server.
#   bash ~/MA-Server/server/jarvis/install-v16.sh [--src DIR] [--identity NAME] [--no-cron] [--skip-tests]
# Ablauf: 1 Sicherung (Crontab, Konfiguration, aktiver Release) -> 2 neuer Release-Ordner -> 3 Tests des NEUEN Releases
# (bei Fehler bleibt der alte aktiv) -> 4 Ordner/Konfiguration (nur anlegen, nie überschreiben) -> 5 Fähigkeiten-Selbsttest
# -> 6 Umschalten (Symlink current, atomar) -> 7 Cron-Takt (jede Minute, flock, nice/ionice) -> 8 doctor.
# Rückweg: bash ~/MA-Server/server/jarvis/rollback-v16.sh   (Daten bleiben immer erhalten)
set -Eeuo pipefail
SRC="$HOME/MA-Server"; ID="philipp"; CRON=1; TESTS=1
while [ $# -gt 0 ]; do
  case "$1" in
    --src) SRC="$2"; shift 2;; --identity) ID="$2"; shift 2;; --no-cron) CRON=0; shift;; --skip-tests) TESTS=0; shift;;
    *) echo "Unbekannte Option $1"; exit 2;;
  esac
done
[ "$(id -u)" -ne 0 ] || { echo "Bitte NICHT als root ausführen."; exit 1; }
[[ "$ID" =~ ^[a-z][a-z0-9_-]{1,30}$ ]] || { echo "Ungültige Identität"; exit 2; }
umask 077
BASE="$HOME/.local/share/ma-jarvis"; CFGDIR="$HOME/.config/ma-jarvis"; CFG="$CFGDIR/jarvis.json"
DATA="/srv/ma-home/library/.jarvis/v16"; RESULTS="/srv/ma-home/library/JARVIS"; LOGDIR="$HOME/.local/state/ma-jarvis"
REV="$(git -C "$SRC" rev-parse --short HEAD 2>/dev/null || echo local)"
TS="$(date +%Y%m%d-%H%M%S)"; REL="$BASE/releases/$TS-$REV"
mkdir -p "$BASE/releases" "$BASE/backups" "$CFGDIR" "$LOGDIR"

echo "== 1 Sicherung"
B="$BASE/backups/$TS"; mkdir -p "$B"
crontab -l > "$B/crontab.txt" 2>/dev/null || : > "$B/crontab.txt"
[ -f "$CFG" ] && cp -p "$CFG" "$B/jarvis.json"
[ -L "$BASE/current" ] && readlink "$BASE/current" > "$B/current.txt"
[ -f "$DATA/system.db" ] && python3 -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" "$DATA/system.db" "$B/system.db"
[ -f "$DATA/$ID/brain.db" ] && python3 -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" "$DATA/$ID/brain.db" "$B/brain-$ID.db"
# Wiederherstellbarkeit prüfen: Crontab-Kopie identisch, DB-Kopien lesbar und konsistent
diff -q <(crontab -l 2>/dev/null || true) "$B/crontab.txt" >/dev/null || { echo "Sicherung der Crontab nicht identisch - Abbruch"; exit 1; }
for db in "$B"/*.db; do [ -e "$db" ] || continue
  python3 -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'" "$db" || { echo "Sicherung $db defekt - Abbruch"; exit 1; }
done
echo "   gesichert und geprüft: $B"

echo "== 2 Release $REL"
mkdir -p "$REL"
cp -r "$SRC/server/jarvis/core/." "$REL/"
mkdir -p "$REL/router" && cp "$SRC/scripts/router/router_core.py" "$REL/router/"
find "$REL" -name __pycache__ -type d -prune -exec rm -r {} +
chmod -R go-w "$REL"; chmod 700 "$REL"

if [ "$TESTS" = 1 ]; then
  echo "== 3 Tests des neuen Releases (gedrosselt)"
  ( cd "$REL/brain-runtime" && nice -n 15 ionice -c2 -n7 python3 -m unittest discover -s tests > "$B/tests.log" 2>&1 ) \
    || { tail -25 "$B/tests.log"; echo "TESTS ROT - der bisherige Release bleibt aktiv. Log: $B/tests.log"; exit 1; }
  tail -3 "$B/tests.log"
fi

echo "== 4 Ordner und Konfiguration"
mkdir -p "$DATA/$ID" "$DATA/tools" "$RESULTS"
chmod 700 "$DATA" "$DATA/$ID" "$DATA/tools"; chmod 750 "$RESULTS"
if [ ! -f "$CFG" ]; then
  python3 - "$CFG" "$ID" "$DATA" "$RESULTS" "$BASE" <<'PY'
import json, os, sys
cfg, ident, data, results, base = sys.argv[1:6]
c = {"identity": ident, "project": "jarvis", "state_dir": f"{data}/{ident}", "results_dir": results,
     "system_db": f"{data}/system.db", "tools_dir": f"{data}/tools", "claude_bin": os.path.expanduser("~/.local/bin/claude"),
     "router_dir": f"{base}/current/router", "bridge_socket": "/run/ma-claude/bridge.sock",
     "limits": {"claude": {"calls_per_day": 40, "tokens_per_day": 1500000, "identity_calls_per_day": 30, "max_concurrent": 1},
                "helper": {"calls_per_day": 0, "tokens_per_day": 0, "identity_calls_per_day": 0, "max_concurrent": 1},
                "plan_guard": {"five_hour_max_pct": 70, "week_max_pct": 85, "fail_closed": False}},
     "job_defaults": {"claude_calls": 8, "tokens_new": 600000, "wall_s": 14400, "fix_rounds": 2},
     "job_max": {"claude_calls": 20, "tokens_new": 2000000},
     "resources": {"min_mem_mb": 600, "min_mem_heavy_mb": 1200, "max_psi_mem": 10, "max_psi_cpu_heavy": 50,
                   "max_load_per_cpu": 3.0, "max_bridge_jobs": 1},
     "helpers": {"providers": None, "router_mode": "shadow"}, "claude_timeout_s": 900, "claude_max_turns": 30,
     "consolidate_hour": 3}
fd = os.open(cfg, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as fh:
    json.dump(c, fh, indent=1)
PY
  echo "   Konfiguration angelegt: $CFG"
else
  echo "   Konfiguration vorhanden (unverändert): $CFG"
fi
chmod 600 "$CFG"
# Beispiel-Drop-in nur anlegen, wenn noch keins dieses Namens existiert
if [ ! -d "$DATA/tools/wortstatistik" ] && [ -d "$SRC/server/jarvis/dropin-beispiele/wortstatistik" ]; then
  cp -r "$SRC/server/jarvis/dropin-beispiele/wortstatistik" "$DATA/tools/"; chmod 700 "$DATA/tools/wortstatistik"; chmod 600 "$DATA/tools/wortstatistik/"*
fi

echo "== 5 Fähigkeiten erkennen und in der Sandbox selbst testen"
nice -n 15 python3 "$REL/brain-runtime/jarvis_cli.py" --config "$CFG" caps --discover \
  | python3 -c "import json,sys; d=json.load(sys.stdin)['discovered']; print('   builtin:', d['builtin']); print('   drop-in:', d['dropin'], 'abgelehnt:', d['rejected'])"

echo "== 6 Umschalten"
ln -sfn "$REL" "$BASE/current.new" && mv -T "$BASE/current.new" "$BASE/current"
echo "   aktiv: $(readlink "$BASE/current")"

if [ "$CRON" = 1 ]; then
  echo "== 7 Cron-Takt"
  LINE="* * * * * /usr/bin/flock -n $LOGDIR/tick.lock /usr/bin/nice -n 10 /usr/bin/ionice -c2 -n7 /usr/bin/python3 $BASE/current/brain-runtime/jarvis_cli.py --config $CFG tick --max-seconds 50 --log $LOGDIR/tick.log >/dev/null 2>>$LOGDIR/tick.err"
  ( crontab -l 2>/dev/null | grep -v 'ma-jarvis/current/brain-runtime/jarvis_cli.py' || true; echo "$LINE" ) | crontab -
  crontab -l | grep -c jarvis_cli.py | sed 's/^/   Cron-Einträge JARVIS: /'
fi

echo "== 8 doctor"
python3 "$BASE/current/brain-runtime/jarvis_cli.py" --config "$CFG" doctor | python3 -c "import json,sys; d=json.load(sys.stdin); print('   ok:', d['ok'], '| sandbox:', d['sandbox_backend'], '| claude:', d['claude_cli'], '| cron:', d['cron_tick'], '| Fähigkeiten:', d['capabilities'])"
# alte Releases aufräumen (die letzten 5 bleiben)
ls -1d "$BASE/releases/"*/ 2>/dev/null | head -n -5 | while read -r old; do [ "$(readlink -f "$BASE/current")/" != "$old" ] && rm -r "$old"; done
echo "Fertig. Rückweg: bash $SRC/server/jarvis/rollback-v16.sh"
