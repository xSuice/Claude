/* MA-HOME HQ — Views: Dashboard, Items, Dateien, System, Terminal, Verbindungen
   (Ports aus Bestands-app.js, API-Vertraege unveraendert) */
import { $, esc, api, cop, toast, items, fmtBytes, fmtUp, fmtDate, fmtTok, today, lvl } from './api.js';
import { openViewer } from './viewer.js';

const H = (title, sub, extra = '') => '<div class="top"><div><h1>' + esc(title) + '</h1><div class="sub">' + (sub || '') + '</div></div>' + extra + '</div>';

/* ---------- Dashboard (Lage) ---------- */
export async function renderDashboard(root, ctx) {
  root.innerHTML = H('Kommandozentrale', 'Lage auf einen Blick') +
    '<div class="grid cols4 section" id="dkpi"><div class="holo kpi"><span class="label">Server</span><span class="value">…</span></div>' +
    '<div class="holo kpi"><span class="label">Meine Aufgaben offen</span><span class="value">…</span></div>' +
    '<div class="holo kpi"><span class="label">Agenten mit Heartbeat</span><span class="value">…</span></div>' +
    '<div class="holo kpi danger"><span class="label">Watchdog</span><span class="value">…</span></div></div>' +
    '<div id="dbrief"></div>';
  const set = (i, html) => { const el = root.querySelectorAll('#dkpi .value')[i]; if (el) el.innerHTML = html; };
  try {
    const st = await api('/api/status');
    set(0, esc(fmtUp(st.uptime || 0)));
    const bk = st.backup_status;
    if (bk) set(0, esc(fmtUp(st.uptime || 0)) + '<div class="delta' + (/^OK/.test(bk.state) ? '' : ' neg') + '">Backup: ' + esc(bk.state) + '</div>');
  } catch (e) { set(0, '<span class="dot warn"></span>&nbsp;n/a<div class="delta neg" title="' + esc(e.message) + '">Statusdienst nicht erreichbar</div>'); }
  try {
    const t = await items('tasks');
    const open = t.filter(x => !x.done).length;
    set(1, String(open) + '<div class="delta">' + t.length + ' gesamt</div>');
  } catch (e) { set(1, '—'); }
  // Echte Datenform (verifiziert): /api/jarvis/agents = {agents:[{agent,last_heartbeat,status}],tasks,incidents,engine,ts};
  // /api/jarvis/watchdog = [{agent,last_heartbeat,status}]. "Stale" = Heartbeat älter als 10 Min (wie im Bestand).
  const STALE_MS = 10 * 60000;
  const isFresh = a => a && a.last_heartbeat && (Date.now() - new Date(a.last_heartbeat).getTime()) <= STALE_MS;
  try {
    const r = await fetch('/api/jarvis/agents', { credentials: 'same-origin' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();
    const list = Array.isArray(d.agents) ? d.agents : [];
    const fresh = list.filter(isFresh).length;
    const inc = Array.isArray(d.incidents) ? d.incidents.length : 0;
    set(2, String(list.length) + '<div class="delta' + (fresh < list.length ? ' neg' : '') + '">' + fresh + ' aktuell' + (fresh < list.length ? ' · ' + (list.length - fresh) + ' veraltet' : '') + (inc ? ' · ' + inc + ' Incident(s)' : '') + '</div>');
  } catch (e) { set(2, '—<div class="delta neg">' + esc(e.message) + '</div>'); }
  try {
    const r = await fetch('/api/jarvis/watchdog', { credentials: 'same-origin' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();
    const w = (Array.isArray(d) ? d : []).find(x => x && x.agent === 'watchdog');
    const ok = !!(w && String(w.status).toUpperCase() === 'ACTIVE' && isFresh(w));
    set(3, '<span class="dot ' + (ok ? 'live' : w ? 'warn' : 'err') + '"></span>&nbsp;' + (ok ? 'Aktiv' : w ? 'Veraltet' : 'Kein Watchdog') + (w ? '<div class="delta' + (ok ? '' : ' neg') + '">Heartbeat ' + new Date(w.last_heartbeat).toLocaleTimeString('de-DE') + '</div>' : ''));
  } catch (e) { set(3, '<span class="dot warn"></span>&nbsp;—<div class="delta neg">' + esc(e.message) + '</div>'); }
  // Jarvis heute: Morgenbrief + Lern-Impuls aus dem Vault (vom Server per Cron geschrieben)
  try {
    const get = async n => {
      try { const r = await fetch('/api/file?path=' + encodeURIComponent('Bibliothek/vault-notizen/_Claude-Memory/Dienste/' + n), { credentials: 'same-origin' }); return r.ok ? await r.text() : ''; }
      catch (er) { return ''; }
    };
    const [brief, lern] = await Promise.all([get('Morgenbrief.md'), get('Lern-Impuls.md')]);
    const anchor = root.querySelector('#dbrief');
    if (anchor && (brief || lern)) {
      anchor.innerHTML = '<div class="holo"><h2 class="holo-title">JARVIS heute</h2><div id="jbrief"></div><div id="jlern"></div>' +
        '<div class="sub mt"><a href="/api/file?path=' + encodeURIComponent('Bibliothek/fristen.ics') + '">Fristen als Kalenderdatei laden (.ics)</a></div></div>';
      const { mdLite } = await import('./api.js');
      const first = (brief.split(/^(?=## )/m).find(s => s.startsWith('## ')) || brief.slice(0, 1200));
      if (brief) root.querySelector('#jbrief').innerHTML = '<div class="md">' + mdLite(first.slice(0, 1400)) + '</div>';
      if (lern) {
        root.querySelector('#jlern').innerHTML = '<details class="mt"><summary>Lern-Impuls: drei Fragen</summary><div class="md">' + mdLite(lern) + '</div>' +
          '<div class="cacts"><button type="button" data-fb="known">Wusste ich</button><button type="button" data-fb="again">Nochmal</button></div></details>';
        const note = ((lern.match(/\[\[([^\]|]+)\|/) || [])[1] || '') + '.md';
        root.querySelector('#jlern').onclick = async e => {
          const b = e.target.closest('button[data-fb]'); if (!b) return;
          try {
            const r = await cop('lern_feedback', { data: JSON.stringify({ note, result: b.dataset.fb }) });
            toast(r.ok ? (b.dataset.fb === 'again' ? 'Kommt bald wieder dran' : 'Seltener gefragt') : 'Rückmeldung nicht gespeichert', r.ok ? 0 : 1);
          } catch (er) { toast(er.message, 1); }
        };
      }
    }
  } catch (e) { /* Karte optional */ }
  root.querySelector('#dkpi').insertAdjacentHTML('afterend',
    '<p class="row" style="margin:0 0 16px"><button class="btn primary" data-go="chat">JARVIS fragen</button>' +
    '<button class="btn" data-go="tasks">Aufgaben ansehen</button><button class="btn" data-go="files">Dateien öffnen</button></p>');
  root.querySelectorAll('[data-go]').forEach(b => b.onclick = () => ctx.go(b.dataset.go));
}

/* ---------- Aufgaben ---------- */
export function renderTasks(root, ctx) {
  const render = async () => {
    const list = (await items('tasks')).sort((a, b) => (a.done - b.done) || ((a.due || '9') < (b.due || '9') ? -1 : 1));
    $('#list', root).innerHTML = list.length ? list.map(t => '<div class="row ' + (t.done ? 'done' : lvl(t.due)) + '" data-id="' + t.id + '"><button class="check ' + (t.done ? 'on' : '') + '" data-a="toggle" aria-label="Erledigt">' + (t.done ? '✓' : '') + '</button><div class="grow"><b>' + esc(t.title) + '</b>' + (t.due ? '<span>fällig ' + fmtDate(t.due) + (!t.done && lvl(t.due) === 'l3' ? ' · STUFE 3' : !t.done && lvl(t.due) === 'l2' ? ' · STUFE 2' : '') + '</span>' : '') + '</div><button class="icon-btn" data-a="del" aria-label="Löschen">🗑</button></div>').join('') : '<div class="empty">Keine Aufgaben. Leg unten eine an.</div>';
    $('#list', root).onclick = async e => {
      const b = e.target.closest('button'); if (!b) return; const id = b.closest('.row').dataset.id; const t = list.find(x => x.id === id);
      try {
        if (b.dataset.a === 'toggle') await api('/api/items/tasks/' + id, { method: 'PUT', body: { title: t.title, due: t.due || '', done: !t.done } });
        else await api('/api/items/tasks/' + id, { method: 'DELETE', body: undefined });
        render();
      } catch (er) { toast(er.message, 1); }
    };
  };
  root.innerHTML = H('Aufgaben', 'Was ansteht') + '<form class="form" id="f"><label>Neue Aufgabe<input name="title" required maxlength="240" placeholder="z. B. Fahrschule anrufen"></label><label>Fällig<input type="date" name="due"></label><button class="btn">+ Hinzufügen</button></form><div class="list" id="list"></div>';
  $('#f', root).onsubmit = async e => { e.preventDefault(); const f = new FormData(e.target); try { await api('/api/items/tasks', { body: { title: f.get('title'), due: f.get('due') || '', done: false } }); e.target.reset(); render(); } catch (er) { toast(er.message, 1); } };
  render();
}

/* ---------- Notizen ---------- */
export function renderNotes(root) {
  let sel = null;
  const render = async () => {
    const list = await items('notes');
    $('#nlist', root).innerHTML = list.length ? list.map(n => '<div class="row" data-id="' + n.id + '"><div class="grow"><b>' + esc(n.title) + '</b><span>' + esc(n.content.slice(0, 70)) + '</span></div><button class="icon-btn" data-a="del" aria-label="Löschen">🗑</button></div>').join('') : '<div class="empty">Noch keine Notizen.</div>';
    $('#nlist', root).onclick = async e => {
      const r = e.target.closest('.row'); if (!r) return; const id = r.dataset.id;
      if (e.target.closest('[data-a="del"]')) { try { await api('/api/items/notes/' + id, { method: 'DELETE', body: undefined }); if (sel === id) sel = null; edit(); render(); } catch (er) { toast(er.message, 1); } return; }
      sel = id; edit(list.find(n => n.id === id));
    };
  };
  const edit = n => {
    $('#ed', root).innerHTML = '<form class="form col" id="nf"><label>Titel<input name="title" required maxlength="240" value="' + esc(n ? n.title : '') + '"></label><label>Text<textarea name="content" maxlength="20000">' + esc(n ? n.content : '') + '</textarea></label><div><button class="btn">✓ Speichern</button></div></form>';
    $('#nf', root).onsubmit = async e => { e.preventDefault(); const f = new FormData(e.target); const body = { title: f.get('title'), content: f.get('content') };
      try { if (sel) await api('/api/items/notes/' + sel, { method: 'PUT', body }); else { const r = await api('/api/items/notes', { body }); sel = r.id; } toast('Gespeichert'); render(); } catch (er) { toast(er.message, 1); } };
  };
  root.innerHTML = H('Notizen', 'Kurz festhalten', '<button class="btn" id="new">+ Neu</button>') + '<div class="grid wide"><div class="list" id="nlist"></div><div class="card" id="ed"></div></div>';
  $('#new', root).onclick = () => { sel = null; edit(); };
  edit(); render();
}

/* ---------- Geld ---------- */
export function renderMoney(root) {
  const render = async () => {
    const list = (await items('money')).sort((a, b) => a.date < b.date ? 1 : -1);
    const total = list.reduce((s, m) => s + m.cents, 0) / 100;
    $('#msum', root).innerHTML = '<span class="' + (total >= 0 ? 'money-pos' : 'money-neg') + '">' + total.toLocaleString('de-DE', { style: 'currency', currency: 'EUR' }) + '</span> <small>Gesamt</small>';
    $('#mlist', root).innerHTML = list.length ? list.map(m => '<div class="row" data-id="' + m.id + '"><div class="grow"><b>' + esc(m.title) + '</b><span>' + fmtDate(m.date) + (m.category ? ' · ' + esc(m.category) : '') + '</span></div><span class="' + (m.cents >= 0 ? 'money-pos' : 'money-neg') + '">' + (m.cents / 100).toLocaleString('de-DE', { style: 'currency', currency: 'EUR' }) + '</span><button class="icon-btn" aria-label="Löschen">🗑</button></div>').join('') : '<div class="empty">Keine Buchungen.</div>';
    $('#mlist', root).onclick = async e => { const b = e.target.closest('.icon-btn'); if (!b) return; try { await api('/api/items/money/' + b.closest('.row').dataset.id, { method: 'DELETE', body: undefined }); render(); } catch (er) { toast(er.message, 1); } };
  };
  root.innerHTML = H('Geld', 'Einnahmen (+) und Ausgaben (−)', '<div class="stat" id="msum"></div>') + '<form class="form" id="f"><label>Wofür<input name="title" required maxlength="240"></label><label>Betrag €<input name="amount" required inputmode="decimal" placeholder="-12,50"></label><label>Datum<input type="date" name="date" value="' + today() + '" required></label><label>Kategorie<input name="category" maxlength="80"></label><button class="btn">+ Buchen</button></form><div class="list" id="mlist"></div>';
  $('#f', root).onsubmit = async e => { e.preventDefault(); const f = new FormData(e.target); const amount = String(f.get('amount')).replace(',', '.');
    try { await api('/api/items/money', { body: { title: f.get('title'), amount, date: f.get('date'), category: f.get('category') } }); e.target.reset(); e.target.date.value = today(); render(); } catch (er) { toast(er.message, 1); } };
  render();
}

/* ---------- Training ---------- */
export function renderTraining(root) {
  const render = async () => {
    const list = (await items('training')).sort((a, b) => a.date < b.date ? 1 : -1);
    $('#tlist', root).innerHTML = list.length ? list.map(t => '<div class="row" data-id="' + t.id + '"><div class="grow"><b>' + esc(t.exercise) + '</b><span>' + fmtDate(t.date) + ' · ' + t.sets + '×' + t.reps + (t.kg > 0 ? ' · ' + t.kg + ' kg' : '') + (t.note ? ' · ' + esc(t.note) : '') + '</span></div><button class="icon-btn" aria-label="Löschen">🗑</button></div>').join('') : '<div class="empty">Noch kein Training eingetragen.</div>';
    $('#tlist', root).onclick = async e => { const b = e.target.closest('.icon-btn'); if (!b) return; try { await api('/api/items/training/' + b.closest('.row').dataset.id, { method: 'DELETE', body: undefined }); render(); } catch (er) { toast(er.message, 1); } };
  };
  root.innerHTML = H('Training', 'Sätze und Gewichte') + '<form class="form" id="f"><label>Übung<input name="exercise" required maxlength="240"></label><label>Datum<input type="date" name="date" value="' + today() + '" required></label><label>Sätze<input type="number" name="sets" min="1" value="3" required></label><label>Wdh.<input type="number" name="reps" min="1" value="10" required></label><label>kg<input name="kg" inputmode="decimal" value="0"></label><label>Notiz<input name="note" maxlength="2000"></label><button class="btn">+ Eintragen</button></form><div class="list" id="tlist"></div>';
  $('#f', root).onsubmit = async e => { e.preventDefault(); const f = Object.fromEntries(new FormData(e.target)); f.kg = String(f.kg).replace(',', '.');
    try { await api('/api/items/training', { body: f }); toast('Eingetragen'); render(); } catch (er) { toast(er.message, 1); } };
  render();
}

/* ---------- Dateien ---------- */
let filesPath = '';
export function setFilesPath(p) { filesPath = p || ''; }
export function renderFiles(root) {
  const path = filesPath;
  root.innerHTML = H('Dateien', 'Deine Ablage auf dem Server') + '<form class="quick" id="sf"><input name="q" placeholder="Notizen und Dokumente durchsuchen …" autocomplete="off" enterkeyhint="search"><button class="btn">Suchen</button></form><div class="list" id="sres" hidden></div><div class="crumbs" id="cr"></div><div class="list" id="fl"><div class="skeleton"></div></div>';
  $('#sf', root).onsubmit = async e => {
    e.preventDefault();
    const q = String(new FormData(e.target).get('q')).trim(), box = $('#sres', root);
    if (q.length < 2) { box.hidden = true; return; }
    box.hidden = false; box.innerHTML = '<div class="empty">Suche läuft …</div>';
    try {
      const d = await cop('search', { q });
      box.innerHTML = (d.hits || []).length ? d.hits.map(h => '<div class="row" data-p="' + esc(h.path) + '"><div class="grow"><b>' + esc(h.path.split('/').slice(-1)[0]) + '</b><span>' + esc(h.path.split('/').slice(0, -1).join(' / ')) + ' · Zeile ' + h.line + '</span><span>' + esc(h.text) + '</span></div></div>').join('') + '<div class="sub">Höchstens 40 Treffer. Tippen öffnet die Datei.</div>' : '<div class="empty">Nichts gefunden.</div>';
      box.onclick = ev => { const r = ev.target.closest('.row'); if (r) openViewer('Bibliothek/' + r.dataset.p, r.dataset.p.split('/').slice(-1)[0]); };
    } catch (er) { box.innerHTML = '<div class="empty">' + esc(er.message) + '</div>'; }
  };
  const parts = path ? path.split('/') : [];
  $('#cr', root).innerHTML = '<button data-p="">Start</button>' + parts.map((p, i) => ' / <button data-p="' + esc(parts.slice(0, i + 1).join('/')) + '">' + esc(p) + '</button>').join('');
  $('#cr', root).onclick = e => { const b = e.target.closest('button'); if (b) { filesPath = b.dataset.p; renderFiles(root); } };
  api('/api/files?path=' + encodeURIComponent(path)).then(d => {
    $('#fl', root).innerHTML = d.entries.length ? d.entries.map(f => '<div class="row" data-n="' + esc(f.name) + '" data-d="' + (f.directory ? 1 : 0) + '"><span class="tag">' + (f.directory ? '▤' : '□') + '</span><div class="grow"><b>' + esc(f.name) + '</b><span>' + (f.directory ? 'Ordner' : fmtBytes(f.size)) + '</span></div>' + (f.directory ? '' : '<a class="btn small ghost" href="/api/file?path=' + encodeURIComponent((path ? path + '/' : '') + f.name) + '">Laden</a>') + '</div>').join('') : '<div class="empty">Dieser Ordner ist leer.</div>';
    $('#fl', root).onclick = e => { const r = e.target.closest('.row'); if (!r || e.target.closest('a')) return; const full = (path ? path + '/' : '') + r.dataset.n; if (r.dataset.d === '1') { filesPath = full; renderFiles(root); } else openViewer(full, r.dataset.n); };
  }).catch(er => { $('#fl', root).innerHTML = '<div class="empty">' + esc(er.message) + '</div>'; });
}

/* ---------- System ---------- */
export async function renderSystem(root, ctx) {
  root.innerHTML = H('System', 'Zustand des Servers') + '<div class="skeleton"></div>';
  let st;
  try { st = await api('/api/status'); } catch (er) {
    root.innerHTML = H('System', 'Zustand des Servers') + '<div class="holo danger"><h2 class="holo-title">Statusdienst nicht erreichbar<span class="sub">' + esc(er.message) + '</span></h2>' +
      '<p class="muted">Der Host-Agent (<span class="mono">/run/ma-home/agent.sock</span>) lässt das Portal nicht durch. Betroffen: Systemstatus, Dienst-Neustart und Dokument-Vorschau/Druck. Alle anderen Bereiche laufen normal.</p></div>';
    return;
  }
  const bk = st.backup_status;
  const cont = (st.containers || []).map(c => '<div class="row"><span class="tag ' + (c.state === 'running' ? 'ok' : 'bad') + '">' + esc(c.state) + '</span><div class="grow"><b>' + esc(c.name) + '</b>' + (c.oom ? '<span>Speicher knapp (OOM)</span>' : '') + '</div>' + (ctx.me.admin && ['filebrowser', 'ntfy', 'couchdb'].includes(c.name) ? '<button class="btn small ghost" data-s="' + esc(c.name) + '">Neu starten</button>' : '') + '</div>').join('');
  root.innerHTML = H('System', 'Zustand des Servers') + '<div class="grid">' +
    '<div class="card"><h2>Laufzeit</h2><div class="stat">' + fmtUp(st.uptime) + '</div></div>' +
    '<div class="card"><h2>Drucker</h2><span class="tag ' + (st.printer ? 'ok' : 'warn') + '">' + (st.printer ? 'bereit' : 'nicht bereit') + '</span> <span class="tag ' + (st.scanner ? 'ok' : 'warn') + '">Scanner ' + (st.scanner ? 'ja' : 'nein') + '</span></div>' +
    '<div class="card"><h2>Backup</h2>' + (bk ? '<span class="tag ' + (/^OK/.test(bk.state) ? 'ok' : 'warn') + '">' + esc(bk.state) + '</span><div class="sub">' + (bk.time ? new Date(bk.time).toLocaleString('de-DE') : '') + '</div>' : '<span class="tag warn">nicht eingerichtet</span>') + '</div></div>' +
    (cont ? '<div class="card mt"><h2>Dienste</h2><div class="list">' + cont + '</div></div>' : '') +
    '<p class="sub"><a href="/api/export">Meine Daten exportieren (JSON)</a></p>';
  root.onclick = async e => { const b = e.target.closest('[data-s]'); if (!b) return; b.disabled = true; try { await api('/api/service', { body: { service: b.dataset.s, verb: 'restart' } }); toast(b.dataset.s + ' startet neu'); } catch (er) { toast(er.message, 1); } b.disabled = false; };
}

/* ---------- Terminal ---------- */
const TERM_DIRS = { server: 'Server-Home', maserver: 'MA-Server', bibliothek: 'Bibliothek', notizen: 'Notizen' };
const termState = { out: '', hist: [], hi: 0, busy: false, ctl: null, dir: 'auto', ask: '' };
function termAutoDir(cmd) {
  if (/vault-notizen|vault-q|\bvault\b|\.md\b|obsidian|notiz/i.test(cmd)) return 'notizen';
  if (/\/srv\/ma-home|\blibrary\b|\binbox\b|\bmedia\b|bibliothek|\.(mp3|flac|pdf|docx?|xlsx?|pptx?|jpe?g|png)\b/i.test(cmd)) return 'bibliothek';
  if (/MA-Server|\bgit\b|\b(tests?|scripts?|portal-ui|server|docs|app)\//i.test(cmd) || /\b(CHANGELOG|BACKLOG|CLAUDE)\.md\b|portal_smoke|pytest|\bnpm\b|\bnode\b|\bmake\b|\.py\b|\.js\b|\.sh\b/i.test(cmd)) return 'maserver';
  return 'server';
}
export function renderTerm(root) {
  root.innerHTML = H('Terminal', 'Befehle als Benutzer andrew auf dem Server (sudo nach Einrichtung, höchstens 120 s)', '<button class="btn ghost small" id="tclr">Leeren</button>') +
    '<div class="cwrap"><pre class="tout" id="tout"></pre><form class="cform" id="tf"><div class="copts"><label>Ordner<select name="dir"><option value="auto">Automatisch</option><option value="server">Server-Home</option><option value="maserver">MA-Server (Projekt)</option><option value="bibliothek">Bibliothek</option><option value="notizen">Notizen</option></select></label></div>' +
    '<div class="cin"><input name="cmd" class="tcmd" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Befehl, z. B. df -h"><button class="btn" id="trun">Ausführen</button><button class="btn ghost" type="button" id="tstop" hidden>Stopp</button></div></form></div>';
  const out = $('#tout', root), f = $('#tf', root);
  f.dir.value = termState.dir; f.dir.onchange = () => { termState.dir = f.dir.value; };
  const show = () => { out.textContent = termState.out; out.scrollTop = out.scrollHeight; };
  const add = t => { termState.out = (termState.out + t).slice(-200000); show(); };
  show();
  $('#tclr', root).onclick = () => { termState.out = ''; show(); };
  $('#tstop', root).onclick = () => { if (termState.ctl) termState.ctl.abort(); };
  f.cmd.onkeydown = e => {
    if (e.key === 'ArrowUp' && termState.hist.length) { termState.hi = Math.max(0, termState.hi - 1); f.cmd.value = termState.hist[termState.hi]; e.preventDefault(); }
    else if (e.key === 'ArrowDown') { termState.hi = Math.min(termState.hist.length, termState.hi + 1); f.cmd.value = termState.hist[termState.hi] || ''; e.preventDefault(); }
  };
  f.onsubmit = async e => {
    e.preventDefault();
    const cmd = String(f.cmd.value).trim(); if (!cmd || termState.busy) return;
    const RISKY = /(^|[;&|]\s*)sudo\s|(^|[;&|]\s*)(sudo\s+)?(rm\s+(-\w*[rf]\w*|--recursive|--force)|dd\s|mkfs|shutdown|reboot|poweroff|chmod\s+-R|chown\s+-R|mv\s+\/)|\|\s*(sudo\s+)?(ba)?sh\b|>\s*\/dev\/(sd|nvme)|:\(\)\s*\{/;
    if (RISKY.test(cmd) && termState.ask !== cmd) { termState.ask = cmd; toast('Riskanter Befehl. Zum Bestätigen denselben Befehl noch einmal ausführen.', 1); return; }
    termState.ask = '';
    termState.hist.push(cmd); termState.hist = termState.hist.slice(-50); termState.hi = termState.hist.length;
    f.cmd.value = ''; termState.busy = true; $('#trun', root).disabled = true; $('#tstop', root).hidden = false;
    const dir = f.dir.value === 'auto' ? termAutoDir(cmd) : f.dir.value;
    add((f.dir.value === 'auto' ? '[Ordner: ' + TERM_DIRS[dir] + ']\n' : '') + '$ ' + cmd + '\n');
    termState.ctl = new AbortController();
    try {
      const r = await fetch('/api/term', { method: 'POST', credentials: 'same-origin', signal: termState.ctl.signal, headers: { 'Content-Type': 'application/json', 'X-MA-Request': '1' }, body: JSON.stringify({ cmd, dir }) });
      if (!r.ok) throw new Error(r.status === 403 ? 'Nur für Administratoren.' : 'Fehler ' + r.status);
      const reader = r.body.getReader(), dec = new TextDecoder(); let buf = '';
      for (;;) {
        const { done, value } = await reader.read(); if (done) break;
        buf += dec.decode(value, { stream: true });
        let i;
        while ((i = buf.indexOf('\n')) >= 0) {
          const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1); if (!line) continue;
          let d; try { d = JSON.parse(line); } catch (er) { continue; }
          if (d.type === 'out') add(d.t); else if (d.type === 'end') add('[Ende, Code ' + d.code + ']\n\n'); else if (d.type === 'error') add('[Fehler: ' + d.error + ']\n');
        }
      }
    } catch (er) { add(er.name === 'AbortError' ? '[Abgebrochen]\n\n' : '[Fehler: ' + er.message + ']\n'); }
    termState.busy = false; termState.ctl = null;
    const b = $('#trun', root); if (b) { b.disabled = false; $('#tstop', root).hidden = true; }
  };
}

/* ---------- Verbindungen ---------- */
export async function renderVerbindungen(root) {
  root.innerHTML = H('Verbindungen', 'Konten, die Claude nutzen kann') + '<div class="skeleton"></div>';
  const d = await cop('connectors', {});
  if (!d.ok) { root.innerHTML = H('Verbindungen') + '<div class="empty">' + esc(d.error || 'Keine Daten') + '</div>'; return; }
  const label = { ok: 'verbunden', login: 'Anmeldung nötig', fehler: 'Fehler' };
  const rank = { login: 0, fehler: 1, ok: 2 };
  const its = d.items.slice().sort((a, b) => rank[a.state] - rank[b.state] || a.name.localeCompare(b.name));
  const need = its.filter(x => x.state !== 'ok').length;
  root.innerHTML = H('Verbindungen', its.length + ' Verbindungen · ' + need + ' brauchen Aufmerksamkeit') +
    '<div class="list">' + its.map(x => '<div class="row"><div class="grow"><b>' + esc(x.name) + '</b><span>' + esc(x.url) + '</span></div><span class="tag">' + label[x.state] + '</span></div>').join('') + '</div>' +
    '<div class="empty">Anmelden geht nur in den Konnektor-Einstellungen von claude.ai, nicht hier. Im Chat gelten die Verbindungen nur im Modus „konnektoren“ und „voll“.</div>';
}
