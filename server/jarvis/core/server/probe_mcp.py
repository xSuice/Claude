#!/usr/bin/env python3
"""Check the real MCP subprocess framing, startup and tools without Claude tokens."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

def check(config, runtime):
    reqs=[
        {'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'ma-server-test','version':'1'}}},
        {'jsonrpc':'2.0','method':'notifications/initialized'},
        {'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}},
        {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'brain_lookup','arguments':{'project':'ma-home','query':'Testfrage Project Server'}}},
    ]
    data='\n'.join(json.dumps(r) for r in reqs)+'\n'
    proc=subprocess.run([sys.executable,str(runtime/'mcp_server_v5.py'),'--config',str(config)],
        input=data,text=True,capture_output=True,timeout=15)
    if proc.returncode!=0: raise AssertionError(proc.stderr)
    msgs=[json.loads(x) for x in proc.stdout.splitlines() if x.strip()]
    result={m.get('id'):m for m in msgs}
    assert set(result)=={1,2,3},result
    assert 'result' in result[1] and 'result' in result[2],result
    names={x['name'] for x in result[2]['result']['tools']}
    assert {'brain_lookup','brain_create_goal','brain_log_episode'}<=names,names
    assert 'result' in result[3],result[3]
    return {'tools':len(names),'returned_items':len(result[3]['result']['content']), 'status':'pass'}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--runtime',type=Path,default=Path(__file__).resolve().parents[1]/'brain-runtime')
    a=p.parse_args()
    print(json.dumps(check(a.config.resolve(),a.runtime.resolve()),indent=2))
