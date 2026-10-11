'use strict';
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
let chats = [], cur = null, running = null, cfg = null, lastSend = null;
const uid = () => crypto.randomUUID();

/* Council: derselbe automatische Start wie im Portal (Ideen und Entscheidungen). "ohne council" schaltet ab. */
const COUNCIL = idee => 'AI-Council: Prüfe diese Idee aus fünf Rollen und bewerte jede Rolle mit zwei bis vier Sätzen.\n' +
  '1. Skeptiker: Was kann schiefgehen, welche Annahmen sind ungeprüft?\n2. Grundlagen: Was ist belegt, was fehlt an Fakten (nutze meine Notizen, wenn passend)?\n' +
  '3. Chancen: Wo steckt der größte Hebel?\n4. Außenblick: Wie sieht es für jemanden aus, der nichts über mich weiß?\n5. Umsetzer: Konkrete nächste drei Schritte mit Aufwand.\n' +
  'Danach eine zweite Prüfrunde: Wo widersprechen sich die Rollen? Schließe mit einer klaren Empfehlung (machen, ändern, lassen) und einer offenen Frage an mich.\n\nIdee:\n' + idee;
const COUNCIL_AUTO = /^(?![\s\S]*(ohne|kein) council)(?=[\s\S]{25,})[\s\S]*(\bcouncil\b|prüf(e|en)? (meine|diese|die|den|das|mal)|gute idee|lohnt (es )?sich|\bsoll(te)? ich\b|was hältst du (von|davon)|vor- ?und nachteile|\b(entscheidung|projektidee|geschäftsidee)\b|\b(umbau|neuaufbau|migration)\b[\s\S]*\?|\bwelche(r|s)? (variante|option|lösung) )/i;

const SUGGEST = [
  'Wie voll ist die Backup-Platte und lief das letzte Backup durch?',
  'Fasse meine Fristen für diese Woche zusammen.',
  'Was ist heute auf dem Server passiert? Gab es Probleme?',
  'Welche neuen Dateien liegen in der Bibliothek?'
];

