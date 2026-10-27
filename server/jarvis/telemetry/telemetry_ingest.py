"""Ingest for the PC telemetry snapshot: reads ONE JSON object on stdin, validates strictly, stores atomically (0600).
Called via ssh by the PC reporter. Exit 2 = rejected input."""
import json,sys
sys.path.insert(0,'/opt/jarvis/council')
import telemetry_core as T
PC_FILE='/home/andrew/.local/state/ma-jarvis/pc-telemetry.json'
try:
    data=T.validate_pc(json.loads(sys.stdin.read(4096)))
except (ValueError,TypeError) as e:
    print('rejected:',e,file=sys.stderr);sys.exit(2)
T.write_pc(PC_FILE,data);print('ok')
