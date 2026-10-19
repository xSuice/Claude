"""Pure PUBLIC M1a diagnosis rules; no model, I/O, oracle, family or template input.

Receipts certify the declared synthetic diagnostic rules, not general real-world
causality. Production integration/authorization and OS isolation are separate gates.
"""


from datetime import datetime
import re
import math


def _number(value):
    return type(value) in (int,float) and value>=0 and (type(value) is int or math.isfinite(value))

READ_TOOLS = frozenset({'service_status','service_readiness','read_config','read_logs'})
OBS_KEYS = frozenset({'id','tool','available_at_step','captured_at','payload'})
# Public fixture vocabulary, fixed independently of individual cases. No generator import.
CAPACITY_RULES = (
 ('max_connections','pool_size','connection_limit_below_pool'),
 ('nofile_limit','worker_count','fd_limit_below_workers'),
 ('queue_max_len','burst_size','queue_capacity_below_burst'),
 ('maxmemory_mb','working_set_mb','cache_memory_below_working_set'),
 ('max_threads','concurrency','thread_limit_below_concurrency'),
 ('disk_quota_mb','retention_mb','disk_quota_below_retention'),
 ('rate_limit_rps','client_rps','rate_limit_below_client_load'),
 ('job_timeout_s','job_duration_s','job_timeout_below_duration'),
 ('max_body_kb','upload_kb','body_limit_below_upload'),
 ('max_streams','subscribers','stream_limit_below_subscribers'),
 ('tmpfs_mb','scratch_mb','tmpfs_below_scratch_need'),
 ('max_cursors','query_parallelism','cursor_limit_below_parallelism'),
 ('heap_mb','batch_mb','heap_below_batch_size'),
 ('max_children','parallel_requests','child_limit_below_requests'))
READINESS_REASONS=frozenset({'dependency_not_ready','cache_warmup_incomplete','migration_pending',
 'certificate_reload_failed','queue_consumer_stalled','config_reload_pending','disk_pressure_throttling',
 'lock_contention','index_rebuild_running','leader_election_pending','snapshot_restore_running','token_refresh_failing'})
STALE_SECONDS=600


def _fresh(o):
    age=o['payload'].get('checked_s_ago',0)
    return _number(age) and age<=STALE_SECONDS


def valid_observations(observations, user_context, step):
    if (not isinstance(observations,list) or not isinstance(user_context,str)
            or type(step) is not int or step<0):
        return False
    seen=set()
    for o in observations:
        if not isinstance(o,dict) or set(o)!=OBS_KEYS:
            return False
        oid=o['id']
        if not isinstance(oid,str) or not oid or oid in seen:
            return False
        seen.add(oid)
        if (not isinstance(o['tool'],str) or o['tool'] not in READ_TOOLS|{'tool_result'}
                or not isinstance(o['payload'],dict)
                or type(o['available_at_step']) is not int
                or not 0<=o['available_at_step']<=step):
            return False
        service=o['payload'].get('service')
        payload=o['payload']
        if 'lines' in payload and (not isinstance(payload['lines'],list)
                or any(not isinstance(line,str) for line in payload['lines'])):
            return False
        if 'checked_s_ago' in payload and not _number(payload['checked_s_ago']):
            return False
        if service is not None and (not isinstance(service,str) or not service):
            return False
        try:
            if datetime.fromisoformat(o['captured_at'].replace('Z','+00:00')).utcoffset() is None:
                return False
        except (AttributeError,ValueError,TypeError):
            return False
    return True


def _mentions(text, service):
    return bool(re.search(r'(?<![\w-])'+re.escape(service)+r'(?![\w-])',text))


def _receipt(status='ABSTAIN', cause=None, proof=()):
    return {'status': status, 'cause_id': cause,
            'proof_observation_ids': sorted(set(proof))}


