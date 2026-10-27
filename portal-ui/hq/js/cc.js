/* MA-HOME HQ — Command Center (M4, SPEC §13): dieselben echten Daten wie Living HQ (gemeinsamer Store),
   plus Server-/Token-/Job-/Automations-Quellen. Keine parallelen Statussysteme, keine simulierten Werte.
   Felder ohne Datenquelle werden ausdruecklich als "nicht angebunden" gezeigt. */
import { esc, api, cop, fmtBytes, fmtUp, fmtTok } from './api.js';
import { subscribe, S, isFresh, shortName } from './store.js';
import { ROSTER, SYSTEM, ROOMS } from './roster.js';
import { SLASH_CMDS, SLASH_SKILLS } from './chat.js';
import { renderLedger } from './ledger-view.js';

let stopFn = null;
export function leaveCC() { if (stopFn) { stopFn(); stopFn = null; } }

const RE_WORK = /ACTIVE|RUNNING|IN_?PROGRESS|WORKING/i, RE_PLAN = /PLANNING|INBOX|PENDING|QUEUED|READY/i, RE_DONE = /^(?:DONE|COMPLETE|COMPLETED|CLOSED|CANCELLED|CANCELED|ARCHIVED|FAILED)$/i;
const pct = (a, b) => b ? Math.max(0, Math.min(100, Math.round(a / b * 100))) : 0;
const bar = (p, hot) => '<div class="ccbar' + (hot || p >= 85 ? ' hot' : '') + '"><i style="width:' + p + '%"></i></div>';
const ago = iso => { const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000); return s < 90 ? Math.round(s) + ' s' : s < 5400 ? Math.round(s / 60) + ' min' : s < 172800 ? Math.round(s / 3600) + ' Std' : Math.round(s / 86400) + ' Tg'; };
const hhmm = t => new Date(t).toLocaleTimeString('de-DE');
const trunc = (s, n) => { s = String(s ?? ''); return s.length > n ? s.slice(0, n - 1) + '…' : s; };
const NA = (what, why) => '<div class="ccna"><b>' + esc(what) + '</b> – nicht angebunden<div class="faint">' + esc(why) + '</div></div>';

