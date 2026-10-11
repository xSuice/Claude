/* MA Home – Oberfläche (ohne Bibliotheken). Nutzt die vorhandene API von portal.py. */
(() => {
'use strict';
const $ = (s, r = document) => r.querySelector(s);
const view = $('#view');
const ICONS = {
  home: '<path d="M3 11l9-8 9 8M5 10v10h14V10"/>',
  tasks: '<path d="M9 11l3 3 8-8M4 12v7a1 1 0 001 1h14"/>',
  notes: '<path d="M6 3h9l4 4v14H6zM14 3v5h5M9 13h7M9 17h5"/>',
  money: '<rect x="3" y="6" width="18" height="12" rx="2"/><circle cx="12" cy="12" r="2.5"/>',
  training: '<path d="M3 9v6M6 7v10M18 7v10M21 9v6M6 12h12"/>',
  files: '<path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>',
  system: '<rect x="3" y="4" width="18" height="6" rx="1.5"/><rect x="3" y="14" width="18" height="6" rx="1.5"/><path d="M7 7h.01M7 17h.01"/>',
  trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
  check: '<path d="M5 12l5 5 9-10"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  down: '<path d="M12 4v11m0 0l-4-4m4 4l4-4M5 20h14"/>',
  ha: '<path d="M3 11l9-8 9 8M6 10v9h12v-9M10 19v-5h4v5"/>',
  bell: '<path d="M6 16V11a6 6 0 1112 0v5l2 2H4zM10 20a2 2 0 004 0"/>',
  sync: '<path d="M20 11a8 8 0 00-14-4M4 4v4h4M4 13a8 8 0 0014 4M20 20v-4h-4"/>',
  claude: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM18 16l.8 2.2L21 19l-2.2.8L18 22l-.8-2.2L15 19l2.2-.8z"/>',
  send: '<path d="M4 12l16-8-6 16-3-7z"/>',
  fimg: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 17l-5-5-9 8"/>',
  ffilm: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M10 9l5 3-5 3z"/>',
  fmusic: '<path d="M9 18V6l11-2v12"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/>',
  fzip: '<path d="M6 3h9l4 4v14H6zM11 5v2M11 9v2M11 13v2"/>',
  fcode: '<path d="M9 8l-4 4 4 4M15 8l4 4-4 4"/>',
  fsheet: '<rect x="4" y="3" width="16" height="18" rx="1.5"/><path d="M4 9h16M4 15h16M10 3v18"/>',
  fpdf: '<path d="M6 3h9l4 4v14H6z"/><path d="M9 14h6M9 17h4"/>',
  wissen: '<circle cx="6" cy="6" r="2.2"/><circle cx="18" cy="8" r="2.2"/><circle cx="9" cy="18" r="2.2"/><circle cx="19" cy="19" r="1.6"/><path d="M8 7l8 1M7 8l1.6 8M11 17.6l6.4 1M17.6 10l1 7"/>',
  logo: '<path d="M12 2.5c.9 3 4.2 4.6 4.2 9a4.2 4.2 0 01-8.4 0c0-1.8.8-3 1.7-4 .3 1.1.9 1.7 1.5 1.9C10.8 7.6 11.1 5 12 2.5z"/>'
};
const ico = n => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[n] || ''}</svg>`;
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const today = () => new Date().toISOString().slice(0, 10);
const fmtBytes = n => n >= 1e9 ? (n / 1e9).toFixed(1) + ' GB' : n >= 1e6 ? (n / 1e6).toFixed(1) + ' MB' : n >= 1e3 ? Math.round(n / 1e3) + ' KB' : n + ' B';
const fmtUp = s => { const d = Math.floor(s / 86400), h = Math.floor(s % 86400 / 3600), m = Math.floor(s % 3600 / 60); return d ? `${d} T ${h} Std` : h ? `${h} Std ${m} Min` : `${m} Min`; };
const lvl = d => { if (!d) return ''; const diff = (new Date(d + 'T12:00:00') - new Date()) / 864e5; return diff < 0.5 ? 'l3' : diff < 3.5 ? 'l2' : ''; };
const fmtDate = d => d ? new Date(d + 'T12:00:00').toLocaleDateString('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit' }) : '';

const CANDLE = '<svg viewBox="0 0 24 32" aria-hidden="true"><path d="M7 14h10v16H7zM12 14v-3"/><path d="M12 10c-1.6-1.2-1.4-2.6-.2-3.6 1-.9.9-2.1.3-3"/></svg>';
new MutationObserver(() => document.querySelectorAll('.empty:not([data-c])').forEach(e => { e.dataset.c = '1'; e.insertAdjacentHTML('afterbegin', '<span class="candle">' + CANDLE + '</span>'); })).observe(view, { childList: true, subtree: true });

let me = { user: '', admin: false, domain: '' };
let toastTimer;
function toast(msg, err) { const t = $('#toast'); t.textContent = msg; t.className = 'toast show' + (err ? ' err' : ''); clearTimeout(toastTimer); toastTimer = setTimeout(() => t.className = 'toast', 3200); }

async function api(path, opts = {}) {
  const o = { credentials: 'same-origin', headers: {}, ...opts };
  if (opts.body !== undefined) { o.method = opts.method || 'POST'; o.body = JSON.stringify(opts.body); o.headers = { 'Content-Type': 'application/json', 'X-MA-Request': '1' }; }
  else if (opts.method && opts.method !== 'GET') o.headers = { 'Content-Type': 'application/json', 'X-MA-Request': '1' };
  const r = await fetch(path, o);
  let data = null; try { data = await r.json(); } catch (e) { /* leer */ }
  if (!r.ok) throw new Error((data && data.error) || `Fehler ${r.status}`);
  return data;
}
const items = k => api('/api/items/' + k).then(d => d.items);

const TABS = [['home', 'Lage'], ['tasks', 'Aufgaben'], ['notes', 'Notizen'], ['money', 'Geld'], ['training', 'Training'], ['claude', 'Claude'], ['wissen', 'Wissen'], ['files', 'Dateien'], ['system', 'System']];
function buildNav() {
  $('#nav').innerHTML = TABS.map(([id, name]) => `<button data-t="${id}">${ico(id)}<span>${name}</span></button>`).join('');
  $('#nav').addEventListener('click', e => { const b = e.target.closest('button'); if (b) location.hash = '#/' + b.dataset.t; });
}
function head(title, sub, extra = '') { return `<div class="top"><div><div class="kicker">MA Home · ${esc(title)}</div><h1>${title}</h1><div class="sub">${sub || ''}</div></div>${extra}</div>`; }
const greeting = () => { const h = new Date().getHours(); return h < 5 ? 'Gute Nacht' : h < 11 ? 'Guten Morgen' : h < 17 ? 'Hallo' : h < 22 ? 'Guten Abend' : 'Gute Nacht'; };

/* ---------- Lage (Übersicht, alles anklickbar) ---------- */
const KEYNOTES = [
  ['Übersicht', 'Übersicht.md', 'Startseite des Vaults'], ['Fristen', '_Claude-Memory/Dienste/Fristen-Uebersicht.md', 'Was ansteht'],
  ['Mail-Tagesbericht', '_Claude-Memory/Dienste/Mail-Tagesbericht.md', 'Neues in deinen Mails'], ['Morgenbrief', '_Claude-Memory/Dienste/Morgenbrief.md', 'Heute in Kürze'], ['Server-Abgleich', '_Claude-Memory/Dienste/Server-Abgleich.md', 'Was ist neu auf dem Server'],
  ['MA-Server Zentrale', '30 Technik/MA-Server/MA-Server Zentrale.md', 'Stand der Zentrale'], ['Profil', '_Claude-Memory/Profil.md', 'Wer du bist, wie wir arbeiten'],
  ['Crimson Zone', '20 Projekte/Crimson Zone/Crimson Zone.md', 'Projekt'], ['Eternal Bonds', '20 Projekte/Projekt Schmejd/Projekt Schmejd.md', 'Projekt']];
async function home() {
  view.innerHTML = head('Lage', new Date().toLocaleDateString('de-DE', { weekday: 'long', day: 'numeric', month: 'long' })) + '<div class="skeleton"></div>';
  const [st, tasks, money, tr, gr] = await Promise.all([
    api('/api/status').catch(() => null), items('tasks').catch(() => []), items('money').catch(() => []), items('training').catch(() => []), loadGraph().catch(() => null)]);
  const open = tasks.filter(t => !t.done).sort((a, b) => (a.due || '9') < (b.due || '9') ? -1 : 1);
  const month = today().slice(0, 7);
  const sum = money.filter(m => m.date.startsWith(month)).reduce((s, m) => s + m.cents, 0) / 100;
  let dom = 'ma-server.duckdns.org'; try { dom = new URL(me.domain).host || dom; } catch (e) { /* Standard */ }
  const bk = st && st.backup_status && st.backup_status.state;
  const pills = st ? `<span class="pill dot">Server online</span><span class="pill">Laufzeit ${fmtUp(st.uptime)}</span>` + (bk ? `<span class="pill ${/^OK/.test(bk) ? 'dot' : 'dot off'}">Backup: ${esc(String(bk).slice(0, 38))}</span>` : '') : '<span class="pill dot off">Status nicht abrufbar</span>';
  const bar = (p, hot) => `<div class="bar ${hot ? 'hot' : ''}"><i data-p="${Math.round(p)}"></i></div>`;
  const hubs = gr ? gr.nodes.map((n, i) => [n, i]).sort((a, b) => b[0].d - a[0].d).slice(0, 14) : [];
  const taskRows = open.slice(0, 5).map(t => `<a class="row ${lvl(t.due)}" href="#/tasks"><div class="grow"><b>${esc(t.title)}</b>${t.due ? `<span>fällig ${fmtDate(t.due)}${lvl(t.due) === 'l3' ? ' · STUFE 3' : lvl(t.due) === 'l2' ? ' · STUFE 2' : ''}</span>` : ''}</div></a>`).join('');
  view.innerHTML = head('Lage', new Date().toLocaleDateString('de-DE', { weekday: 'long', day: 'numeric', month: 'long' })) + `
  <a class="hero hero-link" href="#/system"><h2>${greeting()}, ${esc(me.user)}.</h2><p>${open.length ? `${open.length} offene Aufgabe${open.length > 1 ? 'n' : ''}` + (open[0].due ? `, als Nächstes: ${esc(open[0].title)} (${fmtDate(open[0].due)})` : '') : 'Keine offenen Aufgaben. Alles erledigt.'}</p><div class="pills">${pills}</div></a>
  <form class="quick" id="qf"><input name="q" placeholder="Frag Claude auf deinem Server … (Enter)" autocomplete="off"><button class="btn">${ico('claude')} Fragen</button></form>
  <div class="grid wide">
    <div class="card"><h2>${ico('tasks')} Aufgaben <a class="more" href="#/tasks">alle</a></h2><div class="list">${taskRows || '<div class="empty">Keine offenen Aufgaben.</div>'}</div></div>
    <div class="card"><h2>${ico('notes')} Wichtige Notizen</h2><div class="chips">${KEYNOTES.map(([n, p, d], i) => `<button class="chip" data-k="${i}" title="${esc(d)}">${esc(n)}</button>`).join('')}</div></div>
    ${gr ? `<div class="card"><h2>${ico('wissen')} Wissen <a class="more" href="#/wissen">Graph öffnen</a></h2><div class="chips">${hubs.map(([n, i]) => `<button class="chip" data-g="${i}" title="${n.d} Verbindungen">${esc(n.n)}</button>`).join('')}</div><div class="sub mt">${gr.nodes.length} Notizen · ${gr.links.length} Verbindungen</div></div>` : ''}
  </div>
  <div class="grid mt">
    ${st ? `<a class="card statlink" href="#/system"><h2>Speicher</h2><div class="stat">${fmtBytes(st.disk_total - st.disk_used)} <small>frei</small></div>${bar(st.disk_used / st.disk_total * 100, st.disk_used / st.disk_total > .85)}<div class="sub">${fmtBytes(st.disk_used)} von ${fmtBytes(st.disk_total)}</div></a>
    <a class="card statlink" href="#/system"><h2>Arbeitsspeicher</h2><div class="stat">${Math.round(st.ram_used / st.ram_total * 100)}<small> %</small></div>${bar(st.ram_used / st.ram_total * 100, st.ram_used / st.ram_total > .9)}<div class="sub">${fmtBytes(st.ram_used)} von ${fmtBytes(st.ram_total)}</div></a>` : ''}
    <a class="card statlink" href="#/money"><h2>${ico('money')} Dieser Monat</h2><div class="stat ${sum >= 0 ? 'money-pos' : 'money-neg'}">${sum.toLocaleString('de-DE', { style: 'currency', currency: 'EUR' })}</div><div class="sub">Summe der Buchungen</div></a>
    <a class="card statlink" href="#/training"><h2>${ico('training')} Training</h2><div class="stat">${tr.length ? esc(tr[0].exercise) : '–'}</div><div class="sub">${tr.length ? `zuletzt ${fmtDate(tr[0].date)}, ${tr[0].sets}×${tr[0].reps} ${tr[0].kg > 0 ? tr[0].kg + ' kg' : ''}` : 'noch kein Eintrag'}</div></a>
  </div>
  <div class="card mt"><h2>Alles auf einen Klick</h2><div class="apps">
    <a class="app" href="#/claude"><div class="ic c3">${ico('claude')}</div><b>Claude</b><span>Chat auf dem Server</span></a>
    <a class="app" href="#/wissen"><div class="ic c1">${ico('wissen')}</div><b>Wissen</b><span>Graph der Notizen</span></a>
    <a class="app" href="#/files"><div class="ic c4">${ico('files')}</div><b>Dateien</b><span>Ablage, Bibliothek, Backup</span></a>
    <a class="app" href="#/files?p=${encodeURIComponent('Bibliothek/inbox')}"><div class="ic c2">${ico('down')}</div><b>Eingang</b><span>Neue Dateien</span></a>
    <a class="app" href="https://ha.${dom}/"><div class="ic c1">${ico('ha')}</div><b>Home Assistant</b><span>Smart Home</span></a>
    <a class="app" href="https://ntfy.${dom}/"><div class="ic c3">${ico('bell')}</div><b>Meldungen</b><span>ntfy</span></a>
  </div></div>`;
  view.querySelectorAll('.bar i').forEach(i => requestAnimationFrame(() => i.style.setProperty('--p', i.dataset.p)));
  $('#qf').onsubmit = e => { e.preventDefault(); const q = String(new FormData(e.target).get('q')).trim(); if (!q) return; try { sessionStorage.setItem('ma-claude-q', q); } catch (er) { /* ohne Speicher */ } location.hash = '#/claude'; };
  view.querySelectorAll('.chip[data-k]').forEach(b => { b.onclick = () => { const [n, p] = KEYNOTES[+b.dataset.k]; openViewer('Bibliothek/vault-notizen/' + p, p.split('/').pop()); }; });
  view.querySelectorAll('.chip[data-g]').forEach(b => { b.onclick = () => openNote(+b.dataset.g); });
}

/* ---------- Aufgaben ---------- */
async function tasks() {
  const render = async () => {
    const list = (await items('tasks')).sort((a, b) => (a.done - b.done) || ((a.due || '9') < (b.due || '9') ? -1 : 1));
    $('#list').innerHTML = list.length ? list.map(t => `<div class="row ${t.done ? 'done' : lvl(t.due)}" data-id="${t.id}"><button class="check ${t.done ? 'on' : ''}" data-a="toggle" aria-label="Erledigt">${t.done ? ico('check') : ''}</button><div class="grow"><b>${esc(t.title)}</b>${t.due ? `<span>fällig ${fmtDate(t.due)}${!t.done && lvl(t.due) === 'l3' ? ' · STUFE 3' : !t.done && lvl(t.due) === 'l2' ? ' · STUFE 2' : ''}</span>` : ''}</div><button class="icon-btn" data-a="del" aria-label="Löschen">${ico('trash')}</button></div>`).join('') : '<div class="empty">Keine Aufgaben. Leg unten eine an.</div>';
    $('#list').onclick = async e => {
      const b = e.target.closest('button'); if (!b) return; const id = b.closest('.row').dataset.id; const t = list.find(x => x.id === id);
      try {
        if (b.dataset.a === 'toggle') await api(`/api/items/tasks/${id}`, { method: 'PUT', body: { title: t.title, due: t.due || '', done: !t.done } });
        else await api(`/api/items/tasks/${id}`, { method: 'DELETE', body: undefined });
        render();
      } catch (er) { toast(er.message, 1); }
    };
  };
  view.innerHTML = head('Aufgaben', 'Was ansteht') + `<form class="form" id="f"><label>Neue Aufgabe<input name="title" required maxlength="240" placeholder="z. B. Fahrschule anrufen"></label><label>Fällig<input type="date" name="due"></label><button class="btn">${ico('plus')} Hinzufügen</button></form><div class="list" id="list"></div>`;
  $('#f').onsubmit = async e => { e.preventDefault(); const f = new FormData(e.target); try { await api('/api/items/tasks', { body: { title: f.get('title'), due: f.get('due') || '', done: false } }); e.target.reset(); render(); } catch (er) { toast(er.message, 1); } };
  render();
}

/* ---------- Notizen ---------- */
async function notes() {
  let sel = null;
  const render = async () => {
    const list = await items('notes');
    $('#nlist').innerHTML = list.length ? list.map(n => `<div class="row" data-id="${n.id}"><div class="grow"><b>${esc(n.title)}</b><span>${esc(n.content.slice(0, 70))}</span></div><button class="icon-btn" data-a="del" aria-label="Löschen">${ico('trash')}</button></div>`).join('') : '<div class="empty">Noch keine Notizen.</div>';
    $('#nlist').onclick = async e => {
      const r = e.target.closest('.row'); if (!r) return; const id = r.dataset.id;
      if (e.target.closest('[data-a="del"]')) { try { await api(`/api/items/notes/${id}`, { method: 'DELETE', body: undefined }); if (sel === id) sel = null; edit(); render(); } catch (er) { toast(er.message, 1); } return; }
      sel = id; edit(list.find(n => n.id === id));
    };
  };
  const edit = n => {
    $('#ed').innerHTML = `<form class="form col" id="nf"><label>Titel<input name="title" required maxlength="240" value="${esc(n ? n.title : '')}"></label><label>Text<textarea name="content" maxlength="20000">${esc(n ? n.content : '')}</textarea></label><div><button class="btn">${ico('check')} Speichern</button></div></form>`;
    $('#nf').onsubmit = async e => { e.preventDefault(); const f = new FormData(e.target); const body = { title: f.get('title'), content: f.get('content') };
      try { if (sel) await api(`/api/items/notes/${sel}`, { method: 'PUT', body }); else { const r = await api('/api/items/notes', { body }); sel = r.id; } toast('Gespeichert'); render(); } catch (er) { toast(er.message, 1); } };
  };
  view.innerHTML = head('Notizen', 'Kurz festhalten', `<button class="btn" id="new">${ico('plus')} Neu</button>`) + '<div class="grid wide"><div class="list" id="nlist"></div><div class="card" id="ed"></div></div>';
  $('#new').onclick = () => { sel = null; edit(); };
  edit(); render();
}

/* ---------- Geld ---------- */
async function money() {
  const render = async () => {
    const list = (await items('money')).sort((a, b) => a.date < b.date ? 1 : -1);
    const total = list.reduce((s, m) => s + m.cents, 0) / 100;
    $('#msum').innerHTML = `<span class="${total >= 0 ? 'money-pos' : 'money-neg'}">${total.toLocaleString('de-DE', { style: 'currency', currency: 'EUR' })}</span> <small>Gesamt</small>`;
    $('#mlist').innerHTML = list.length ? list.map(m => `<div class="row" data-id="${m.id}"><div class="grow"><b>${esc(m.title)}</b><span>${fmtDate(m.date)}${m.category ? ' · ' + esc(m.category) : ''}</span></div><span class="${m.cents >= 0 ? 'money-pos' : 'money-neg'}">${(m.cents / 100).toLocaleString('de-DE', { style: 'currency', currency: 'EUR' })}</span><button class="icon-btn" aria-label="Löschen">${ico('trash')}</button></div>`).join('') : '<div class="empty">Keine Buchungen.</div>';
    $('#mlist').onclick = async e => { const b = e.target.closest('.icon-btn'); if (!b) return; try { await api(`/api/items/money/${b.closest('.row').dataset.id}`, { method: 'DELETE', body: undefined }); render(); } catch (er) { toast(er.message, 1); } };
  };
  view.innerHTML = head('Geld', 'Einnahmen (+) und Ausgaben (−)', '<div class="stat" id="msum"></div>') + `<form class="form" id="f"><label>Wofür<input name="title" required maxlength="240"></label><label>Betrag €<input name="amount" required inputmode="decimal" placeholder="-12,50"></label><label>Datum<input type="date" name="date" value="${today()}" required></label><label>Kategorie<input name="category" maxlength="80"></label><button class="btn">${ico('plus')} Buchen</button></form><div class="list" id="mlist"></div>`;
  $('#f').onsubmit = async e => { e.preventDefault(); const f = new FormData(e.target); const amount = String(f.get('amount')).replace(',', '.');
    try { await api('/api/items/money', { body: { title: f.get('title'), amount, date: f.get('date'), category: f.get('category') } }); e.target.reset(); e.target.date.value = today(); render(); } catch (er) { toast(er.message, 1); } };
  render();
}

/* ---------- Training ---------- */
async function training() {
  const render = async () => {
    const list = (await items('training')).sort((a, b) => a.date < b.date ? 1 : -1);
    $('#tlist').innerHTML = list.length ? list.map(t => `<div class="row" data-id="${t.id}"><div class="grow"><b>${esc(t.exercise)}</b><span>${fmtDate(t.date)} · ${t.sets}×${t.reps}${t.kg > 0 ? ' · ' + t.kg + ' kg' : ''}${t.note ? ' · ' + esc(t.note) : ''}</span></div><button class="icon-btn" aria-label="Löschen">${ico('trash')}</button></div>`).join('') : '<div class="empty">Noch kein Training eingetragen.</div>';
    $('#tlist').onclick = async e => { const b = e.target.closest('.icon-btn'); if (!b) return; try { await api(`/api/items/training/${b.closest('.row').dataset.id}`, { method: 'DELETE', body: undefined }); render(); } catch (er) { toast(er.message, 1); } };
  };
  view.innerHTML = head('Training', 'Sätze und Gewichte') + `<form class="form" id="f"><label>Übung<input name="exercise" required maxlength="240"></label><label>Datum<input type="date" name="date" value="${today()}" required></label><label>Sätze<input type="number" name="sets" min="1" value="3" required></label><label>Wdh.<input type="number" name="reps" min="1" value="10" required></label><label>kg<input name="kg" inputmode="decimal" value="0"></label><label>Notiz<input name="note" maxlength="2000"></label><button class="btn">${ico('plus')} Eintragen</button></form><div class="list" id="tlist"></div>`;
  $('#f').onsubmit = async e => { e.preventDefault(); const f = Object.fromEntries(new FormData(e.target)); f.kg = String(f.kg).replace(',', '.');
    try { await api('/api/items/training', { body: f }); toast('Eingetragen'); render(); } catch (er) { toast(er.message, 1); } };
  render();
}

const FTYPES = [
  [/^(md|markdown|txt|rtf|doc|docx|odt|log)$/, 'notes', 'Text'], [/^pdf$/, 'fpdf', 'PDF'],
  [/^(xls|xlsx|ods|csv)$/, 'fsheet', 'Tabelle'], [/^(ppt|pptx|odp)$/, 'fpdf', 'Präsentation'],
  [/^(png|jpe?g|gif|webp|svg|bmp|tiff?|heic|ico)$/, 'fimg', 'Bild'], [/^(mp4|webm|mov|mkv|avi)$/, 'ffilm', 'Video'],
  [/^(mp3|wav|ogg|m4a|flac|aac)$/, 'fmusic', 'Audio'], [/^(zip|7z|rar|tar|gz|tgz|xz|bz2)$/, 'fzip', 'Archiv'],
  [/^(py|js|ts|sh|bash|ps1|bat|json|ya?ml|toml|ini|conf|xml|html|css|sql|java|c|h|cpp|go|rs|service|timer|base|canvas)$/, 'fcode', 'Code']];
function ftag(f) {
  if (f.directory) return '<span class="tag">' + ico('files') + '</span>';
  const ext = (f.name.includes('.') ? f.name.split('.').pop() : '').toLowerCase();
  const t = FTYPES.find(([re]) => re.test(ext));
  return '<span class="tag ftag" title="' + esc(t ? t[2] : 'Datei') + '">' + ico(t ? t[1] : 'notes') + '<small>' + esc((ext || 'datei').slice(0, 5)) + '</small></span>';
}

/* ---------- Dateien ---------- */
async function files() {
  const q = new URLSearchParams(location.hash.split('?')[1] || ''); const path = q.get('p') || '';
  view.innerHTML = head('Dateien', 'Deine Ablage auf dem Server') + '<div class="crumbs" id="cr"></div><div class="list" id="fl"><div class="skeleton"></div></div>';
  const parts = path ? path.split('/') : [];
  $('#cr').innerHTML = `<button data-p="">Start</button>` + parts.map((p, i) => ` / <button data-p="${esc(parts.slice(0, i + 1).join('/'))}">${esc(p)}</button>`).join('');
  $('#cr').onclick = e => { const b = e.target.closest('button'); if (b) location.hash = '#/files' + (b.dataset.p ? '?p=' + encodeURIComponent(b.dataset.p) : ''); };
  try {
    const d = await api('/api/files?path=' + encodeURIComponent(path));
    $('#fl').innerHTML = d.entries.length ? d.entries.map(f => `<div class="row" data-n="${esc(f.name)}" data-d="${f.directory ? 1 : 0}">${ftag(f)}<div class="grow"><b>${esc(f.name)}</b><span>${f.directory ? 'Ordner' : fmtBytes(f.size)}</span></div>${f.directory ? '' : `<a class="btn small ghost" href="/api/file?path=${encodeURIComponent((path ? path + '/' : '') + f.name)}">${ico('down')} Laden</a>`}</div>`).join('') : '<div class="empty">Dieser Ordner ist leer.</div>';
    $('#fl').onclick = e => { const r = e.target.closest('.row'); if (!r || e.target.closest('a')) return; const full = (path ? path + '/' : '') + r.dataset.n; if (r.dataset.d === '1') location.hash = '#/files?p=' + encodeURIComponent(full); else openViewer(full, r.dataset.n); };
  } catch (er) { $('#fl').innerHTML = `<div class="empty">${esc(er.message)}</div>`; }
}

/* ---------- System ---------- */
async function system() {
  view.innerHTML = head('System', 'Zustand des Servers') + '<div class="skeleton"></div>';
  let st; try { st = await api('/api/status'); } catch (er) { view.innerHTML = head('System') + `<div class="empty">${esc(er.message)}</div>`; return; }
  const bk = st.backup_status;
  const cont = (st.containers || []).map(c => `<div class="row"><span class="tag ${c.state === 'running' ? 'ok' : 'bad'}">${esc(c.state)}</span><div class="grow"><b>${esc(c.name)}</b>${c.oom ? '<span>Speicher knapp (OOM)</span>' : ''}</div>${me.admin && ['filebrowser', 'ntfy', 'couchdb'].includes(c.name) ? `<button class="btn small ghost" data-s="${esc(c.name)}">Neu starten</button>` : ''}</div>`).join('');
  view.innerHTML = head('System', 'Zustand des Servers') + `<div class="grid">
    <div class="card"><h2>Laufzeit</h2><div class="stat">${fmtUp(st.uptime)}</div></div>
    <div class="card"><h2>Drucker</h2><span class="tag ${st.printer ? 'ok' : 'warn'}">${st.printer ? 'bereit' : 'nicht bereit'}</span> <span class="tag ${st.scanner ? 'ok' : 'warn'}">Scanner ${st.scanner ? 'ja' : 'nein'}</span></div>
    <div class="card"><h2>Backup</h2>${bk ? `<span class="tag ${/^OK/.test(bk.state) ? 'ok' : 'warn'}">${esc(bk.state)}</span><div class="sub">${bk.time ? new Date(bk.time).toLocaleString('de-DE') : ''}</div>` : '<span class="tag warn">nicht eingerichtet</span>'}</div></div>
  ${cont ? `<div class="card mt"><h2>Dienste</h2><div class="list">${cont}</div></div>` : ''}
  <p class="sub"><a href="/api/export">Meine Daten exportieren (JSON)</a></p>`;
  view.onclick = async e => { const b = e.target.closest('[data-s]'); if (!b) return; b.disabled = true; try { await api('/api/service', { body: { service: b.dataset.s, verb: 'restart' } }); toast(b.dataset.s + ' startet neu'); } catch (er) { toast(er.message, 1); } b.disabled = false; };
}

/* ---------- Claude (Chat mit Claude Code auf dem Server) ---------- */
function mdLite(src) {
  const blocks = [];
  let t = esc(src).replace(/```(?:\w+)?\n([\s\S]*?)```/g, (_m, c) => { blocks.push('<pre><code>' + c + '</code></pre>'); return '\u0000' + (blocks.length - 1) + '\u0000'; });
  t = t.replace(/`([^`\n]+)`/g, '<code>$1</code>').replace(/\*\*([^*\n]+)\*\*/g, '<b>$1</b>');
  t = t.split(/\n{2,}/).map(p => /^\s*[-*] /m.test(p) ? '<ul>' + p.split('\n').map(l => l.replace(/^\s*[-*] (.*)$/, '<li>$1</li>')).join('') + '</ul>' : '<p>' + p.replace(/\n/g, '<br>') + '</p>').join('');
  return t.replace(/\u0000(\d+)\u0000/g, (_m, i) => blocks[+i]);
}
let claudeState = { msgs: [], sid: null, busy: false };
function claudeLoad() {
  try { const d = JSON.parse(localStorage.getItem('ma-claude') || 'null'); if (d) claudeState = { msgs: d.msgs || [], sid: d.sid || null, busy: false }; } catch (e) { /* kein Speicher */ }
}
function claudeSave() {
  try { localStorage.setItem('ma-claude', JSON.stringify({ msgs: claudeState.msgs.slice(-80), sid: claudeState.sid })); } catch (e) { /* ignorieren */ }
}
function claudeRender() {
  const box = $('#cmsgs'); if (!box) return;
  const S = claudeState;
  box.innerHTML = S.msgs.length ? S.msgs.map(m => {
    if (m.r === 'u') return '<div class="cm u">' + esc(m.t) + '</div>';
    if (m.r === 't') return '<div class="ctool">' + esc(m.t) + '</div>';
    if (m.r === 'e') return '<div class="cerr">' + esc(m.t) + '</div>';
    return '<div class="cm' + (m.live ? ' typing' : '') + '">' + mdLite(m.t || '…') + '</div>';
  }).join('') : '<div class="empty">Frag Claude auf deinem Server.<br>Zum Beispiel: „Wie voll ist die Backup-Platte?“ oder „Was ist neu in meinen Notizen?“<br>Mit „Nur lesen“ kann nichts verändert werden.</div>';
  box.scrollTop = box.scrollHeight;
}
let pendingImgs = [];
const IMG_BUDGET = 100000; // Zeichen gesamt; das Portal nimmt höchstens 128 KB je Anfrage
function imgChips() {
  const c = $('#cimgs'); if (!c) return;
  c.innerHTML = pendingImgs.map((_, i) => '<span class="chip">📎 Bild ' + (i + 1) + ' <b data-i="' + i + '" title="Entfernen">×</b></span>').join('');
  c.querySelectorAll('b').forEach(b => { b.onclick = () => { pendingImgs.splice(+b.dataset.i, 1); imgChips(); }; });
}
function imgFit(file, budget) {
  return new Promise((resolve, reject) => {
    const im = new Image(), url = URL.createObjectURL(file);
    im.onload = () => {
      URL.revokeObjectURL(url);
      for (const dim of [1280, 1024, 800, 640, 480]) for (const q of [0.7, 0.55, 0.4]) {
        const k = Math.min(1, dim / Math.max(im.width, im.height)), cv = document.createElement('canvas');
        cv.width = Math.round(im.width * k); cv.height = Math.round(im.height * k);
        cv.getContext('2d').drawImage(im, 0, 0, cv.width, cv.height);
        const u = cv.toDataURL('image/jpeg', q);
        if (u.length <= budget) return resolve(u);
      }
      reject(new Error('Bild zu groß'));
    };
    im.onerror = () => { URL.revokeObjectURL(url); reject(new Error('Kein lesbares Bild')); };
    im.src = url;
  });
}
async function imgAdd(files) {
  const list = [...files].filter(f => f.type.startsWith('image/'));
  if (!list.length) return;
  if (pendingImgs.length + list.length > 3) { toast('Höchstens 3 Bilder', 1); return; }
  const n = pendingImgs.length + list.length;
  try {
    // bisherige Bilder bleiben, das Budget wird auf alle Bilder verteilt (neue Bilder bekommen den Rest)
    const used = pendingImgs.reduce((a, u) => a + u.length, 0), each = Math.floor((IMG_BUDGET - used) / list.length);
    if (each < 8000) { toast('Kein Platz mehr, bitte ein Bild entfernen', 1); return; }
    for (const f of list) pendingImgs.push(await imgFit(f, each));
    imgChips();
  } catch (er) { toast(er.message, 1); }
}
async function claudeSend(prompt, opts) {
  const S = claudeState;
  if (S.busy || !prompt) return;
  S.busy = true;
  const imgs = pendingImgs; pendingImgs = []; imgChips();
  S.msgs.push({ r: 'u', t: (imgs.length ? '📎 ' + imgs.length + ' Bild' + (imgs.length > 1 ? 'er' : '') + '\n' : '') + prompt }, { r: 'a', t: '', live: true });
  claudeRender();
  const asst = () => S.msgs.slice().reverse().find(m => m.r === 'a');
  try {
    const r = await fetch('/api/claude', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-MA-Request': '1' }, body: JSON.stringify({ prompt, session: S.sid, ...opts, images: imgs }) });
    if (!r.ok) {
      let m = 'Fehler ' + r.status;
      try { m = (await r.json()).error || m; } catch (e) { /* leer */ }
      throw new Error(r.status === 403 ? 'Nur für Administratoren.' : m);
    }
    const reader = r.body.getReader(), dec = new TextDecoder();
    let buf = '';
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1);
        if (!line) continue;
        let d; try { d = JSON.parse(line); } catch (e) { continue; }
        if (d.session_id) S.sid = d.session_id;
        const ev = d.event;
        if (d.type === 'stream_event' && ev && ev.type === 'content_block_delta' && ev.delta && ev.delta.type === 'text_delta') {
          const a = asst(); if (a) a.t += ev.delta.text;
        } else if (d.type === 'assistant' && d.message && Array.isArray(d.message.content)) {
          for (const b of d.message.content) {
            if (b.type !== 'tool_use') continue;
            const inp = b.input || {};
            const idx = S.msgs.findIndex(m => m.live);
            S.msgs.splice(idx < 0 ? S.msgs.length : idx, 0, { r: 't', t: b.name + ': ' + String(inp.command || inp.file_path || inp.pattern || inp.path || '').slice(0, 80) });
          }
        } else if (d.type === 'result') {
          const a = asst();
          if (d.is_error) {
            S.msgs.push({ r: 'e', t: /not logged in|\/login/i.test(String(d.result)) ? 'Claude ist auf dem Server noch nicht angemeldet. Das geht nur einmal und nur mit deinem Konto. Auf deinem PC in PowerShell eingeben: ssh -t ma-server "~/.local/bin/claude". Danach funktioniert dieser Chat dauerhaft.' : String(d.result) });
          } else if (a && !a.t && d.result) a.t = d.result;
        } else if (d.type === 'bridge_model') {
          if (!opts.model || opts.model === 'auto') S.msgs.splice(Math.max(0, S.msgs.findIndex(m => m.live)), 0, { r: 't', t: 'Modell automatisch gewählt: ' + d.model });
        } else if (d.type === 'bridge_error') {
          S.msgs.push({ r: 'e', t: d.error });
        }
        claudeRender();
      }
    }
  } catch (er) { S.msgs.push({ r: 'e', t: er.message }); }
  S.msgs.forEach(m => { delete m.live; });
  S.msgs = S.msgs.filter(m => !(m.r === 'a' && !m.t));
  S.busy = false; claudeSave(); claudeRender();
  const b = $('#csend'); if (b) b.disabled = false;
}
const COUNCIL = (idee) => 'AI-Council: Prüfe diese Idee aus fünf Rollen und bewerte jede Rolle mit zwei bis vier Sätzen.\n' +
  '1. Skeptiker: Was kann schiefgehen, welche Annahmen sind ungeprüft?\n2. Grundlagen: Was ist belegt, was fehlt an Fakten (nutze meine Notizen im Vault, wenn passend)?\n' +
  '3. Chancen: Wo steckt der größte Hebel?\n4. Außenblick: Wie sieht es für jemanden aus, der nichts über mich weiß (Leser, Kunde, Ausbilder)?\n5. Umsetzer: Konkrete nächste drei Schritte mit Aufwand.\n' +
  'Danach eine zweite Prüfrunde: Wo widersprechen sich die Rollen? Schließe mit einer klaren Empfehlung (machen, ändern, lassen) und einer offenen Frage an mich.\n\nIdee:\n' + idee;

