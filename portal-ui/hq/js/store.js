/* MA-HOME HQ — gemeinsamer Daten-Store (M3 Living HQ; M4 Command Center nutzt denselben Store).
   Quelle ausschliesslich echte API-Daten. Events entstehen NUR aus Zustandsaenderungen zwischen zwei Polls
   (keine erfundene Aktivitaet). Polling nur, solange mindestens ein Abonnent aktiv ist und der Tab sichtbar ist. */

export const STALE_MS = 10 * 60000;          // wie im Bestand: Heartbeat aelter als 10 Min = veraltet
const POLL_MS = 5000, POLL_BUSY_MS = 2000;   // CORE-003: schneller nachsehen, solange etwas läuft (Statuswechsel < 3 s sichtbar)
export const pollDelay = st => ((st.engine.active || []).length || st.tasks.some(t => /ACTIVE|RUNNING|IN_?PROGRESS|WORKING/i.test(t.status)) ? POLL_BUSY_MS : POLL_MS);

/* Einheitlicher Ereignis-/Zustandsvertrag (Vollpaket 0.4) – NUR aus Engine-/Task-Status abgeleitet, nie aus Modelltext. */
export function unifiedState(status) {
  const s = String(status || '').toUpperCase();
  if (/^(?:DONE|COMPLETE|COMPLETED)$/.test(s)) return 'DONE_VERIFIED';   // V16 'done' = unabhängige Abnahme bestanden
  if (/^(?:FAILED|ERROR)$/.test(s)) return 'FAILED';
  if (/^(?:PARTIAL)$/.test(s)) return 'PARTIAL';
  if (/^(?:CANCELLED|CANCELED)$/.test(s)) return 'CANCELLED';
  if (/WAITING_APPROVAL|NEEDS_APPROVAL/.test(s)) return 'WAITING_APPROVAL';
  if (/BLOCKED|WAITING_PC|WAITING/.test(s)) return 'BLOCKED';
  if (/RECOVER|RETRY/.test(s)) return 'RECOVERING';
  if (/ACTIVE|RUNNING|IN_?PROGRESS|WORKING|PLANNING/.test(s)) return 'RUNNING';
  return 'IDLE';
}