export function renderCC(root, ctx) {
  leaveCC();
  root.innerHTML =
    '<div class="top"><div><h1>Command Center</h1><div class="sub">Dieselben echten Daten wie das Living HQ – ohne parallele Statussysteme</div></div><div id="ccstamp" class="chip"></div></div>' +
    '<div class="grid cols4 section" id="cckpi"></div>' +
    '<div class="grid cols2 section"><div class="holo" id="ccagents"></div><div class="holo" id="cctasks"></div></div>' +
    '<div class="grid cols2 section"><div class="holo" id="ccinc"></div><div class="holo" id="ccjobs"></div></div>' +
    '<div class="grid cols3 section"><div class="holo" id="cctok"></div><div class="holo" id="ccsrv"></div><div class="holo" id="ccconn"></div></div>' +
    '<div class="grid cols3 section"><div class="holo" id="ccauto"></div><div class="holo" id="ccskills"></div><div class="holo" id="cchist"></div></div>' +
    '<div class="holo section" id="ccna"></div>';
  const $id = id => root.querySelector('#' + id);
  const X = { tele: null, status: null, usage: null, plan: null, jobs: [], conn: null, sched: null, sess: null, errs: {} };

  /* ---- Renderer ---- */
  function kpis() {
    const open = S.tasks.filter(t => !RE_DONE.test(t.status)).length;
    const fresh = S.agents.filter(isFresh).length;
    const jobsToday = X.usage && X.usage.today ? Object.values(X.usage.today).reduce((a, k) => a + (k.jobs || 0), 0) : null;
    const box = (l, v, d, cls) => '<div class="holo kpi ' + (cls || '') + '"><span class="label">' + l + '</span><span class="value">' + v + '</span><span class="delta' + (cls ? ' neg' : '') + '">' + d + '</span></div>';
    $id('cckpi').innerHTML =
      box('Agenten', ROSTER.length + SYSTEM.length, fresh + ' von ' + S.agents.length + ' Heartbeats aktuell') +
      box('Aufträge offen', open, S.tasks.length + ' gesamt') +
      box('Incidents offen', S.incidents.length, S.incidents.length ? 'Handlungsbedarf' : 'keine', S.incidents.length ? 'danger' : '') +
      box('Chat-Aufträge heute', jobsToday == null ? '…' : jobsToday, X.usage ? 'Limit Chat ' + ((X.usage.limits || {}).chat || '?') + '/Tag' : '');
    $id('ccstamp').innerHTML = S.error ? '<span class="dot err"></span> Datenfehler: ' + esc(S.error) : '<span class="dot live"></span> Stand ' + (S.ts ? hhmm(S.ts) : '…');
  }

  function agents() {
    const rows = ROSTER.concat(SYSTEM).map(([id, role, room]) => {
      const tasks = S.tasks.filter(t => t.assigned_to === id), open = tasks.filter(t => !RE_DONE.test(t.status));
      const st = open.some(t => RE_WORK.test(t.status)) ? 'arbeitet' : open.some(t => RE_PLAN.test(t.status)) ? 'Planung' : 'ohne Auftrag';
      const hb = S.agents.find(a => a.agent === id);
      const inc = S.incidents.filter(i => (S.tasks.find(t => t.task_id === i.subject) || {}).assigned_to === id || i.subject === id).length;
      return '<tr><td><b>' + esc(shortName(id)) + '</b><div class="faint">' + esc(role) + '</div></td><td>' + esc(ROOMS[room].name) + '</td><td>' +
        '<span class="chip ' + (st === 'arbeitet' ? 'cyan' : '') + '">' + st + '</span></td><td class="mono">' + open.length + '/' + tasks.length + '</td><td class="mono">' +
        (hb ? (isFresh(hb) ? '<span class="dot ok"></span> ' : '<span class="dot warn"></span> ') + ago(hb.last_heartbeat) : '<span class="faint">–</span>') + '</td><td>' + (inc ? '<span class="chip crimson">' + inc + '</span>' : '') + '</td></tr>';
    }).join('');
    $id('ccagents').innerHTML = '<h2 class="holo-title">Agenten &amp; Council<span class="sub">Raum = Schreibtisch-Zuordnung · Status aus Tasks · Heartbeat nur wo vorhanden</span></h2>' +
      '<div class="ccscroll" tabindex="0" role="region" aria-label="Tabelle, mit Pfeiltasten scrollbar"><table class="table"><thead><tr><th>Agent</th><th>Raum</th><th>Status</th><th>Offen/Ges.</th><th>Heartbeat</th><th>⚠</th></tr></thead><tbody>' + rows + '</tbody></table></div>';
  }

  function tasks() {
    const order = t => RE_WORK.test(t.status) ? 0 : RE_PLAN.test(t.status) ? 1 : RE_DONE.test(t.status) ? 3 : 2;
    const list = S.tasks.slice().sort((a, b) => order(a) - order(b) || String(b.updated).localeCompare(String(a.updated)));
    $id('cctasks').innerHTML = '<h2 class="holo-title">Aufgaben &amp; Delegationen<span class="sub">/api/jarvis/tasks</span></h2>' +
      '<div class="ccscroll" tabindex="0" role="region" aria-label="Tabelle, mit Pfeiltasten scrollbar"><table class="table"><thead><tr><th>Task</th><th>Zugewiesen</th><th>Status</th><th>Aktualisiert</th></tr></thead><tbody>' +
      (list.map(t => '<tr><td><span class="mono">' + esc(t.task_id) + '</span><div class="faint">' + esc(trunc(t.title, 46)) + '</div></td><td>' + esc(shortName(t.assigned_to) || '–') + '</td><td><span class="chip ' + (RE_WORK.test(t.status) ? 'cyan' : '') + '">' + esc(t.status) + '</span></td><td class="mono">vor ' + ago(t.updated) + '</td></tr>').join('') || '<tr><td colspan="4" class="faint">Keine Tasks.</td></tr>') + '</tbody></table></div>';
  }

  function incidents() {
    $id('ccinc').innerHTML = '<h2 class="holo-title">Incidents &amp; Fehler<span class="sub">Watchdog-Befunde, offen</span></h2>' +
      (S.incidents.length ? '<ul class="hql">' + S.incidents.map(i => '<li><span class="chip crimson">' + esc(i.classification) + '</span> <b class="mono">' + esc(i.subject) + '</b><div class="faint">' + esc(i.adapter) + ' · seit ' + Math.round(i.age_min / 60) + ' Std · ' + esc(i.incident_id) + '</div></li>').join('') + '</ul>' : '<div class="faint">Keine offenen Incidents.</div>');
  }

  function jobs() {
    const sum = X.jobs.reduce((a, j) => a + (j.tokens_new || 0), 0), calls = X.jobs.reduce((a, j) => a + (j.claude_calls || 0), 0);
    $id('ccjobs').innerHTML = '<h2 class="holo-title">Engine-Jobs<span class="sub">/api/jarvis/jobs · ' + X.jobs.length + ' letzte · ' + fmtTok(sum) + ' neue Token · ' + calls + ' Claude-Aufrufe</span></h2>' +
      (S.engine.active.length ? '<p><span class="chip cyan"><span class="dot live"></span> ' + S.engine.active.length + ' aktiv</span></p>' : '') +
      '<div class="ccscroll" tabindex="0" role="region" aria-label="Tabelle, mit Pfeiltasten scrollbar"><table class="table"><thead><tr><th>Job</th><th>Anfrage</th><th>Calls</th><th>Token</th><th>Ergebnis</th></tr></thead><tbody>' +
      (X.jobs.slice(0, 12).map(j => '<tr><td class="mono">' + esc(j.id.slice(-6)) + '<div class="faint">' + (j.finished ? hhmm(j.finished * 1000) : '') + '</div></td><td>' + esc(trunc(j.request, 40)) + '</td><td class="mono">' + (j.claude_calls ?? '–') + '</td><td class="mono">' + fmtTok(j.tokens_new || 0) + '</td><td><span class="chip ' + (j.verdict === 'done' ? 'cyan' : 'crimson') + '">' + esc(j.verdict || j.state) + '</span></td></tr>').join('') || '<tr><td colspan="5" class="faint">Keine Jobs.</td></tr>') + '</tbody></table></div>';
  }

  function tokens() {
    const u = X.usage, p = X.plan, T = (u && u.today) || {}, L = (u && u.limits) || {};
    const names = { chat: 'Chat', council: 'Council', geplant: 'Geplant' };
    const days = u && u.days ? Object.keys(u.days).sort().slice(-5).reverse() : [];
    $id('cctok').innerHTML = '<h2 class="holo-title">Token &amp; Kosten<span class="sub">Claude-Brücke · usage-Op</span></h2>' +
      (u ? Object.keys(names).map(k => { const j = (T[k] || {}).jobs || 0; return '<div class="ccrow"><span>' + names[k] + '</span><span class="mono">' + j + ' / ' + (L[k] ?? '?') + ' Aufträge</span></div>' + bar(pct(j, L[k])); }).join('') +
        '<div class="faint" style="margin-top:6px">Heute: ' + fmtTok(Object.values(T).reduce((a, k) => a + (k.in || 0), 0)) + ' rein / ' + fmtTok(Object.values(T).reduce((a, k) => a + (k.out || 0), 0)) + ' raus</div>' : '<div class="faint">' + esc(X.errs.usage || 'lädt …') + '</div>') +
      (p && p.ok ? [['five', 'Sitzung 5 h'], ['week', 'Woche']].filter(x => p[x[0]]).map(x => '<div class="ccrow" style="margin-top:10px"><span>' + x[1] + ' (Plan)</span><span class="mono">' + Math.round(p[x[0]].p) + ' %</span></div>' + bar(Math.min(100, Math.round(p[x[0]].p)))).join('') : '') +
      (days.length ? '<div class="hqk">Letzte Tage (Aufträge · Token rein/raus)</div>' + days.map(d => { const D = u.days[d], j = Object.values(D).reduce((a, k) => a + (k.jobs || 0), 0), i = Object.values(D).reduce((a, k) => a + (k.in || 0), 0), o = Object.values(D).reduce((a, k) => a + (k.out || 0), 0); return '<div class="ccrow"><span class="mono">' + d.slice(5) + '</span><span class="mono">' + j + ' · ' + fmtTok(i) + '/' + fmtTok(o) + '</span></div>'; }).join('') : '');
  }

  function server() {
    const s = X.status;
    $id('ccsrv').innerHTML = '<h2 class="holo-title">Server<span class="sub">ma-server · /api/status</span></h2>' + (s ?
      '<div class="ccrow"><span>CPU</span><span class="mono">' + Math.round(s.cpu) + ' %</span></div>' + bar(Math.round(s.cpu)) +
      '<div class="ccrow"><span>RAM</span><span class="mono">' + fmtBytes(s.ram_used) + ' / ' + fmtBytes(s.ram_total) + '</span></div>' + bar(pct(s.ram_used, s.ram_total)) +
      '<div class="ccrow"><span>Disk</span><span class="mono">' + fmtBytes(s.disk_used) + ' / ' + fmtBytes(s.disk_total) + '</span></div>' + bar(pct(s.disk_used, s.disk_total)) +
      '<div class="ccrow"><span>Laufzeit</span><span class="mono">' + fmtUp(s.uptime) + '</span></div>' +
      '<div class="ccrow"><span>Backup</span><span class="mono">' + esc((s.backup_status || {}).state || '–') + '</span></div>' +
      '<div class="hqk">Container (' + (s.containers || []).length + ')</div>' + (s.containers || []).map(c => '<div class="ccrow"><span><span class="dot ' + (c.state === 'running' ? 'ok' : 'err') + '"></span> ' + esc(c.name) + (c.oom ? ' ⚠OOM' : '') + '</span><span class="mono">' + fmtBytes(c.memory || 0) + '</span></div>').join('')
      : '<div class="faint">' + esc(X.errs.status || 'lädt …') + '</div>');
  }

  function conn() {
    const c = X.conn;
    const by = c && c.ok ? c.items.reduce((m, i) => (m[i.state] = (m[i.state] || 0) + 1, m), {}) : null;
    $id('ccconn').innerHTML = '<h2 class="holo-title">Verbindungen &amp; Provider<span class="sub">Claude-Konnektoren</span></h2>' + (by ?
      '<div class="ccrow"><span><span class="dot ok"></span> verbunden</span><span class="mono">' + (by.ok || 0) + '</span></div>' +
      '<div class="ccrow"><span><span class="dot warn"></span> Anmeldung nötig</span><span class="mono">' + (by.login || 0) + '</span></div>' +
      '<div class="ccrow"><span><span class="dot err"></span> Fehler</span><span class="mono">' + (by.fehler || 0) + '</span></div>' +
      '<div class="hqk">Auffällig</div><ul class="hql">' + c.items.filter(i => i.state !== 'ok').slice(0, 6).map(i => '<li>' + esc(i.name) + ' <span class="faint">' + esc(i.state) + '</span></li>').join('') + '</ul>' : '<div class="faint">' + esc(X.errs.conn || 'lädt …') + '</div>');
  }

  function auto() {
    const t = X.sched && X.sched.tasks;
    $id('ccauto').innerHTML = '<h2 class="holo-title">Automatisierungen<span class="sub">geplante JARVIS-Aufgaben</span></h2>' + (t ? (t.length ? '<ul class="hql">' + t.map(x => '<li>' + (x.enabled ? '' : '⏸ ') + '<b>' + esc(x.title) + '</b><div class="faint">' + (x.trigger === 'inbox' ? 'bei neuer Datei' : esc(x.time)) + ' · ' + esc(x.mode) + ' · ' + esc(x.model) + (x.last ? ' · zuletzt ' + esc(x.last) : '') + '</div></li>').join('') + '</ul>' : '<div class="faint">Keine geplanten Aufgaben angelegt.</div>') : '<div class="faint">' + esc(X.errs.sched || 'lädt …') + '</div>');
  }

  function skills() {
    $id('ccskills').innerHTML = '<h2 class="holo-title">Skills &amp; Werkzeuge<span class="sub">Katalog des Portal-Chats (Slash-Menü)</span></h2>' +
      '<div class="hqk">Skills (' + SLASH_SKILLS.length + ')</div><div class="ccchips">' + SLASH_SKILLS.map(s => '<span class="chip" title="' + esc(s[1]) + '">/' + esc(s[0]) + '</span>').join('') + '</div>' +
      '<div class="hqk">Befehle (' + SLASH_CMDS.length + ')</div><div class="ccchips">' + SLASH_CMDS.map(s => '<span class="chip" title="' + esc(s[1]) + '">/' + esc(s[0]) + '</span>').join('') + '</div>';
  }

  function history() {
    const ev = S.events.slice(0, 6), se = X.sess && X.sess.sessions ? X.sess.sessions.slice(0, 5) : [];
    $id('cchist').innerHTML = '<h2 class="holo-title">Historie<span class="sub">Ereignisse seit Aufruf · letzte Chat-Verläufe</span></h2>' +
      (ev.length ? '<ul class="hql">' + ev.map(e => '<li><span class="mono faint">' + hhmm(e.t) + '</span> ' + esc(trunc(e.text, 70)) + '</li>').join('') + '</ul>' : '<div class="faint">Seit dem Öffnen keine Änderungen.</div>') +
      (se.length ? '<div class="hqk">Chat-Verläufe</div><ul class="hql">' + se.map(s => '<li>' + esc(trunc(s.title, 56)) + '<div class="faint">' + esc(s.where) + ' · vor ' + ago(s.time * 1000) + '</div></li>').join('') + '</ul>' : '');
  }

  function pcPanel() {
    const t = X.tele && X.tele.pc;
    if (!t) return NA('PC- & GPU-Telemetrie', X.errs.tele || 'lädt …');
    if (t.state !== 'fresh') return NA('PC- & GPU-Telemetrie', t.state === 'stale' ? 'Letzter Messwert vor ' + t.age_s + ' s – PC-Reporter meldet nicht mehr (PC aus oder Reporter gestoppt).' : 'Kein gültiger Messwert vorhanden (' + t.state + ').');
    const g = t.gpu;
    return '<div class="ccna ok"><b>PC &amp; GPU</b> – Messwert vor ' + t.age_s + ' s<div class="ccrow"><span>CPU</span><span class="mono">' + Math.round(t.cpu_pct) + ' %</span></div>' + bar(Math.round(t.cpu_pct)) +
      '<div class="ccrow"><span>RAM</span><span class="mono">' + Math.round(t.ram_pct) + ' %</span></div>' + bar(Math.round(t.ram_pct)) +
      (g ? '<div class="ccrow"><span>GPU</span><span class="mono">' + Math.round(g.util_pct) + ' % · ' + Math.round(g.temp_c) + ' °C</span></div>' + bar(Math.round(g.util_pct)) +
        '<div class="ccrow"><span>VRAM</span><span class="mono">' + Math.round(g.vram_used_mb) + ' / ' + Math.round(g.vram_total_mb) + ' MB</span></div>' + bar(pct(g.vram_used_mb, g.vram_total_mb)) : '<div class="faint">Keine GPU-Werte (nvidia-smi nicht verfügbar).</div>') +
      '<div class="faint">Nur Messwerte; keine Prozessnamen. Zeigt Auslastung, nicht ob ein Worker arbeitet.</div></div>';
  }

  function logPanel() {
    const L = X.tele && X.tele.logs;
    if (!L) return NA('Logs', X.errs.tele || 'lädt …');
    const rows = Object.keys(L.units).map(u => { const v = L.units[u]; return v.error ? '<li><span class="dot warn"></span> <b class="mono">' + esc(u) + '</b> <span class="faint">' + esc(v.error) + '</span></li>' :
      '<li><span class="dot ' + (v.errors ? 'err' : 'ok') + '"></span> <b class="mono">' + esc(u) + '</b> ' + v.errors + ' Fehler' + v.last.map(m => '<div class="faint mono">' + hhmm(m.t * 1000) + ' ' + esc(m.msg) + '</div>').join('') + '</li>'; }).join('');
    return '<div class="ccna ok"><b>Logs</b> – ' + esc(L.window) + '<ul class="hql">' + rows + '</ul><div class="faint">Zugangsdaten werden maskiert; höchstens 3 gekürzte Zeilen je Dienst.</div></div>';
  }

  function na() {
    $id('ccna').innerHTML = renderLedger(X.ledger) + '<h2 class="holo-title">Weitere Quellen<span class="sub">Angebunden nur, wo eine echte Datenquelle existiert – nichts wird simuliert</span></h2><div class="grid cols3">' +
      NA('Modelle & Router-Quoten', 'Evidence-Router-Ledger liegt auf dem Server (router/), hat aber keinen Portal-Endpunkt.') + pcPanel() + logPanel() + '</div>';
  }

  let active = true;
  const paint = () => { if (!active || !root.querySelector('#cckpi')) return; kpis(); agents(); tasks(); incidents(); jobs(); tokens(); server(); conn(); auto(); skills(); history(); na(); };

  /* ---- Zusatzquellen (30 s) ---- */
  async function slow() {
    const get = async (k, fn) => { try { X[k] = await fn(); delete X.errs[k]; } catch (e) { X.errs[k] = e.message; } };
    await Promise.all([
      get('status', () => api('/api/status')),
      get('tele', () => api('/api/jarvis/telemetry')),
      get('ledger', async () => { const r = await api('/api/jarvis', { body: { cmd: 'usage' } }); if (!r.ok) throw new Error('Ledger nicht verfügbar'); return r.data; }),
      get('usage', () => cop('usage', {})),
      get('conn', () => cop('connectors', {})),
      get('sched', () => cop('sched_list', {})),
      get('sess', () => cop('sessions', {})),
      get('jobs', async () => { const d = await api('/api/jarvis/jobs'); return d.jobs || []; }),
      get('plan', async () => (await cop('jobs', {})).plan)
    ]);
    paint();
  }

  const unsub = subscribe(() => paint());
  paint(); slow();
  const t30 = setInterval(() => { if (!document.hidden) slow(); }, 30000);
  stopFn = () => { active = false; clearInterval(t30); unsub(); };
}
