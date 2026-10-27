/* MA-HOME HQ — gemeinsamer Daten-Store (M3 Living HQ; M4 Command Center nutzt denselben Store).
   Quelle ausschliesslich echte API-Daten. Events entstehen NUR aus Zustandsaenderungen zwischen zwei Polls
   (keine erfundene Aktivitaet). Polling nur, solange mindestens ein Abonnent aktiv ist und der Tab sichtbar ist. */

export const STALE_MS = 10 * 60000;          // wie im Bestand: Heartbeat aelter als 10 Min = veraltet
const POLL_MS = 5000;

export const S = {
  agents: [],            // [{agent,last_heartbeat,status}]
  tasks: [],             // [{task_id,title,status,assigned_to,created,updated,priority}]
  incidents: [],         // [{incident_id,classification,subject,state,age_min,...}]
  engine: { active: [], recent: [] },
  ts: null, error: null, loaded: false, polls: 0,
  events: []             // [{t,type,agent,text,sev}]  neueste zuerst
};

const subs = new Set();
let timer = null, busy = false, prev = null;

try { S.events = JSON.parse(sessionStorage.getItem('hq-events') || '[]'); } catch (e) { S.events = []; }

export const isFresh = a => !!(a && a.last_heartbeat && (Date.now() - new Date(a.last_heartbeat).getTime()) <= STALE_MS);
export const shortName = id => String(id || '').replace(/^jarvis-/, '');

async function getJson(path) {
  const r = await fetch(path, { credentials: 'same-origin' });
  if (!r.ok) throw new Error(path.split('/').pop() + ': HTTP ' + r.status);
  return r.json();
}

function diff(old, cur) {
  const ev = [];
  const push = (type, agent, text, sev) => ev.push({ t: Date.now(), type, agent: agent || null, text, sev: sev || 'info' });
  if (!old) return ev;
  const ot = Object.fromEntries(old.tasks.map(t => [t.task_id, t]));
  for (const t of cur.tasks) {
    const o = ot[t.task_id], who = shortName(t.assigned_to);
    if (!o) { push('task_new', t.assigned_to, 'Neuer Auftrag ' + t.task_id + (who ? ' → ' + who : '') + ': ' + t.title, 'info'); continue; }
    if (o.status !== t.status) push('task_status', t.assigned_to, t.task_id + ': ' + o.status + ' → ' + t.status + (who ? ' (' + who + ')' : ''), /DONE/i.test(t.status) ? 'ok' : 'info');
    else if (o.assigned_to !== t.assigned_to) push('task_assign', t.assigned_to, t.task_id + ' neu zugewiesen: ' + shortName(o.assigned_to) + ' → ' + (who || '—'), 'info');
  }
  const oi = new Set(old.incidents.map(i => i.incident_id)), ci = new Set(cur.incidents.map(i => i.incident_id));
  const tmap = Object.fromEntries(cur.tasks.map(t => [t.task_id, t]));
  for (const i of cur.incidents) if (!oi.has(i.incident_id)) push('incident_open', (tmap[i.subject] || {}).assigned_to || (/^jarvis-/.test(i.subject) ? i.subject : null), 'Incident ' + i.classification + ': ' + i.subject, 'warn');
  for (const i of old.incidents) if (!ci.has(i.incident_id)) push('incident_closed', null, 'Incident behoben: ' + i.classification + ' ' + i.subject, 'ok');
  const oa = Object.fromEntries(old.agents.map(a => [a.agent, a]));
  for (const a of cur.agents) {
    const o = oa[a.agent];
    if (o && isFresh(o) && !isFresh(a)) push('agent_stale', a.agent, 'Heartbeat veraltet: ' + a.agent, 'warn');
    if (o && !isFresh(o) && isFresh(a)) push('agent_back', a.agent, 'Heartbeat wieder aktuell: ' + a.agent, 'ok');
  }
  const oj = new Set((old.engine.recent || []).map(j => j.id)), oact = new Set((old.engine.active || []).map(j => j.id || JSON.stringify(j)));
  for (const j of cur.engine.recent || []) if (!oj.has(j.id)) push('job_done', 'jarvis-core', 'Engine-Job ' + j.id + ' ' + j.state + ' (' + (j.tokens_new || 0) + ' Token)', 'ok');
  for (const j of cur.engine.active || []) if (!oact.has(j.id || JSON.stringify(j))) push('job_start', 'jarvis-core', 'Engine-Job gestartet: ' + (j.id || '?'), 'info');
  return ev;
}

async function poll() {
  if (busy) return;
  busy = true;
  try {
    const [ag, tk] = await Promise.all([getJson('/api/jarvis/agents'), getJson('/api/jarvis/tasks')]);
    const cur = {
      agents: Array.isArray(ag.agents) ? ag.agents : [],
      tasks: Array.isArray(tk) ? tk : [],
      incidents: Array.isArray(ag.incidents) ? ag.incidents : [],
      engine: { active: (ag.engine && ag.engine.active) || [], recent: (ag.engine && ag.engine.recent) || [] }
    };
    const fresh = diff(prev, cur);
    prev = cur;
    Object.assign(S, cur, { ts: Date.now(), error: null, loaded: true, polls: S.polls + 1 });
    if (fresh.length) {
      S.events = fresh.reverse().concat(S.events).slice(0, 80);
      try { sessionStorage.setItem('hq-events', JSON.stringify(S.events)); } catch (e) { /* */ }
    }
    emit(fresh);
  } catch (e) {
    S.error = e.message; S.ts = Date.now();
    emit([]);
  }
  busy = false;
}

function emit(fresh) { subs.forEach(fn => { try { fn(S, fresh); } catch (e) { console.error(e); } }); }
function loop() { if (!document.hidden) poll(); }
document.addEventListener('visibilitychange', () => { if (!document.hidden && subs.size) poll(); });

export function subscribe(fn) {
  subs.add(fn);
  if (!timer) { timer = setInterval(loop, POLL_MS); poll(); } else if (S.loaded) fn(S, []);
  return () => { subs.delete(fn); if (!subs.size && timer) { clearInterval(timer); timer = null; prev = null; } };
}

/* Gemeinsame Zustandsableitung je Agent (Voice nutzt sie; HQ/CC haben identische Regeln) */
const RE_WORK = /ACTIVE|RUNNING|IN_?PROGRESS|WORKING/i, RE_PLAN = /PLANNING|INBOX|PENDING|QUEUED|READY/i, RE_DONE = /DONE|COMPLETE|CLOSED/i;
export function agentState(id) {
  const tasks = S.tasks.filter(t => t.assigned_to === id), open = tasks.filter(t => !RE_DONE.test(t.status));
  const tmap = Object.fromEntries(S.tasks.map(t => [t.task_id, t]));
  const incidents = S.incidents.filter(i => (tmap[i.subject] || {}).assigned_to === id || i.subject === id);
  const hb = S.agents.find(a => a.agent === id) || null;
  const status = open.some(t => RE_WORK.test(t.status)) ? 'working' : open.some(t => RE_PLAN.test(t.status)) ? 'planning' : 'idle';
  return { id, status, tasks, open, incidents, hb, alert: incidents.length > 0 || !!(hb && !isFresh(hb)) };
}

/* Einmalig frische Daten holen (fuer Sprachantworten ausserhalb von HQ/CC): wartet auf den ersten Emit, max. 6 s */
export function refresh() {
  return new Promise(res => {
    let un = null, done = false;
    const fin = () => { if (done) return; done = true; res(); queueMicrotask(() => { if (un) un(); }); };
    un = subscribe(() => fin());
    if (done && un) un();
    setTimeout(fin, 6000);
  });
}
