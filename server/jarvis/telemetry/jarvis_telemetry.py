"""GET /api/jarvis/telemetry – read-only: PC snapshot (pushed by the PC reporter) + per-unit error summary from journald.
Admin only. Adds no write path. Runs inside ma-home-web."""
import json,subprocess,time
from flask import Blueprint,jsonify,g,abort
import telemetry_core as T

telemetry_bp=Blueprint('jarvis_telemetry',__name__)
PC_FILE='/home/andrew/.local/state/ma-jarvis/pc-telemetry.json'
UNITS=T.safe_units(['ma-home-web','ma-home-agent','ma-claude-bridge','jarvis-watchdog','ma-git-sync','caddy'])
_cache={'t':0,'v':None}

def _logs():
    if _cache['v'] is not None and time.time()-_cache['t']<30:return _cache['v']
    out={}
    for u in UNITS:
        try:
            r=subprocess.run(['journalctl','-u',u,'--since','1 hour ago','-p','err','-o','json','--no-pager','-n','200'],capture_output=True,text=True,timeout=5)
            out[u]=T.summarize_journal(r.stdout) if r.returncode==0 else {'error':'journal nicht lesbar'}
        except Exception:
            out[u]={'error':'journal nicht lesbar'}
    _cache.update(t=time.time(),v=out);return out

@telemetry_bp.route('/api/jarvis/telemetry',methods=['GET'])
def telemetry():
    if not getattr(g,'admin',False):abort(403)
    return jsonify({'pc':T.read_pc(PC_FILE),'logs':{'window':'1 h, Prioritaet err und schlimmer','units':_logs()},'ts':time.time()})
