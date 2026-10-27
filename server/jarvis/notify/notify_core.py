"""Pure planning logic for JARVIS push notifications (no I/O, no network, no model calls).
Sends ONLY: incident open >= INCIDENT_MIN_AGE (once), incident resolved (once), newly finished engine jobs (state only).
Never includes job requests/results/free text. First run records a baseline and sends nothing."""
import re

INCIDENT_MIN_AGE = 120 * 60
MAX_PER_RUN = 5
SEEN_MAX = 200
_CTRL = re.compile(r'\x1b\[[0-9;]*[A-Za-z]|[\x00-\x1f\x7f]')
_SECRET = re.compile(r'sk-[A-Za-z0-9_-]{8,}|\b[A-Fa-f0-9]{32,}\b|(?i:bearer\s+\S+)')

def clean(s, limit=60):
    s = _SECRET.sub('[REDACTED]', _CTRL.sub(' ', str(s)))
    s = re.sub(r'\s+', ' ', s).strip()
    return s if len(s) <= limit else s[:limit] + '…'

def _valid(state):
    return isinstance(state, dict) and isinstance(state.get('jobs_seen'), list) and isinstance(state.get('incidents_notified'), dict)

def plan(incidents, jobs_recent, state, now):
    """-> (messages, new_state). messages: [{title,message,priority,tags}]"""
    first = not _valid(state)
    st = {'jobs_seen': list(state['jobs_seen']), 'incidents_notified': dict(state['incidents_notified'])} if not first else {'jobs_seen': [], 'incidents_notified': {}}
    msgs = []
    open_ids = {i.get('incident_id') for i in incidents if i.get('incident_id')}
    if first:
        for i in incidents:
            if i.get('incident_id'): st['incidents_notified'][i['incident_id']] = now
        st['jobs_seen'] = [j['id'] for j in jobs_recent if j.get('id')][-SEEN_MAX:]
        return [], st
    for i in sorted(incidents, key=lambda x: x.get('opened_ts') or 0):
        iid = i.get('incident_id')
        if not iid or iid in st['incidents_notified']: continue
        age = now - (i.get('opened_ts') or now)
        if age >= INCIDENT_MIN_AGE:
            st['incidents_notified'][iid] = now
            msgs.append({'title': 'Incident: ' + clean(i.get('classification')) + ' (' + clean(i.get('subject')) + ')', 'message': 'offen seit ' + str(int(age // 3600)) + ' Std – Details im Command Center', 'priority': 4, 'tags': 'warning'})
    for iid in list(st['incidents_notified']):
        if iid not in open_ids:
            del st['incidents_notified'][iid]
            msgs.append({'title': 'Incident behoben (' + clean(iid) + ')', 'message': 'nicht mehr offen im Watchdog', 'priority': 3, 'tags': 'white_check_mark'})
    seen = set(st['jobs_seen'])
    for j in sorted(jobs_recent, key=lambda x: x.get('finished') or 0):
        jid = j.get('id')
        if not jid or jid in seen: continue
        seen.add(jid); st['jobs_seen'].append(jid)
        bad = str(j.get('state')) in ('failed', 'cancelled', 'partial')
        msgs.append({'title': 'Auftrag ' + clean(jid) + ' ' + clean(j.get('state'), 20), 'message': 'Ergebnis im Portal (JARVIS-Aufträge)', 'priority': 4 if bad else 3, 'tags': 'x' if bad else 'tada'})
    st['jobs_seen'] = st['jobs_seen'][-SEEN_MAX:]
    if len(msgs) > MAX_PER_RUN:
        extra = len(msgs) - (MAX_PER_RUN - 1)
        msgs = msgs[:MAX_PER_RUN - 1] + [{'title': str(extra) + ' weitere Meldungen', 'message': 'Details im Portal', 'priority': 3, 'tags': 'information_source'}]
    return msgs, st