export const S = {
  agents: [],            // [{agent,last_heartbeat,status}]
  tasks: [],             // [{task_id,title,status,assigned_to,created,updated,priority}]
  incidents: [],         // [{incident_id,classification,subject,state,age_min,...}]
  engine: { active: [], recent: [] },
  activity: { agents: {}, last: 0 },   // V16-AgentEvents (normalisiert serverseitig, nur echte Ereignisse)
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

// Completion is not success: preserve the original state, classify exactly.
const eventSeverity = status => /^(?:DONE|COMPLETE|COMPLETED)$/i.test(String(status || '')) ? 'ok' : /^(?:FAILED|ERROR)$/i.test(String(status || '')) ? 'warn' : 'info';

function diff(old, cur) {
  const ev = [];
  const push = (type, agent, text, sev) => ev.push({ t: Date.now(), type, agent: agent || null, text, sev: sev || 'info' });
  if (!old) return ev;
  const ot = Object.fromEntries(old.tasks.map(t => [t.task_id, t]));
  for (const t of cur.tasks) {
    const o = ot[t.task_id], who = shortName(t.assigned_to);
    if (!o) { push('task_new', t.assigned_to, 'Neuer Auftrag ' + t.task_id + (who ? ' → ' + who : '') + ': ' + t.title, 'info'); continue; }
    if (o.status !== t.status) push('task_status', t.assigned_to, t.task_id + ': ' + o.status + ' → ' + t.status + (who ? ' (' + who + ')' : ''), eventSeverity(t.status));
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
  for (const j of cur.engine.recent || []) if (!oj.has(j.id)) push('job_done', 'jarvis-core', 'Engine-Job ' + j.id + ' ' + j.state + ' (' + (j.tokens_new || 0) + ' Token)', eventSeverity(j.state));
  for (const j of cur.engine.active || []) if (!oact.has(j.id || JSON.stringify(j))) push('job_start', 'jarvis-core', 'Engine-Job gestartet: ' + (j.id || '?'), 'info');
  return ev;
}

/* Living HQ: /api/jarvis cmd activity (lesend, Allowlist). Fehler hier blockieren das HQ nicht (dann ohne Engine-Figuren). */
async function getActivity(since) {
  try {
    const r = await fetch('/api/jarvis', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-MA-Request': '1' },
      body: JSON.stringify({ cmd: 'activity', since: since || 0 }) });
    if (!r.ok) return null;
    const j = await r.json();
    return j && j.ok !== false ? (j.data || j) : null;
  } catch (e) { return null; }
}

let inflight = null, actP = null, actRes = null;
function poll() {
  if (inflight) return inflight;
  inflight = doPoll().finally(() => { inflight = null; });
  return inflight;
}
async function doPoll() {
  busy = true;
  try {
    if (!actP) actP = getActivity(S.activity.last).then(r => { actRes = r; }).finally(() => { actP = null; });   // entkoppelt: bremst den Poll nicht
    const [ag, tk] = await Promise.all([getJson('/api/jarvis/agents'), getJson('/api/jarvis/tasks')]);
    const ac = actRes; actRes = null;
    const cur = {
      agents: Array.isArray(ag.agents) ? ag.agents : [],
      tasks: Array.isArray(tk) ? tk : [],
      incidents: Array.isArray(ag.incidents) ? ag.incidents : [],
      engine: { active: (ag.engine && ag.engine.active) || [], recent: (ag.engine && ag.engine.recent) || [] }
    };
    const fresh = diff(prev, cur);
    if (ac) {
      for (const e of ac.events || []) if (S.activity.last) fresh.push({ t: e.ts * 1000, type: 'agent_' + e.activity, agent: e.agent, text: e.job + ' · ' + e.text, sev: e.sev, job: e.job });
      S.activity = { agents: ac.agents || {}, last: ac.last_id || S.activity.last };
    }
    prev = cur;
    Object.assign(S, cur, { ts: Date.now(), error: null, loaded: true, polls: S.polls + 1 });
    if (fresh.length) {
      S.events = fresh.reverse().concat(S.events).slice(0, 80);
      try { sessionStorage.setItem('hq-events', JSON.stringify(S.events)); } catch (e) { /* */ }
    }
    emit(fresh);
    busy = false;
    return true;
  } catch (e) {
    S.error = e.message; S.ts = Date.now();
    emit([]);
    busy = false;
    return false;
  }
}

function emit(fresh) { subs.forEach(fn => { try { fn(S, fresh); } catch (e) { console.error(e); } }); }
function loop() {
  timer = setTimeout(async () => { if (!document.hidden) await poll(); if (timer) loop(); }, S.loaded ? pollDelay(S) : POLL_MS);
}
document.addEventListener('visibilitychange', () => { if (!document.hidden && subs.size) poll(); });

export function subscribe(fn) {
  subs.add(fn);
  if (!timer) { timer = true; poll(); loop(); } else if (S.loaded) fn(S, []);
  return () => { subs.delete(fn); if (!subs.size && timer) { clearTimeout(timer); timer = null; prev = null; } };
}

/* Gemeinsame Zustandsableitung je Agent (Voice nutzt sie; HQ/CC haben identische Regeln) */
const RE_WORK = /ACTIVE|RUNNING|IN_?PROGRESS|WORKING/i, RE_PLAN = /PLANNING|INBOX|PENDING|QUEUED|READY/i, RE_DONE = /^(?:DONE|COMPLETE|COMPLETED|CLOSED|CANCELLED|CANCELED|ARCHIVED|FAILED)$/i;
export function agentState(id) {
  const tasks = S.tasks.filter(t => t.assigned_to === id), open = tasks.filter(t => !RE_DONE.test(t.status));
  const tmap = Object.fromEntries(S.tasks.map(t => [t.task_id, t]));
  const incidents = S.incidents.filter(i => (tmap[i.subject] || {}).assigned_to === id || i.subject === id);
  const hb = S.agents.find(a => a.agent === id) || null;
  const status = open.some(t => RE_WORK.test(t.status)) ? 'working' : open.some(t => RE_PLAN.test(t.status)) ? 'planning' : 'idle';
  return { id, status, tasks, open, incidents, hb, alert: incidents.length > 0 || !!(hb && !isFresh(hb)) };
}

/* Einmalig FRISCHE Daten holen (Sprachantworten ausserhalb von HQ/CC): erzwingt einen Poll (gleichzeitige Aufrufe teilen ihn),
   liefert true nur bei erfolgreichem Abruf, false bei Fehler oder Timeout (max. 6 s) – nie stillschweigend veraltete Daten als frisch. */
export async function refresh() {
  const un = subscribe(() => {});
  let timer = null;
  try {
    return await Promise.race([poll(), new Promise(res => { timer = setTimeout(() => res(false), 6000); })]);
  } finally { clearTimeout(timer); un(); }
}