// Automatischer Council: nur bei klaren Formulierungen (Treffer kosten einen langen Durchlauf). Mit "ohne council" in der Nachricht abschaltbar.
const COUNCIL_AUTO = /^(?![\s\S]*ohne council)[\s\S]*(\bcouncil\b|prüf(e)? (meine|diese|die) (idee|entscheidung|plan)|ist das eine gute idee|lohnt (es )?sich das)/i;

async function claude() {
  claudeLoad();
  view.innerHTML = head('Claude', 'Dein Assistent auf dem Server', '<button class="btn ghost small" id="cnew">Neuer Chat</button>') +
    '<div class="cwrap"><div class="cmsgs" id="cmsgs"></div><form class="cform" id="cf">' +
    '<div id="cimgs" class="cimgs"></div><div class="copts"><label>Ordner<select name="dir"><option value="notizen">Notizen</option><option value="bibliothek">Bibliothek</option><option value="maserver">MA-Server (Projekt)</option><option value="server">Server-Home</option></select></label>' +
    '<label>Rechte<select name="mode"><option value="lesen">Nur lesen</option><option value="notizen">Notizen bearbeiten</option><option value="voll">Voll (wie am PC)</option><option value="voll_senden">Voll + Senden/Löschen (nur diese Nachricht)</option></select></label>' +
    '<label>Modell<select name="model"><option value="auto">Auto</option><option value="sonnet">Sonnet</option><option value="haiku">Haiku (sparsam)</option><option value="opus">Opus</option></select></label></div>' +
    '<div class="cin"><textarea name="prompt" rows="2" placeholder="Frag Claude … (Bild per Strg+V einfügen)"></textarea><input type="file" id="cfile" accept="image/*" multiple hidden><button class="btn ghost" type="button" id="cattach" title="Bild anhängen">📎</button><button class="btn ghost" type="button" id="ccouncil" title="Prüft deine Idee aus fünf Rollen mit zweiter Runde">Council</button><button class="btn" id="csend">' + ico('send') + ' Senden</button></div></form></div>';
  claudeRender();
  $('#cnew').onclick = () => { if (claudeState.busy) return; claudeState = { msgs: [], sid: null, busy: false }; claudeSave(); claudeRender(); };
  $('#cf').onsubmit = e => {
    e.preventDefault();
    const f = new FormData(e.target); const p = String(f.get('prompt')).trim();
    if ((!p && !pendingImgs.length) || claudeState.busy) return;
    $('#csend').disabled = true; e.target.prompt.value = '';
    const auto = COUNCIL_AUTO.test(p) && !p.startsWith('AI-Council:');
    if (auto) toast('Council automatisch gestartet');
    claudeSend(auto ? COUNCIL(p) : p, { dir: f.get('dir'), mode: f.get('mode') === 'voll_senden' && auto ? 'voll' : f.get('mode'), model: f.get('model') });
    if (f.get('mode') === 'voll_senden') e.target.mode.value = 'voll';
  };
  try { const q = sessionStorage.getItem('ma-claude-q'); if (q) { sessionStorage.removeItem('ma-claude-q'); $('#cf').prompt.value = q; setTimeout(() => $('#cf').requestSubmit(), 150); } } catch (er) { /* ohne Speicher */ }
  $('#ccouncil').onclick = () => { const f = new FormData($('#cf')); const p = String(f.get('prompt')).trim(); if (!p || claudeState.busy) { toast('Erst die Idee ins Feld schreiben', 1); return; } $('#cf').prompt.value = ''; claudeSend(COUNCIL(p), { dir: f.get('dir'), mode: f.get('mode') === 'voll_senden' ? 'voll' : f.get('mode'), model: f.get('model') }); };
  $('#cattach').onclick = () => $('#cfile').click();
  $('#cfile').onchange = e => { imgAdd(e.target.files); e.target.value = ''; };
  $('#cf').prompt.addEventListener('paste', e => { const fs = [...(e.clipboardData || {}).files || []]; if (fs.some(f => f.type.startsWith('image/'))) { e.preventDefault(); imgAdd(fs); } });
  $('#cf').prompt.addEventListener('keydown', e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); $('#cf').requestSubmit(); } });
}