def diagnose(observations, user_context, *, step=0):
    if not valid_observations(observations,user_context,step):
        return _receipt()
    services={o['payload']['service'] for o in observations if 'service' in o['payload']}
    targets=[s for s in services if _mentions(user_context,s)]
    if len(targets)!=1:
        return _receipt()
    target=targets[0]
    # Host read generation first, timestamp second; never trust list position.
    # A simultaneous contradiction cannot be resolved by choosing a convenient value.
    active=[]
    groups={}
    for o in observations:
        if o['tool'] in {'service_status','service_readiness','read_config'}:
            groups.setdefault((o['tool'],o['payload'].get('service')),[]).append(o)
        else:
            active.append(o)
    for group in groups.values():
        rank=lambda o:(o['available_at_step'],datetime.fromisoformat(o['captured_at'].replace('Z','+00:00')))
        latest=max(map(rank,group))
        current=[o for o in group if rank(o)==latest]
        if current[0]['tool']=='read_config':
            # Simultaneous partial snapshots may add fields, but conflicting
            # values cannot be resolved by ID/order or by selecting a failure.
            for index,left in enumerate(current):
                for right in current[index+1:]:
                    overlap=set(left['payload']) & set(right['payload'])
                    if any(left['payload'][key] != right['payload'][key] for key in overlap):
                        return _receipt('OBSERVATION_CONFLICT',proof=[o['id'] for o in current])
            active.extend(sorted(current,key=lambda o:o['id']))
            continue
        states=[o['payload'].get('state') for o in current]
        if any(value!=states[0] for value in states[1:]):
            return _receipt('OBSERVATION_CONFLICT',proof=[o['id'] for o in current])
        active.append(min(current,key=lambda o:o['id']))
    observations=active
    target_logs=[o for o in observations if o['tool']=='read_logs' and o['payload'].get('service')==target]
    text='\n'.join(line for o in target_logs for line in o['payload'].get('lines',[]) if isinstance(line,str))
    stopped=[o for o in observations if o['tool']=='service_status'
             and o['payload'].get('service')!=target
             and o['payload'].get('state') in ('stopped','failed','inactive')
             and isinstance(o['payload'].get('service'),str)
             and _mentions(text,o['payload']['service'])]
    if stopped:
        return _receipt('VERIFIED_DIAGNOSIS','dependency_not_running',[min(stopped,key=lambda o:o['id'])['id']])
    configs=[o for o in observations if o['tool']=='read_config'
             and o['payload'].get('service')==target and o['payload'].get('parse_ok') is False]
    if configs:
        return _receipt('VERIFIED_DIAGNOSIS','config_value_invalid',[min(configs,key=lambda o:o['id'])['id']])
    configs_all=[o for o in observations if o['tool']=='read_config']
    for capacity_key,demand_key,cause in CAPACITY_RULES:
        for demand in configs_all:
            amount=demand['payload'].get(demand_key)
            if demand['payload'].get('service')!=target or not _number(amount):
                continue
            limits=[o for o in configs_all if _number(o['payload'].get(capacity_key))]
            limits.sort(key=lambda o:(o['payload'][capacity_key],o['id']))
            if limits and amount>limits[0]['payload'][capacity_key]:
                return _receipt('VERIFIED_DIAGNOSIS',cause,[demand['id'],limits[0]['id']])
    errors=[o for o in target_logs if any(isinstance(line,str) and re.search(r'\bERROR\b',line,re.I)
             for line in o['payload'].get('lines',[]))]
    for o in observations:
        reason=o['payload'].get('reason')
        normalized=reason.lower().replace(' ','_') if isinstance(reason,str) else None
        relevant=((o['tool']=='service_readiness' and o['payload'].get('service')==target)
                  or (o['tool']=='service_status' and o['payload'].get('service')!=target
                      and o['payload'].get('state')=='degraded'))
        if errors and relevant and _fresh(o) and normalized in READINESS_REASONS:
            return _receipt('VERIFIED_DIAGNOSIS',normalized,[errors[0]['id'],o['id']])
    stale=[o for o in observations if o['tool']=='service_status'
           and o['payload'].get('service')==target and not _fresh(o)]
    if stale and errors:
        return _receipt('OBSERVATION_CONFLICT',proof=[stale[0]['id'],errors[0]['id']])
    status=[o for o in observations if o['tool']=='service_status' and _fresh(o)
            and o['payload'].get('service')==target and o['payload'].get('state')=='running']
    ready=[o for o in observations if o['tool']=='service_readiness' and _fresh(o)
           and o['payload'].get('service')==target and o['payload'].get('state')=='ready']
    if status and ready:
        return _receipt('VERIFIED_DIAGNOSIS','service_healthy',[status[0]['id'],ready[0]['id']])
    return _receipt()


