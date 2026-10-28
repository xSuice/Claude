"""Ingest for the PC telemetry snapshot: reads ONE JSON object on stdin, validates strictly, stores atomically (0600).
Called via ssh by the PC reporter. Exit 2 = rejected input.
KUMA-PUSH: after a valid snapshot, report a heartbeat to the local Uptime-Kuma push monitor (best effort, 2 s)."""
import json,os,sys,urllib.request
sys.path.insert(0,'/opt/jarvis/council')
import telemetry_core as T
PC_FILE='/home/andrew/.local/state/ma-jarvis/pc-telemetry.json'
PUSH_FILE='/home/andrew/.config/ma-jarvis/kuma-pc-push'
try:
    data=T.validate_pc(json.loads(sys.stdin.read(4096)))
except (ValueError,TypeError) as e:
    print('rejected:',e,file=sys.stderr);sys.exit(2)
T.write_pc(PC_FILE,data);print('ok')
try:
    with open(PUSH_FILE,encoding='utf-8') as f:tok=f.read().strip()
    if tok.isascii() and tok.replace('-','').replace('_','').isalnum():
        urllib.request.urlopen('http://127.0.0.1:3001/api/push/'+tok+'?status=up&msg=OK',timeout=2).read()
except (OSError,ValueError):
    pass
