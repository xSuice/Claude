#!/usr/bin/env python3
"""JARVIS -> Signal push. Cron every 5 min. Reuses notification baseline; own account only.
Usage: jarvis_notify.py [--dry-run] [--test]"""
import glob,json,os,sqlite3,sys,time
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import notify_core as N
HOME=os.path.expanduser('~')
STATE=os.path.join(HOME,'.local/state/ma-jarvis/notify-state.json')
INC='/opt/jarvis/watchdog/state/open_incidents.json'

def load_state():
    try:return json.load(open(STATE))
    except (OSError,ValueError):return None
def save_state(st):
    os.makedirs(os.path.dirname(STATE),exist_ok=True)
    tmp=STATE+'.tmp';open(tmp,'w').write(json.dumps(st));os.chmod(tmp,0o600);os.replace(tmp,STATE)
def incidents():
    try:raw=json.load(open(INC))
    except (OSError,ValueError):return []
    return [{'incident_id':v.get('incident_id'),'classification':v.get('classification'),'subject':v.get('subject'),'opened_ts':v.get('opened_ts')} for v in raw.values()] if isinstance(raw,dict) else []
def jobs():
    out=[]
    for p in sorted(glob.glob('/srv/ma-home/library/.jarvis/v16/*/brain.db')):
        try:
            c=sqlite3.connect('file:%s?mode=ro'%p,uri=True,timeout=5)
            out+=[{'id':r[0],'state':r[1],'finished':r[2]} for r in c.execute("SELECT id,state,finished FROM jobs WHERE state IN ('done','partial','failed','cancelled') ORDER BY finished DESC LIMIT 20")]
            c.close()
        except Exception:pass
    return out
def send(m):
    from signal_push import send as signal_send
    path=os.path.join(HOME,'.local/share/ma-jarvis/signal/account/data/accounts.json')
    accounts=json.load(open(path))['accounts']
    if len(accounts)!=1:raise RuntimeError('Expected exactly one Signal account')
    return signal_send(m,accounts[0]['number'])
def main():
    a=sys.argv[1:]
    if '--test' in a:
        print('test send:',send({'title':'JARVIS Testnachricht','message':'Wenn du das siehst, funktionieren die Meldungen.','priority':3,'tags':'bell'}));return 0
    msgs,st=N.plan(incidents(),jobs(),load_state(),time.time())
    if '--dry-run' in a:
        print('would send',len(msgs),[m['title'] for m in msgs]);return 0
    ok=True
    for m in msgs:
        try:send(m)
        except Exception as e:
            ok=False;print('send failed:',type(e).__name__);break
    if ok:save_state(st)          # nur nach erfolgreichem Senden: sonst naechster Lauf erneut
    return 0 if ok else 1
if __name__=='__main__':sys.exit(main())