/* kleines, sicheres Markdown: erst escapen, dann Code, Überschriften, fett/kursiv, Listen, Absätze */
function md(src) {
  const blocks = [];
  let t = esc(src).replace(/```(?:\w+)?\n([\s\S]*?)```/g, (_m, c) => { blocks.push('<div class="code"><button class="cp" data-cp type="button">Kopieren</button><pre><code>' + c + '</code></pre></div>'); return '\u0000' + (blocks.length - 1) + '\u0000'; });
  t = t.replace(/`([^`\n]+)`/g, '<code>$1</code>').replace(/\*\*([^*\n]+)\*\*/g, '<b>$1</b>').replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<i>$2</i>');
  t = t.split(/\n{2,}/).map(p => {
    const h = p.match(/^(#{1,3}) (.+)$/); if (h && !p.includes('\n')) return '<h' + (h[1].length + 2) + '>' + h[2] + '</h' + (h[1].length + 2) + '>';
    if (/^\s*[-*] /m.test(p) && p.split('\n').every(l => /^\s*[-*] /.test(l) || !l.trim())) return '<ul>' + p.split('\n').filter(l => l.trim()).map(l => l.replace(/^\s*[-*] (.*)$/, '<li>$1</li>')).join('') + '</ul>';
    if (/^\s*\d+[.)] /m.test(p) && p.split('\n').every(l => /^\s*\d+[.)] /.test(l) || !l.trim())) return '<ol>' + p.split('\n').filter(l => l.trim()).map(l => l.replace(/^\s*\d+[.)] (.*)$/, '<li>$1</li>')).join('') + '</ol>';
    if (/^\u0000\d+\u0000$/.test(p.trim())) return p.trim();
    return '<p>' + p.replace(/\n/g, '<br>') + '</p>';
  }).join('');
  return t.replace(/\u0000(\d+)\u0000/g, (_m, i) => blocks[+i]);
}
const save = () => window.ma.saveChats(chats.map(c => ({ ...c, msgs: c.msgs.slice(-200) })));

let toastTimer;
function toast(msg, bad) {
  const el = $('#toast'); el.textContent = msg; el.classList.toggle('bad', !!bad); el.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { el.hidden = true; }, 3200);
}
async function copy(text, what) {
  try { await navigator.clipboard.writeText(text); toast((what || 'Text') + ' kopiert'); } catch (e) { toast('Kopieren nicht möglich', true); }
}

function renderList() {
  const q = $('#search').value.trim().toLowerCase();
  const list = chats.filter(c => !q || c.title.toLowerCase().includes(q) || c.msgs.some(m => (m.t || '').toLowerCase().includes(q)));
  $('#chatlist').innerHTML = list.map(c => '<button data-id="' + c.id + '" class="' + (cur && cur.id === c.id ? 'on' : '') + '" title="' + esc(c.title) + '">' + esc(c.title) + '</button>').join('')
    || '<div class="sub pad">' + (q ? 'Nichts gefunden.' : 'Noch keine Chats.') + '</div>';
  $('#chathead').hidden = !cur || !cur.msgs.length;
  $('#ctitle').textContent = cur ? cur.title : '';
}
function nearBottom(box) { return box.scrollHeight - box.scrollTop - box.clientHeight < 140; }
function renderMsgs(force) {
  const box = $('#msgs'), stick = force || nearBottom(box);
  if (!cur || !cur.msgs.length) {
    box.innerHTML = '<div class="hint"><div class="bigmark">MA</div><b>Frag Claude auf deinem Server.</b><div class="chips">' +
      SUGGEST.map(s => '<button class="chip" data-s="' + esc(s) + '" type="button">' + esc(s) + '</button>').join('') +
      '</div><div class="sub">Ideen und Entscheidungen prüft der Council automatisch („ohne council“ schaltet das ab).</div></div>';
    $('#tobottom').hidden = true;
    return;
  }
  const lastA = cur.msgs.map((m, i) => m.r === 'a' && !m.live ? i : -1).filter(i => i >= 0).pop();
  box.innerHTML = cur.msgs.map((m, i) => {
    if (m.r === 'u') return '<div class="m u">' + esc(m.t) + (m.council ? '<span class="tag">Council</span>' : '') + '</div>';
    if (m.r === 'a') return '<div class="m' + (m.live ? ' typing' : '') + '">' + md(m.t || '…') +
      (m.live || !m.t ? '' : '<div class="acts"><button data-copy="' + i + '" type="button">Kopieren</button>' + (i === lastA && !running ? '<button data-regen type="button">Neu antworten</button>' : '') + '</div>') + '</div>';
    if (m.r === 't') return '<div class="tool">' + esc(m.t) + '</div>';
    return '<div class="err">' + esc(m.t) + (/erreichbar|Code -1|ssh|Timeout/i.test(m.t) ? '<div class="acts"><button data-regen type="button">Erneut versuchen</button></div>' : '') + '</div>';
  }).join('');
  if (stick) box.scrollTop = box.scrollHeight;
  $('#tobottom').hidden = nearBottom(box);
}
function newChat() {
  if (running) return;
  cur = { id: uid(), title: 'Neuer Chat', sid: null, msgs: [] };
  chats.unshift(cur); renderList(); renderMsgs(true); $('#prompt').focus();
}
function openChat(id) { cur = chats.find(c => c.id === id); renderList(); renderMsgs(true); $('#prompt').focus(); }
function showTab(v) {
  try { localStorage.setItem('ma-tab', v); } catch (e) { /* ohne Speicher */ }
  document.querySelectorAll('#tabs button').forEach(x => { if (x.dataset.v === v) x.setAttribute('aria-current', 'page'); else x.removeAttribute('aria-current'); });
  ['chat', 'portal', 'server'].forEach(x => { $('#v-' + x).hidden = x !== v; });
  if (v === 'server') status(true);
  if (v === 'chat') $('#prompt').focus();
}
function autogrow() { const t = $('#prompt'); t.style.height = 'auto'; t.style.height = Math.min(t.scrollHeight, 200) + 'px'; }

function send(retryText) {
  const typed = typeof retryText === 'string' ? retryText : $('#prompt').value.trim();
  if (!typed || running) return;
  if (!cur) newChat();
  const auto = COUNCIL_AUTO.test(typed) && !typed.startsWith('AI-Council:');
  if (cur.msgs.length === 0) cur.title = typed.slice(0, 42);
  cur.msgs.push({ r: 'u', t: typed, council: auto }, { r: 'a', t: '', live: true });
  $('#prompt').value = ''; autogrow();
  const prompt = auto ? COUNCIL(typed) : typed;
  if (auto) toast('Council automatisch gestartet');
  lastSend = { prompt, typed, council: auto };
  running = { id: uid(), chat: cur };
  $('#send').hidden = true; $('#stop').hidden = false;
  renderList(); renderMsgs(true);
  window.ma.send({ id: running.id, prompt, sessionId: cur.sid, dir: $('#dir').value, mode: $('#mode').value, model: $('#model').value });
}
function regenerate() {
  if (running || !cur) return;
  const lastU = cur.msgs.slice().reverse().find(m => m.r === 'u');
  if (!lastU) return;
  // letzte Antwort samt Werkzeugzeilen und Fehlern entfernen, dann dieselbe Frage erneut senden
  const i = cur.msgs.lastIndexOf(lastU);
  cur.msgs.splice(i);
  send(lastU.t);
}

window.ma.onEvent(({ id, type, data }) => {
  if (!running || running.id !== id) return;
  const c = running.chat;
  const lastAssistant = () => c.msgs.slice().reverse().find(m => m.r === 'a');
  if (type === 'json') {
    if (data.session_id) c.sid = data.session_id;
    const ev = data.event;
    if (data.type === 'stream_event' && ev && ev.type === 'content_block_delta' && ev.delta && ev.delta.type === 'text_delta') {
      const l = lastAssistant(); if (l) l.t += ev.delta.text;
    } else if (data.type === 'assistant' && data.message && Array.isArray(data.message.content)) {
      for (const b of data.message.content) {
        if (b.type !== 'tool_use') continue;
        const inp = b.input || {};
        const info = inp.command || inp.file_path || inp.pattern || inp.path || '';
        const idx = c.msgs.findIndex(m => m.live);
        c.msgs.splice(idx < 0 ? c.msgs.length : idx, 0, { r: 't', t: b.name + ': ' + String(info).slice(0, 90) });
      }
    } else if (data.type === 'result') {
      const l = lastAssistant();
      if (l && !l.t && data.result && !data.is_error) l.t = data.result;
      if (data.is_error && data.result) {
        const t = String(data.result);
        c.msgs.push({ r: 'e', t: /not logged in|\/login/i.test(t)
          ? 'Claude ist auf dem Server noch nicht angemeldet. Einmal im Terminal ausführen: ssh -t ma-server "~/.local/bin/claude" und dort anmelden (Browser-Link öffnen, Code einfügen).'
          : t });
      }
    }
  } else if (type === 'end') {
    c.msgs.forEach(m => { delete m.live; });
    c.msgs = c.msgs.filter(m => !(m.r === 'a' && !m.t));
    if (data.code !== 0) {
      const login = /login|auth|credential|sign in|not logged/i.test(data.err || '');
      c.msgs.push({ r: 'e', t: login
        ? 'Claude ist auf dem Server noch nicht angemeldet. Einmal im Terminal ausführen: ssh -t ma-server "~/.local/bin/claude" und anmelden.'
        : ('Fehler (Code ' + data.code + '). ' + (data.err || '')).trim() });
    }
    running = null; $('#send').hidden = false; $('#stop').hidden = true; save();
    if (cur === c) $('#prompt').focus();
  }
  if (cur === c) { renderMsgs(); if (type === 'end') renderList(); }
});

/* ---------- Server ---------- */
const KV = out => { const o = {}, sect = { w: [], s: [], p: '' }; let cur_ = null;
  for (const raw of out.split('\n')) {
    const l = raw.replace(/\r$/, '');
    if (l === '##W') { cur_ = 'w'; continue; } if (l === '##S') { cur_ = 's'; continue; } if (l === '##P') { cur_ = 'p'; continue; }
    if (cur_ === 'w') sect.w.push(l); else if (cur_ === 's') sect.s.push(l); else if (cur_ === 'p') sect.p += l + '\n';
    else { const i = l.indexOf('='); if (i > 0) o[l.slice(0, i)] = l.slice(i + 1).trim(); }
  }
  return { o, ...sect }; };
const bar = (pct, warn = 80, bad = 92) => '<div class="bar"><i class="' + (pct >= bad ? 'bad' : pct >= warn ? 'warn' : '') + '" style="width:' + Math.min(100, Math.max(2, pct)) + '%"></i></div>';
let srvAt = 0;
async function status(force) {
  if (!force && Date.now() - srvAt < 30000 && $('#v-server').hidden) return;
  const el = $('#srv');
  const r = await window.ma.status();
  srvAt = Date.now();
  if (!r.ok) {
    el.innerHTML = '<span class="pill dot off">Server nicht erreichbar</span>';
    $('#srvbody').innerHTML = '<div class="empty">Server nicht erreichbar. Läuft er, und bist du im Heimnetz oder per VPN verbunden?<br><button class="btn" id="srvretry">Erneut prüfen</button></div>';
    const b = $('#srvretry'); if (b) b.onclick = () => status(true);
    return;
  }
  const { o, w, s, p } = KV(r.out);
  const up = parseFloat(o.up) || 0, d = Math.floor(up / 86400), h = Math.floor(up % 86400 / 3600);
  const [used, size] = (o.disk || '0 1').split(/\s+/).map(Number), [ru, rt] = (o.mem || '0 1').split(/\s+/).map(Number), [su, st] = (o.swap || '0 1').split(/\s+/).map(Number);
  const gb = n => (n / 1e9).toFixed(1) + ' GB';
  const diskPct = Math.round(used / size * 100), ramPct = Math.round(ru / rt * 100), load = parseFloat(o.load) || 0;
  const wProbs = w.filter(l => l.startsWith('PROBLEM')), wOk = w.find(l => l.startsWith('OK')), wStand = (w[0] || '').replace('Stand ', '');
  const sProbs = s.slice(1).filter(l => l.trim()), sStand = (s[0] || '').split(' ')[0];
  const par = (p.match(/Stand ([\d\- :]+): \*\*(.+?)\*\*/) || []);
  const okpill = (ok, text) => '<span class="pill dot' + (ok ? '' : ' off') + '">' + esc(text) + '</span>';
  const backupOk = /success/i.test(o.backup || '');
  el.innerHTML = okpill(!wProbs.length, 'Server online · ' + d + ' T ' + h + ' Std');
  $('#srvbody').innerHTML = '<div class="srvtop"><h1>Server</h1><div class="sub">aktualisiert ' + new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' }) + '</div><div class="spacer"></div><button class="btn ghost" id="srvrefresh">Aktualisieren</button></div>'
    + '<div class="grid">'
    + '<div class="card"><h2>Speicher</h2><div class="stat">' + gb(size - used) + ' <small>frei</small></div>' + bar(diskPct) + '<div class="sub">' + gb(used) + ' von ' + gb(size) + ' (' + diskPct + ' %)</div></div>'
    + '<div class="card"><h2>Arbeitsspeicher</h2><div class="stat">' + ramPct + '<small> %</small></div>' + bar(ramPct, 85, 95) + '<div class="sub">' + gb(ru) + ' von ' + gb(rt) + ' · Swap ' + gb(su) + ' von ' + gb(st) + '</div></div>'
    + '<div class="card"><h2>Auslastung</h2><div class="stat">' + load.toFixed(2) + ' <small>Last (2 Kerne)</small></div>' + bar(load / 2 * 100, 70, 100) + '<div class="sub">läuft seit ' + d + ' Tagen ' + h + ' Std</div></div>'
    + '<div class="card"><h2>Backup</h2><div class="stat">' + okpill(backupOk, backupOk ? 'letzter Lauf ok' : (o.backup || 'unbekannt')) + '</div><div class="sub">Timer: ' + esc(o.timer || '?') + (o.backupAt ? ' · ' + esc(o.backupAt.replace(/^\w+ /, '').slice(0, 16)) : '') + '</div></div>'
    + '<div class="card"><h2>Wachhund</h2><div class="stat">' + okpill(!wProbs.length && !!wOk, wProbs.length ? wProbs.length + ' Problem(e)' : (wOk ? 'alles in Ordnung' : 'noch nicht aktiv')) + '</div><div class="sub">' + (wProbs.length ? esc(wProbs.map(x => x.replace('PROBLEM: ', '')).join('; ')) : (wStand ? 'Stand ' + esc(wStand) : 'wird mit automatik-einrichten.sh installiert')) + '</div></div>'
    + '<div class="card"><h2>Sicherheit (wöchentlich)</h2><div class="stat">' + okpill(s.length > 0 && !sProbs.length, s.length ? (sProbs.length ? sProbs.length + ' Hinweis(e)' : 'keine Auffälligkeiten') : 'noch kein Bericht') + '</div><div class="sub">' + (sProbs.length ? esc(sProbs.map(x => x.replace(/^- /, '')).join('; ')) : (sStand ? 'Stand ' + esc(sStand) : '')) + '</div></div>'
    + '<div class="card"><h2>Parität PC ↔ Server</h2><div class="stat">' + okpill(par[2] === 'alles gleich', par[2] || 'unbekannt') + '</div><div class="sub">' + (par[1] ? 'Stand ' + esc(par[1]) : 'kein Bericht gefunden') + '</div></div>'
    + '<div class="card"><h2>Claude auf dem Server</h2><div class="stat">' + esc((o.claude || '?').replace(' (Claude Code)', '')) + '</div><div class="sub">Claude Code</div></div>'
    + '</div>';
  const b = $('#srvrefresh'); if (b) b.onclick = () => status(true);
}

/* ---------- Start ---------- */
(async () => {
  cfg = await window.ma.config();
  $('#logo').innerHTML = '<svg viewBox="0 0 24 24"><path d="M4 18V9l8-5 8 5v9M9 18v-6h6v6"/></svg>';
  $('#ver').textContent = 'v' + (cfg.version || '');
  try { const th = localStorage.getItem('ma-theme'); if (th) document.documentElement.dataset.theme = th; } catch (e) { /* ohne Speicher */ }
  $('#dir').innerHTML = [['notizen', 'Notizen (Spiegel)'], ['bibliothek', 'Bibliothek'], ['server', 'Server-Home']].map(([v, n]) => '<option value="' + v + '">' + n + '</option>').join('');
  chats = await window.ma.loadChats(); cur = chats[0] || null; renderList(); renderMsgs(true);
  const pv = $('#portal'); pv.setAttribute('src', cfg.portal);
  pv.addEventListener('did-fail-load', e => { if (e.errorCode === -3 || !e.isMainFrame) return; $('#pmsg').textContent = 'Portal nicht erreichbar (' + (e.errorDescription || e.errorCode) + '). Läuft der Server, und bist du online?'; $('#pbanner').hidden = false; });
  pv.addEventListener('did-finish-load', () => { $('#pbanner').hidden = true; });
  $('#preload').onclick = () => { $('#pbanner').hidden = true; pv.reload(); };
  $('#newChat').onclick = newChat;
  $('#send').onclick = () => send();
  $('#stop').onclick = () => { if (running) window.ma.stop(running.id); };
  $('#search').oninput = renderList;
  $('#chatlist').onclick = e => { const b = e.target.closest('button'); if (b) openChat(b.dataset.id); };
  $('#cdel').onclick = function () {
    if (!cur || running) return;
    if (this.dataset.sure !== '1') { this.dataset.sure = '1'; this.classList.add('sure'); toast('Nochmal klicken zum Löschen', true); setTimeout(() => { this.dataset.sure = ''; this.classList.remove('sure'); }, 3000); return; }
    chats = chats.filter(c => c !== cur); cur = chats[0] || null; this.dataset.sure = ''; this.classList.remove('sure'); save(); renderList(); renderMsgs(true);
  };
  $('#ctitle').ondblclick = () => {
    if (!cur) return;
    const inp = document.createElement('input'); inp.className = 'search'; inp.value = cur.title; $('#ctitle').replaceWith(inp); inp.focus(); inp.select();
    const done = ok => { if (ok && inp.value.trim()) { cur.title = inp.value.trim().slice(0, 60); save(); } const d = document.createElement('div'); d.className = 'ctitle'; d.id = 'ctitle'; d.title = 'Doppelklick zum Umbenennen'; inp.replaceWith(d); d.ondblclick = $('#chathead').ondblclick; renderList(); };
    inp.onkeydown = e => { if (e.key === 'Enter') done(true); if (e.key === 'Escape') done(false); };
    inp.onblur = () => done(true);
  };
  $('#msgs').onclick = e => {
    const chip = e.target.closest('.chip'); if (chip) { $('#prompt').value = chip.dataset.s; autogrow(); $('#prompt').focus(); return; }
    const cp = e.target.closest('[data-cp]'); if (cp) { copy(cp.parentElement.querySelector('code').textContent, 'Code'); return; }
    const cm = e.target.closest('[data-copy]'); if (cm) { copy(cur.msgs[+cm.dataset.copy].t, 'Antwort'); return; }
    if (e.target.closest('[data-regen]')) regenerate();
  };
  $('#msgs').onscroll = () => { $('#tobottom').hidden = nearBottom($('#msgs')); };
  $('#tobottom').onclick = () => { const b = $('#msgs'); b.scrollTop = b.scrollHeight; };
  $('#theme').onclick = () => {
    const root = document.documentElement, dark = root.dataset.theme ? root.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    root.dataset.theme = dark ? 'light' : 'dark'; try { localStorage.setItem('ma-theme', root.dataset.theme); } catch (e) { /* ohne Speicher */ }
  };
  $('#prompt').addEventListener('input', autogrow);
  $('#prompt').addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); } });
  $('#tabs').onclick = e => { const b = e.target.closest('button'); if (b) showTab(b.dataset.v); };
  window.addEventListener('keydown', e => {
    const mod = e.ctrlKey || e.metaKey;
    if (e.key === 'Escape' && running) { window.ma.stop(running.id); return; }
    if (!mod) return;
    if (e.key === 'n' || e.key === 'N') { e.preventDefault(); showTab('chat'); newChat(); }
    else if (e.key === 'k' || e.key === 'K') { e.preventDefault(); showTab('chat'); $('#search').focus(); $('#search').select(); }
    else if (e.key === '1') { e.preventDefault(); showTab('portal'); } else if (e.key === '2') { e.preventDefault(); showTab('chat'); } else if (e.key === '3') { e.preventDefault(); showTab('server'); }
  });
  status(true); setInterval(() => status(false), 60000);
  let t0 = 'portal'; try { t0 = localStorage.getItem('ma-tab') || 'portal'; } catch (e) { /* ohne Speicher */ }
  showTab(['portal', 'chat', 'server'].includes(t0) ? t0 : 'portal');
})();