/* ---------- Dateivorschau ---------- */
const TEXT_EXT = ['txt', 'log', 'json', 'yml', 'yaml', 'py', 'js', 'ts', 'sh', 'bash', 'csv', 'conf', 'ini', 'xml', 'html', 'css', 'sql', 'toml', 'md', 'markdown', 'canvas', 'base', 'ps1', 'bat', 'java', 'c', 'h', 'cpp', 'go', 'rs', 'service', 'timer', 'env.example'];
const IMG_EXT = { png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', gif: 'image/gif', webp: 'image/webp', svg: 'image/svg+xml', bmp: 'image/bmp' };
function mdDoc(src) {
  let fm = '';
  src = src.replace(/^---\n([\s\S]*?)\n---\n?/, (_m, y) => { fm = '<pre class="fm">' + esc(y) + '</pre>'; return ''; });
  const blocks = [];
  let t = esc(src).replace(/```[^\n]*\n([\s\S]*?)```/g, (_m, c) => { blocks.push('<pre><code>' + c + '</code></pre>'); return '\u0000' + (blocks.length - 1) + '\u0000'; });
  t = t.replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g, '<span class="wl" data-t="$1">$2</span>').replace(/\[\[([^\]]+)\]\]/g, '<span class="wl" data-t="$1">$1</span>');
  t = t.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  t = t.replace(/`([^`\n]+)`/g, '<code>$1</code>').replace(/\*\*([^*\n]+)\*\*/g, '<b>$1</b>').replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<i>$2</i>');
  const out = [];
  let list = null;
  const flush = () => { if (list) { out.push('<' + list.t + '>' + list.items.join('') + '</' + list.t + '>'); list = null; } };
  for (const line of t.split('\n')) {
    let m;
    if ((m = line.match(/^(#{1,6})\s+(.*)$/))) { flush(); out.push('<h' + m[1].length + '>' + m[2] + '</h' + m[1].length + '>'); }
    else if (/^\s*(-{3,}|\*{3,})\s*$/.test(line)) { flush(); out.push('<hr>'); }
    else if ((m = line.match(/^\s*[-*]\s+(?:\[( |x)\]\s+)?(.*)$/))) { if (!list || list.t !== 'ul') { flush(); list = { t: 'ul', items: [] }; } list.items.push('<li>' + (m[1] ? (m[1] === 'x' ? '☑ ' : '☐ ') : '') + m[2] + '</li>'); }
    else if ((m = line.match(/^\s*\d+\.\s+(.*)$/))) { if (!list || list.t !== 'ol') { flush(); list = { t: 'ol', items: [] }; } list.items.push('<li>' + m[1] + '</li>'); }
    else if ((m = line.match(/^&gt;\s?(.*)$/))) { flush(); out.push('<blockquote>' + m[1] + '</blockquote>'); }
    else if (!line.trim()) { flush(); }
    else { flush(); out.push('<p>' + line + '</p>'); }
  }
  flush();
  return fm + out.join('').replace(/\u0000(\d+)\u0000/g, (_m, i) => blocks[+i]);
}

const SERVER_DOC = ['pdf', 'doc', 'docx', 'odt', 'ppt', 'pptx', 'odp', 'xls', 'xlsx', 'ods', 'txt', 'rtf', 'png', 'jpg', 'jpeg', 'tif', 'tiff'];
const OFFICE_EXT = ['doc', 'docx', 'odt', 'ppt', 'pptx', 'odp', 'xls', 'xlsx', 'ods', 'rtf', 'tif', 'tiff'];
const MEDIA_EXT = { mp3: 'audio/mpeg', wav: 'audio/wav', ogg: 'audio/ogg', m4a: 'audio/mp4', flac: 'audio/flac', mp4: 'video/mp4', webm: 'video/webm', mov: 'video/quicktime', mkv: 'video/x-matroska' };
async function serverJob(kind, path, onState) {
  const key = crypto.randomUUID();
  await api('/api/jobs', { body: { kind, path, key } });
  for (let i = 0; i < 300; i++) {
    await new Promise(r => setTimeout(r, 1000));
    const st = await api('/api/jobs/' + key);
    if (onState) onState(st);
    if (st.state === 'done') return { id: key, ...st };
    if (st.state === 'error') throw new Error(st.message || 'Auftrag fehlgeschlagen');
  }
  throw new Error('Zeitüberschreitung beim Server-Auftrag');
}
async function serverPreview(path, body) {
  body.innerHTML = '<div class="empty">Der Server wandelt die Datei um …</div>';
  const r = await serverJob('preview', path, st => { if (st.state === 'running') body.innerHTML = '<div class="empty">Der Server wandelt die Datei um … (läuft)</div>'; });
  body.innerHTML = '<div class="pages">' + Array.from({ length: r.pages }, (_, i) => '<img loading="lazy" alt="Seite ' + (i + 1) + '" src="/api/jobs/' + r.id + '/page?n=' + (i + 1) + '">').join('') + '</div>' +
    (r.total_pages > r.pages ? '<div class="sub">Vorschau zeigt ' + r.pages + ' von ' + r.total_pages + ' Seiten. Drucken druckt alle.</div>' : '');
}
async function serverPrint(path, btn) {
  btn.disabled = true; toast('Druckauftrag wird vorbereitet …');
  try { const r = await serverJob('print', path); toast(r.message ? 'Gedruckt: ' + r.message : 'An den Drucker gesendet'); }
  catch (er) { toast(er.message, 1); }
  btn.disabled = false;
}

function closeViewer() { const v = $('#viewer'); if (v) { if (v.dataset.url) URL.revokeObjectURL(v.dataset.url); v.remove(); } }
async function openViewer(path, name) {
  closeViewer();
  const ext = (name.split('.').pop() || '').toLowerCase();
  const dl = '/api/file?path=' + encodeURIComponent(path);
  const v = document.createElement('div');
  v.id = 'viewer'; v.className = 'viewer';
  v.innerHTML = '<div class="vhead"><b>' + esc(name) + '</b><span class="vsp"></span>' + (SERVER_DOC.includes(ext) ? '<button class="btn small ghost" id="vprint">Drucken (Samsung)</button>' : '') + '<button class="btn small ghost" id="vbprint">Druckansicht</button><a class="btn small ghost" href="' + dl + '">' + ico('down') + ' Laden</a><button class="btn small ghost" id="vclose">Schließen</button></div><div class="vbody" id="vbody"><div class="skeleton"></div></div>';
  document.body.appendChild(v);
  $('#vclose').onclick = closeViewer;
  if ($('#vprint')) $('#vprint').onclick = e => serverPrint(path, e.currentTarget);
  $('#vbprint').onclick = () => window.print();
  if (OFFICE_EXT.includes(ext)) { try { await serverPreview(path, $('#vbody')); } catch (er) { $('#vbody').innerHTML = '<div class="empty">' + esc(er.message) + '</div>'; } return; }
  const body = $('#vbody');
  try {
    const r = await fetch(dl, { credentials: 'same-origin' });
    if (!r.ok) throw new Error('Datei nicht lesbar (' + r.status + ')');
    const blob = await r.blob();
    if (IMG_EXT[ext]) {
      const url = URL.createObjectURL(new Blob([blob], { type: IMG_EXT[ext] })); v.dataset.url = url;
      body.innerHTML = '<img class="vimg" alt="' + esc(name) + '" src="' + url + '">';
    } else if (ext === 'pdf') {
      const url = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' })); v.dataset.url = url;
      body.innerHTML = '<iframe class="vpdf" src="' + url + '" title="' + esc(name) + '"></iframe><div class="sub">Wird die PDF nicht angezeigt, nutze „Laden“.</div>';
    } else if (TEXT_EXT.includes(ext) || (!ext && blob.size < 200000)) {
      if (blob.size > 3 * 1024 * 1024) throw new Error('Datei ist zu groß für die Vorschau (' + fmtBytes(blob.size) + '). Bitte laden.');
      const text = await blob.text();
      body.innerHTML = (ext === 'md' || ext === 'markdown') ? '<article class="md">' + mdDoc(text) + '</article>' : '<pre class="vtext">' + esc(text) + '</pre>';
    } else if (MEDIA_EXT[ext]) {
      const url = URL.createObjectURL(new Blob([blob], { type: MEDIA_EXT[ext] })); v.dataset.url = url;
      body.innerHTML = MEDIA_EXT[ext].startsWith('audio') ? '<audio class="vmedia" controls src="' + url + '"></audio>' : '<video class="vmedia" controls playsinline src="' + url + '"></video>';
    } else {
      const head = new Uint8Array(await blob.slice(0, 4096).arrayBuffer());
      const binary = head.some(b => b === 0);
      if (!binary && blob.size < 3 * 1024 * 1024) body.innerHTML = '<pre class="vtext">' + esc(await blob.text()) + '</pre>';
      else body.innerHTML = '<div class="empty">Diese Datei ist ein Binärformat (.' + esc(ext) + ', ' + fmtBytes(blob.size) + ') ohne Vorschau.<br>Nutze „Laden“.</div>';
    }
  } catch (er) { body.innerHTML = '<div class="empty">' + esc(er.message) + '</div>'; }
}
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeViewer(); });

/* ---------- Wissen (Graph wie in Obsidian) ---------- */
let graphCache = null;
async function loadGraph(force) {
  if (graphCache && !force) return graphCache;
  const r = await fetch('/api/file?path=' + encodeURIComponent('Bibliothek/vault-graph.json'), { credentials: 'same-origin' });
  if (!r.ok) throw new Error('Graph nicht verfügbar (' + r.status + '). Ist die Bibliothek im Portal eingebunden?');
  graphCache = await r.json();
  graphCache.byName = {};
  graphCache.nodes.forEach((n, i) => { const k = n.n.toLowerCase(); if (!(k in graphCache.byName)) graphCache.byName[k] = i; graphCache.byName[n.p.slice(0, -3).toLowerCase()] = i; });
  return graphCache;
}
function openNote(i) { const g = graphCache, n = g.nodes[i]; openViewer(g.basis + '/' + n.p, n.n + '.md'); }
document.addEventListener('click', async e => {
  const w = e.target.closest('.wl'); if (!w) return;
  try { const g = await loadGraph(); const k = (w.dataset.t || w.textContent).toLowerCase().replace(/\.md$/, ''); const i = g.byName[k] ?? g.byName[k.split('/').pop()]; if (i !== undefined) openNote(i); else toast('Notiz „' + w.textContent + '“ nicht gefunden', 1); } catch (er) { toast(er.message, 1); }
});
const GCOL = ['#e5173f', '#3d8bfd', '#2fbf71', '#f59e0b', '#a78bfa', '#22c1c3', '#c9ced9', '#ff7ab6', '#84cc16', '#fb923c'];
async function wissen() {
  view.innerHTML = head('Wissen', 'Deine Notizen und ihre Verbindungen', '<div class="gtools"><input id="gq" placeholder="Notiz suchen …"><button class="btn small ghost" id="greset">Ansicht zurücksetzen</button></div>') +
    '<div class="gwrap"><canvas id="gc"></canvas><div class="gtip" id="gtip" hidden></div><div class="glegend" id="glegend"></div><div class="ginfo" id="ginfo"></div></div>';
  let g;
  try { g = await loadGraph(true); } catch (er) { $('.gwrap').innerHTML = '<div class="empty">' + esc(er.message) + '</div>'; return; }
  const cv = $('#gc'), ctx = cv.getContext('2d'), wrap = $('.gwrap');
  const groups = [...new Set(g.nodes.map(n => n.g))].sort();
  const col = Object.fromEntries(groups.map((x, i) => [x, GCOL[i % GCOL.length]]));
  $('#glegend').innerHTML = groups.map(x => '<span><i data-c="' + col[x] + '"></i>' + esc(x) + '</span>').join('');
  document.querySelectorAll('#glegend i').forEach(i => { i.style.background = i.dataset.c; });
  $('#ginfo').textContent = g.nodes.length + ' Notizen · ' + g.links.length + ' Verbindungen · Stand ' + g.stand;
  const N = g.nodes.length, adj = Array.from({ length: N }, () => []);
  g.links.forEach(([a, b]) => { adj[a].push(b); adj[b].push(a); });
  const P = g.nodes.map((n, i) => { const a = i * 2.399963, r = 14 * Math.sqrt(i + 1); return { x: Math.cos(a) * r, y: Math.sin(a) * r, vx: 0, vy: 0, r: 2.6 + Math.sqrt(n.d) * 1.25 }; });
  let W = 0, H = 0, dpr = window.devicePixelRatio || 1, cam = { x: 0, y: 0, k: 0.9 }, alpha = 1, hover = -1, drag = null, query = '';
  const resize = () => { W = wrap.clientWidth; H = wrap.clientHeight; cv.width = W * dpr; cv.height = H * dpr; cv.style.width = W + 'px'; cv.style.height = H + 'px'; };
  resize(); new ResizeObserver(resize).observe(wrap);
  const toWorld = (sx, sy) => ({ x: (sx - W / 2) / cam.k + cam.x, y: (sy - H / 2) / cam.k + cam.y });
  function step() {
    if (alpha < 0.005) return;
    for (let i = 0; i < N; i++) { const p = P[i]; for (let j = i + 1; j < N; j++) { const q = P[j]; let dx = p.x - q.x, dy = p.y - q.y, d2 = dx * dx + dy * dy + 0.01; if (d2 > 90000) continue; const f = 900 / d2 * alpha; dx *= f; dy *= f; p.vx += dx; p.vy += dy; q.vx -= dx; q.vy -= dy; } }
    g.links.forEach(([a, b]) => { const p = P[a], q = P[b]; const dx = q.x - p.x, dy = q.y - p.y, d = Math.sqrt(dx * dx + dy * dy) || 1, f = (d - 46) * 0.02 * alpha; p.vx += dx / d * f; p.vy += dy / d * f; q.vx -= dx / d * f; q.vy -= dy / d * f; });
    for (let i = 0; i < N; i++) { const p = P[i]; if (drag && drag.i === i) continue; p.vx -= p.x * 0.004 * alpha; p.vy -= p.y * 0.004 * alpha; p.x += p.vx; p.y += p.vy; p.vx *= 0.6; p.vy *= 0.6; }
    alpha *= 0.985;
  }
  function draw() {
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
    ctx.translate(W / 2, H / 2); ctx.scale(cam.k, cam.k); ctx.translate(-cam.x, -cam.y);
    const hl = hover >= 0 ? new Set([hover, ...adj[hover]]) : null;
    const match = query ? new Set(g.nodes.map((n, i) => n.n.toLowerCase().includes(query) ? i : -1).filter(i => i >= 0)) : null;
    ctx.lineWidth = 0.7 / cam.k;
    g.links.forEach(([a, b]) => { const on = hl && (a === hover || b === hover); ctx.strokeStyle = on ? 'rgba(255,59,92,.85)' : hl || match ? 'rgba(190,200,225,.05)' : 'rgba(190,200,225,.16)'; ctx.beginPath(); ctx.moveTo(P[a].x, P[a].y); ctx.lineTo(P[b].x, P[b].y); ctx.stroke(); });
    g.nodes.forEach((n, i) => {
      const p = P[i], dim = (hl && !hl.has(i)) || (match && !match.has(i));
      ctx.globalAlpha = dim ? 0.18 : 1; ctx.fillStyle = col[n.g]; ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, 7); ctx.fill();
      if (i === hover || (match && match.has(i))) { ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.4 / cam.k; ctx.stroke(); }
      const showLabel = !dim && (cam.k > 1.6 || n.d > 14 || i === hover || (hl && hl.has(i)) || (match && match.has(i)));
      if (showLabel) { ctx.fillStyle = '#e7eaf2'; ctx.font = (11 / cam.k) + 'px system-ui, sans-serif'; ctx.fillText(n.n, p.x + p.r + 3 / cam.k, p.y + 4 / cam.k); }
    });
    ctx.globalAlpha = 1;
  }
  function loop() { if (!document.body.contains(cv)) return; step(); draw(); requestAnimationFrame(loop); }
  loop();
  const pick = (sx, sy) => { const w = toWorld(sx, sy); let best = -1, bd = 1e9; P.forEach((p, i) => { const d = (p.x - w.x) ** 2 + (p.y - w.y) ** 2; if (d < bd && d < (p.r + 6 / cam.k) ** 2) { bd = d; best = i; } }); return best; };
  const pos = e => { const r = cv.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
  let moved = false;
  cv.addEventListener('pointerdown', e => { cv.setPointerCapture(e.pointerId); const m = pos(e), i = pick(m.x, m.y); moved = false; drag = i >= 0 ? { i } : { pan: true, sx: m.x, sy: m.y, cx: cam.x, cy: cam.y }; });
  cv.addEventListener('pointermove', e => {
    const m = pos(e);
    if (drag && drag.i !== undefined) { const w = toWorld(m.x, m.y); P[drag.i].x = w.x; P[drag.i].y = w.y; alpha = Math.max(alpha, 0.3); moved = true; return; }
    if (drag && drag.pan) { cam.x = drag.cx - (m.x - drag.sx) / cam.k; cam.y = drag.cy - (m.y - drag.sy) / cam.k; moved = true; return; }
    hover = pick(m.x, m.y); const tip = $('#gtip');
    if (hover >= 0) { const n = g.nodes[hover]; tip.hidden = false; tip.textContent = n.n + ' · ' + n.d + ' Verbindungen · ' + n.g; tip.style.left = (m.x + 14) + 'px'; tip.style.top = (m.y + 10) + 'px'; } else tip.hidden = true;
    cv.style.cursor = hover >= 0 ? 'pointer' : 'grab';
  });
  cv.addEventListener('pointerup', e => { const m = pos(e); if (drag && drag.i !== undefined && !moved) openNote(drag.i); drag = null; });
  cv.addEventListener('wheel', e => { e.preventDefault(); const m = pos(e), before = toWorld(m.x, m.y); cam.k = Math.min(6, Math.max(0.15, cam.k * (e.deltaY < 0 ? 1.15 : 0.87))); const after = toWorld(m.x, m.y); cam.x += before.x - after.x; cam.y += before.y - after.y; }, { passive: false });
  $('#gq').addEventListener('input', e => { query = e.target.value.trim().toLowerCase(); if (query) { const i = g.nodes.findIndex(n => n.n.toLowerCase().includes(query)); if (i >= 0) { cam.x = P[i].x; cam.y = P[i].y; cam.k = Math.max(cam.k, 1.6); } } });
  $('#gq').addEventListener('keydown', e => { if (e.key === 'Enter') { const i = g.nodes.findIndex(n => n.n.toLowerCase().includes(query)); if (i >= 0) openNote(i); } });
  $('#greset').onclick = () => { cam = { x: 0, y: 0, k: 0.9 }; query = ''; $('#gq').value = ''; alpha = 0.6; };
}

const ROUTES = { home, tasks, notes, money, training, claude, wissen, files, system };
async function route() {
  const id = (location.hash.slice(2).split('?')[0]) || 'home';
  const fn = ROUTES[id] || home;
  document.querySelectorAll('#nav button').forEach(b => b.removeAttribute('aria-current'));
  const cur = document.querySelector(`#nav button[data-t="${ROUTES[id] ? id : 'home'}"]`); if (cur) cur.setAttribute('aria-current', 'page');
  view.onclick = null;
  try { await fn(); } catch (er) { view.innerHTML = `<div class="empty">${esc(er.message)}</div>`; }
  window.scrollTo(0, 0);
}

(async () => {
  $('#logo').innerHTML = ico('logo');
  buildNav();
  try { me = await api('/api/me'); } catch (er) { view.innerHTML = `<div class="empty">Nicht angemeldet oder Server nicht erreichbar.<br>${esc(er.message)}</div>`; return; }
  $('#whoName').textContent = me.user; $('#whoRole').textContent = me.admin ? 'Administrator' : 'Benutzer'; $('#avatar').textContent = me.user.slice(0, 1).toUpperCase();
  window.addEventListener('hashchange', route);
  route();
})();
})();
