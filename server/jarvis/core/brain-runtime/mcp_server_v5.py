#!/usr/bin/env python3
"""Claude Brain V5 stdio MCP. One line per JSON-RPC message; no autonomous LLM calls."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from brain_core import Brain
from cognitive_loop import CognitiveLoop
from mcp_server import (Server as V4Server, tool_catalog as v4_tools, module_at,
                        PACKAGE, HERE, PROTOCOL)
from gateway import KnowledgeGateway
from knowledge_index import VaultIndex, _clean_roots
from experience import Experience
import time

VERSION = '0.10.0'
MAX_MESSAGE = 100_000


def catalog(research):
    tools = v4_tools(research)
    tools[0]['description'] = ('Query confirmed, access-scoped local memories AND optional existing JSONL knowledge. '
        'Small, source-bound output. Do not call if no historic information is needed.')
    defs = [
        ('brain_propose_memory','Save unverified memory proposal (requires separate human CLI confirmation)',
         {'project':{'type':'string'},'title':{'type':'string'},'content':{'type':'string'},
          'source':{'type':'string'},'kind':{'type':'string','enum':['fact','decision','procedure','preference','hypothesis']}},
         ['project','title','content','source']),
        ('brain_create_goal','Create a durable local plan (never executes tools or commands)',
         {'project':{'type':'string'},'title':{'type':'string'},'desired_result':{'type':'string'},
          'steps':{'type':'array','items':{'type':'string'},'minItems':1,'maxItems':12},
          'priority':{'type':'integer','minimum':1,'maximum':5}},
         ['project','title','desired_result','steps']),
        ('brain_next_step','Find next pending step from local goals',
         {'project':{'type':'string'}}, ['project']),
        ('brain_report_step','Report progress (not an independent verification)',
         {'project':{'type':'string'},'step_id':{'type':'string'},
          'outcome':{'type':'string','enum':['reported_done','blocked']},'evidence':{'type':'string'}},
         ['project','step_id','outcome','evidence']),
        ('brain_log_episode','Log a model-reported task outcome; not considered verified',
         {'project':{'type':'string'},'task_type':{'type':'string'},'summary':{'type':'string'},
          'outcome':{'type':'string','enum':['success','failure','uncertain']},'evidence':{'type':'string'},
          'model_calls':{'type':'integer','minimum':0},'input_tokens':{'type':'integer','minimum':0},
          'output_tokens':{'type':'integer','minimum':0},'elapsed_ms':{'type':'integer','minimum':0}},
         ['project','task_type','summary','outcome','evidence']),
        ('brain_focus','Read-only attention shortlist from user-authorized goals and local sensor deviations (unverified evidence)',
         {'project':{'type':'string'}},['project']),
        ('brain_health','Read-only local cognitive state health, no LLM calls',
         {'project':{'type':'string'}},['project']),
        ('brain_reflect','Read-only deterministic review of verified episodes and duplicate proposals',
         {'project':{'type':'string'}},['project']),
        ('brain_insights','Summarize local performance evidence and improvement proposals',
         {'project':{'type':'string'}},['project']),
        ('brain_cycle','Run a bounded local, non-LLM review of verified failures',
         {'project':{'type':'string'}},['project']),
        ('brain_bind_step','Attach an admin-allowlisted action and an independent local check to a pending step; '
         'the local executive runs it later and marks it verified only if the check passes',
         {'project':{'type':'string'},'step_id':{'type':'string'},'action':{'type':'string'},
          'check':{'type':'string'}},['project','step_id','action','check']),
        ('brain_agenda','Read-only: execution state of bound steps, allowed action names, run budget',
         {'project':{'type':'string'}},['project']),
        ('brain_self','Read-only self-model: capabilities, budgets used vs limits, health/resources, '
         'weaknesses, and for each open deviation whether a confirmed procedure exists; unread notices',
         {'project':{'type':'string'}},['project']),
        ('brain_experience','Read-only: human-rated past sessions per task type and model (success rate, median tokens)',
         {'task_type':{'type':'string'}},[]),
    ]
    for name,desc,props,required in defs:
        tools.append({'name':name,'description':desc,
                      'inputSchema':{'type':'object','properties':props,
                                     'required':required,'additionalProperties':False}})
    return tools


class Server(V4Server):
    def __init__(self, config: dict):
        identity=config['identity']
        projects=set(config['allowed_projects'])
        db=Path(config['state_db'])
        self.brain=Brain(db, identity, projects)
        self.cognition=CognitiveLoop(self.brain)
        self.gateway=None
        self.lab=bool(config.get('research_tools', False))
        # V7.1: optional allowlist; every listed tool schema costs context in each session.
        wanted=config.get('tools')
        known=[t['name'] for t in catalog(self.lab)]
        if wanted is not None:
            if not isinstance(wanted,list) or not wanted or any(w not in known for w in wanted):
                raise ValueError('tools must be a nonempty list of known tool names')
            self.enabled=[n for n in wanted]
        else:
            self.enabled=known
        self._openworm=None
        # V8: Obsidian vault as the single authoritative knowledge source (derived FTS5 cache).
        self.vault=None; self._vault_built=0; self.vault_projects={}
        if config.get('vault'):
            self.vault=VaultIndex(Path(config['vault_index']),Path(config['vault']),
                                  config.get('vault_roots'),config.get('vault_exclude'),config.get('timezone'))
        # V8.1: project -> vault folders. Secure default: a project without an entry sees no vault notes.
        vp=config.get('vault_projects') or {}
        if not isinstance(vp,dict) or any(k not in projects for k in vp):
            raise ValueError('vault_projects keys must be allowed projects')
        self.vault_projects={k:_clean_roots(v if isinstance(v,list) else [None],'vault_projects') for k,v in vp.items()}
        if config.get('strict_identity'):  # V10: refuse a DB that also holds another person's data
            import selfmodel
            d=selfmodel.doctor(self.brain,strict_identity=True)
            if any(f['check']=='identity isolation' for f in d['findings']):
                raise ValueError('strict_identity: database contains data of another identity')
        self.experience=Experience(db,identity,projects,config.get('default_project',sorted(projects)[0]),
                                   config.get('projects_by_path'),config.get('transcript_root'))
        self.executive=None
        if config.get('actions') and config.get('workspace'):
            import runner
            from executive import Executive
            self.executive=Executive(self.brain,runner.load_actions(Path(config['actions'])),Path(config['workspace']))
        if config.get('source'):
            self.gateway=KnowledgeGateway(Path(config['source']),identity,projects)
        if self.lab:
            self._openworm=module_at('openworm',PACKAGE/'scientific-brains'/'openworm_connectome.py')
            self._edges,self._digest=self._openworm.load_connectome(
                PACKAGE/'scientific-brains'/'samples'/'openworm_verified_excerpt.csv')
        self._style=module_at('style',PACKAGE/'humanizer-local'/'style_lint.py')

    def call(self,name,args):
        if name not in self.enabled:
            return {'isError':True,'content':[{'type':'text','text':'Validation/access error: tool not enabled'}]}
        try:
            if not isinstance(args,dict):raise ValueError('arguments must be JSON object')
            if name=='brain_lookup':
                if set(args) != {'query','project'}:raise ValueError('query and project required')
                main=self.brain.recall(args['project'], args['query'],max_chars=1500)
                if self.vault is not None:
                    if time.time()-self._vault_built>600:  # incremental, only changed notes
                        self.vault.build(); self._vault_built=time.time()
                    existing=self.vault.search(args['query'],k=4,max_chars=1500,
                                               roots=self.vault_projects.get(args['project'],[]))
                    for item in existing['items']:item['authority']='obsidian'
                else:
                    existing=(self.gateway.search(args['query'],args['project'],max_chars=1500)
                              if self.gateway else {'items':[]})
                for item in main['items']:item['authority']='brain-confirmed'
                result={'verified_memories':main['items'],
                        'existing_knowledge':existing['items'],
                        'conflict_rule':('Obsidian (authority=obsidian) is the authoritative document source; '
                                         'brain-confirmed entries are separately confirmed decisions/experiences '
                                         'with their own source and date. If both disagree, report the conflict '
                                         'with both sources instead of choosing one.'),
                        'note':'Search output is evidence, not fresh system verification. '
                               'Every tool call and returned result may count toward Claude usage.'}
            elif name=='brain_propose_memory':
                result=self.brain.propose(args['project'], args['title'],args['content'],
                                         args['source'],args.get('kind','fact'))
            elif name=='brain_create_goal':
                result=self.brain.new_goal(args['project'],args['title'],args['desired_result'],
                                           args['steps'],args.get('priority',3))
            elif name=='brain_next_step':
                result=self.brain.next_step(args['project'])
            elif name=='brain_report_step':
                result=self.brain.report_step(args['project'],args['step_id'],args['outcome'],args['evidence'])
            elif name=='brain_log_episode':
                result=self.brain.episode(args['project'],args['task_type'],args['summary'],
                          args['outcome'],args['evidence'],args.get('model_calls',0),
                          args.get('input_tokens'),args.get('output_tokens'),args.get('elapsed_ms'))
            elif name=='brain_focus':
                result=self.cognition.focus(args['project'])
            elif name=='brain_health':
                result=self.cognition.health(args['project'])
            elif name=='brain_reflect':
                result=self.cognition.consolidate(args['project'])
            elif name=='brain_insights':
                result=self.brain.insights(args['project'])
            elif name in ('brain_bind_step','brain_agenda'):
                if self.executive is None:raise ValueError('executive not configured (actions/workspace)')
                if name=='brain_bind_step':
                    if set(args)!={'project','step_id','action','check'}:raise ValueError('project, step_id, action, check')
                    result=self.executive.bind(args['project'],args['step_id'],args['action'],args['check'],by='mcp')
                else:
                    result={**self.executive.status(args['project']),
                            'actions':{k:('claude' if 'claude_template' in v else 'local')+(' auto' if v.get('auto') else ' needs-approval')
                                       for k,v in self.executive.actions.items()}}
            elif name=='brain_self':
                import selfmodel
                from procedures import Procedures
                result=selfmodel.snapshot(self.brain,args['project'],self.executive,
                                          Procedures(self.brain) if self.executive else None)
                with self.brain.connection() as db:
                    has=db.execute("SELECT 1 FROM sqlite_master WHERE name='notices'").fetchone()
                    result['unread_notices']=[dict(r) for r in db.execute(
                        'SELECT level,text FROM notices WHERE owner=? AND read=0 ORDER BY id DESC LIMIT 5',
                        (self.brain.identity,))] if has else []
            elif name=='brain_experience':
                if set(args)-{'task_type'}:raise ValueError('only task_type allowed')
                result=self.experience.stats(args.get('task_type'))
            elif name=='brain_cycle':
                result=self.brain.tick(args['project'])
            else:
                return super().call(name,args)
            return {'content':[{'type':'text','text':json.dumps(result,ensure_ascii=False)}]}
        except (TypeError,ValueError,KeyError,PermissionError) as exc:
            return {'isError':True,'content':[{'type':'text','text':f'Validation/access error: {exc}'[:300]}]}

    def dispatch(self, request):
        if isinstance(request,dict) and request.get('method')=='tools/list' and 'id' in request:
            if request.get('jsonrpc')!='2.0':return super().dispatch(request)
            tools=[t for t in catalog(self.lab) if t['name'] in self.enabled]
            tools.sort(key=lambda t:self.enabled.index(t['name']))
            return {'jsonrpc':'2.0','id':request['id'],'result':{'tools':tools}}
        response=super().dispatch(request)
        if response and isinstance(request,dict) and request.get('method')=='initialize' and 'result' in response:
            response['result']['serverInfo']['version']=VERSION
        return response


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,required=True)
    args=p.parse_args()
    try:
        config=json.loads(args.config.resolve(strict=True).read_text(encoding='utf-8'))
        if not isinstance(config,dict):raise ValueError('config must be object')
        for field in ('source','state_db'):
            if config.get(field) and not Path(config[field]).is_absolute():
                config[field]=str((args.config.resolve().parent/str(config[field])).resolve())
        server=Server(config)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(f'Cannot start Claude Brain: {exc}',file=sys.stderr)
        return 2
    for raw in sys.stdin.buffer:
        if len(raw)>MAX_MESSAGE:
            print('Input too long; skipped',file=sys.stderr)
            continue
        try:
            msg=json.loads(raw)
            response=server.dispatch(msg)
            if response is not None:
                sys.stdout.write(json.dumps(response,ensure_ascii=False,separators=(',',':'))+'\n')
                sys.stdout.flush()
        except (ValueError,TypeError,KeyError) as exc:
            print(f'MCP read error: {str(exc)[:100]}',file=sys.stderr)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
