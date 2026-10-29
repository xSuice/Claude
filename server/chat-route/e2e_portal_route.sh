#!/usr/bin/env bash
# Portal-E2E der Chat-Weiche (Server-Rollen). Gibt nur Ziel/Text/Ergebnis aus, keine Schlüssel.
K=$(python3 -c "import json;print(json.load(open('/etc/ma-home/portal.json'))['proxy_key'])")
t0=$(date +%s)
curl -s -N -m 290 -H "X-MA-Key: $K" -H "Remote-User: andrew" -H "Origin: https://ma-server.duckdns.org" -H "X-MA-Request: 1" -H "Content-Type: application/json" \
  -d "{\"prompt\":\"$1\",\"mode\":\"lesen\",\"dir\":\"notizen\"}" http://127.0.0.1:18765/api/claude | python3 -c "
import sys,json
for l in sys.stdin:
    l=l.strip()
    if l.startswith('data:'): l=l[5:].strip()
    try: d=json.loads(l)
    except ValueError: continue
    t=d.get('type')
    if t=='bridge_model': print('wer:',d.get('model'))
    elif t=='stream_event' and d['event'].get('delta',{}).get('text'): print('Text:',d['event']['delta']['text'][:400].replace(chr(10),' / '))
    elif t=='result': print('Ergebnis: is_error=%s route=%s'%(d.get('is_error'),d.get('ma_route')))"
echo "[$(( $(date +%s)-t0 )) s]"; tail -1 ~/.local/share/ma-claude/route-log.jsonl
