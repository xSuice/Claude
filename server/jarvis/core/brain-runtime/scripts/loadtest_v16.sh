#!/bin/bash
# JARVIS V16 Lastmessung (Gate F): wechselt Fenster "off" (Cron-Takt entfernt), "idle" (Takt aktiv, kein Auftrag)
# und "load" (echter Auftrag) ab. Je Fenster: Rohdaten (JSONL) + Zusammenfassung; je Auftrag: Status/Events.
#   setsid nohup bash loadtest_v16.sh OUTDIR PLANFILE > OUTDIR/run.log 2>&1 &
# PLANFILE: eine Zeile je Fenster:  off | idle | load <Auftragstext> | load2 <Auftrag A> || <Auftrag B>
#           waitplan <PCT>  = warten, bis das 5h-Fenster des Claude-Plans unter PCT % liegt (max. 4 h)
# Umgebung: W=Fensterlänge s (300), EVERY=Abtastung s (3), COOL=Pause zwischen Fenstern s (30)
# Sicherheit: Die Crontab wird vorher gesichert und bei JEDEM Ende (auch Abbruch) wiederhergestellt.
set -Euo pipefail
OUT="${1:?OUTDIR}"; PLAN="${2:?PLANFILE}"
W="${W:-300}"; EVERY="${EVERY:-3}"; COOL="${COOL:-30}"
BASE="$HOME/.local/share/ma-jarvis"; CFG="$HOME/.config/ma-jarvis/jarvis.json"; LOCK="$HOME/.local/state/ma-jarvis/tick.lock"
CLI=(python3 "$BASE/current/brain-runtime/jarvis_cli.py" --config "$CFG")
MEAS="$(dirname "$(readlink -f "$0")")/measure_v16_load.py"
mkdir -p "$OUT"; umask 077
crontab -l > "$OUT/crontab.orig"
restore() { crontab "$OUT/crontab.orig"; echo "$(date +%T) Crontab wiederhergestellt"; }
trap restore EXIT
log() { echo "$(date +%T) $*"; }

submit() {  # $1 = Auftragstext -> Job-ID
  python3 -c 'import json,sys; print(json.dumps({"request": sys.argv[1], "client_id": "loadtest"}))' "$1" \
    | "${CLI[@]}" submit | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("job_id") or d.get("id") or "ERR")'
}
job_state() {  # -> "state finished"
  "${CLI[@]}" status "$1" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("state"), d.get("finished") or 0)'
}
wait_jobs() {  # Job-IDs ... ; wartet bis alle fertig/blockiert sind (max 25 min)
  local deadline=$(( $(date +%s) + 1500 )) all st fin
  while :; do
    all=1
    for j in "$@"; do
      read -r st fin < <(job_state "$j")
      case "$st" in waiting_approval|waiting_pc) ;; *) [ "$fin" != 0 ] || all=0;; esac
    done
    [ "$all" = 1 ] && return 0
    [ "$(date +%s)" -lt "$deadline" ] || { log "Zeitlimit beim Warten auf $*"; return 1; }
    sleep 15
  done
}
idle_check() {  # kein laufender Takt mit Arbeit: auf freien Lock warten (max 10 min)
  local n=0; until flock -n "$LOCK" true; do sleep 5; n=$((n+1)); [ $n -lt 120 ] || break; done
}

i=0
while IFS= read -r line || [ -n "$line" ]; do
  [[ -z "$line" || "$line" == \#* ]] && continue
  i=$((i+1)); kind="${line%% *}"; rest="${line#* }"; [ "$rest" = "$line" ] && rest=""
  label="$(printf '%02d' $i)-$kind"
  case "$kind" in
    off)
      crontab -l | grep -v 'ma-jarvis/current/brain-runtime/jarvis_cli.py' | crontab -
      idle_check
      log "$label: Takt aus, messe ${W}s"
      python3 "$MEAS" --seconds "$W" --every "$EVERY" --label "$label" --raw "$OUT/$label.jsonl" > "$OUT/$label.json"
      crontab "$OUT/crontab.orig";;
    idle)
      idle_check
      log "$label: Leerlauf mit Takt, messe ${W}s"
      python3 "$MEAS" --seconds "$W" --every "$EVERY" --label "$label" --raw "$OUT/$label.jsonl" > "$OUT/$label.json";;
    load|load2)
      idle_check
      rm -f "$OUT/$label.stop"
      python3 "$MEAS" --seconds 2400 --min-seconds "$W" --stop-file "$OUT/$label.stop" --every "$EVERY" \
        --label "$label" --raw "$OUT/$label.jsonl" > "$OUT/$label.json" &
      mp=$!
      sleep 10
      jobs=()
      if [ "$kind" = load2 ]; then
        jobs+=("$(submit "${rest%% || *}")"); jobs+=("$(submit "${rest#* || }")")
      else
        jobs+=("$(submit "$rest")")
      fi
      log "$label: Aufträge ${jobs[*]}"
      echo "${jobs[*]}" > "$OUT/$label.jobs"
      valid=(); for j in "${jobs[@]}"; do [ "$j" != ERR ] && valid+=("$j"); done
      [ ${#valid[@]} -gt 0 ] && { wait_jobs "${valid[@]}" || true; }
      sleep 30; touch "$OUT/$label.stop"; wait "$mp" || true
      for j in "${jobs[@]}"; do
        [ "$j" = ERR ] && { log "$label: Einreichen gescheitert"; continue; }
        "${CLI[@]}" status "$j" > "$OUT/$label.$j.status.json"
        "${CLI[@]}" events "$j" > "$OUT/$label.$j.events.json"
        log "$label: $j $(job_state "$j")"
      done;;
    waitplan)
      log "warte, bis das 5h-Fenster unter ${rest}% liegt"
      for _ in $(seq 1 480); do
        p="$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); from ledger import bridge_plan_probe; d = bridge_plan_probe()() or {}; print(int((d.get("five") or {}).get("p", 999)))' "$BASE/current/brain-runtime" 2>/dev/null || echo 999)"
        [ "$p" -lt "$rest" ] && break; sleep 30
      done
      log "5h-Fenster bei ${p}%"; continue;;
    *) log "unbekannt: $line"; continue;;
  esac
  sleep "$COOL"
done < "$PLAN"
cp ~/.local/state/ma-jarvis/tick.log "$OUT/tick.log" 2>/dev/null || true
journalctl -t CRON --since "@$(stat -c %Y "$OUT/crontab.orig")" --no-pager 2>/dev/null | grep -c jarvis_cli > "$OUT/cron-runs.txt" || true
log "fertig"