def preflight(observations, user_context):
    status=diagnose(observations,user_context,step=0)['status']
    if status=='OBSERVATION_CONFLICT':
        return 'D_OBSERVATION_CONFLICT'
    return 'D_CLEAR' if status=='VERIFIED_DIAGNOSIS' else 'D_ABSTAIN'


def select_read(state):
    """Rank authorized concrete reads by visible diagnostic need, never fixture identity."""
    import itertools
    import json
    if not isinstance(state,dict) or set(state)!={'user_context','observations','tool_catalog','read_budget','reads_used','read_keys'}:
        return None
    budget,used=state['read_budget'],state['reads_used']
    if type(budget) is not int or type(used) is not int or not 0<=used<budget:
        return None
    prior=state['read_keys']
    if (not isinstance(prior,list) or any(not isinstance(k,str) for k in prior)
            or len(prior)!=used or len(set(prior))!=used
            or not valid_observations(state['observations'],state['user_context'],used)):
        return None
    catalog=state['tool_catalog']
    if not isinstance(catalog,list):
        return None
    options=[]
    tools=set()
    for entry in catalog:
        if not isinstance(entry,dict) or set(entry)!={'tool','params'}:
            return None
        tool,spec=entry['tool'],entry['params']
        if not isinstance(tool,str) or tool not in READ_TOOLS or tool in tools or not isinstance(spec,dict):
            return None
        tools.add(tool)
        if 'service' not in spec or len(spec)>4:
            return None
        for key,values in spec.items():
            if (not isinstance(key,str) or not isinstance(values,list) or not values
                    or len(values)>64 or any(not isinstance(v,str) or not v for v in values)
                    or len(values)!=len(set(values))):
                return None
        size=math.prod(len(v) for v in spec.values())
        if size+len(options)>1024:
            return None
        keys=sorted(spec)
        for values in itertools.product(*(sorted(spec[k]) for k in keys)):
            params=dict(zip(keys,values))
            canonical=json.dumps([tool,sorted(params.items())],ensure_ascii=False)
            if canonical not in prior:
                options.append((tool,params,canonical))
    services={p['service'] for _,p,_ in options}
    services.update(o['payload'].get('service') for o in state['observations'])
    targets=[s for s in services if isinstance(s,str) and _mentions(state['user_context'],s)]
    if len(targets)!=1:
        return None
    target=targets[0]
    visible=state['observations']
    target_obs=[o for o in visible if o['payload'].get('service')==target]
    logs='\n'.join(line for o in target_obs for line in o['payload'].get('lines',[]))
    demands={k for _,k,_ in CAPACITY_RULES for o in target_obs
             if o['tool']=='read_config' and _number(o['payload'].get(k))}
    stale=any(o['tool']=='service_status' and not _fresh(o) for o in target_obs)
    def priority(option):
        tool,params,canonical=option
        service=params['service']
        same=service==target
        score={'service_readiness':70,'service_status':60,'read_config':50,'read_logs':30}[tool]+(20 if same else 0)
        if demands and tool=='read_config' and not same:
            score=120+(5 if 'pool_size' in demands and re.search(r'(^|[-_])(db|database|sql)([-_]|$)',service,re.I) else 0)
        if stale and same and tool=='service_readiness':
            score=150
        if re.search(r'parse|invalid|config|crash',logs,re.I) and same and tool=='read_config':
            score=145
        if re.search(r'connect.*refused',logs,re.I) and not same and _mentions(logs,service) and tool=='service_status':
            score=160
        if not demands and re.search(r'timeout|timed out|upstream',logs,re.I) and same and tool=='read_config' and not stale:
            score=135
        if any(o['tool']==tool and o['payload'].get('service')==service and _fresh(o) for o in visible) and tool!='read_logs':
            score-=90
        if tool=='read_logs' and params.get('window')=='last_5m':
            score+=5
        return (-score,canonical)
    if not options:
        return None
    tool,params,_=min(options,key=priority)
    return {'tool':tool,'params':params}

