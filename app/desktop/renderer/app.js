'use strict';
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
let chats = [], cur = null, running = null, cfg = null;
const uid = () => crypto.randomUUID();

/* kleines, sicheres Markdown: erst escapen, dann Code, fett, Listen, Absaetze */
function md(src) {
  const blocks = [];
  let t = esc(src).replace(/```(?:\w+)?\n([\s\S]*?)```/g, (_m, c) => { blocks.push('<pre><code>' + c + '</code></pre>'); return '\u0000' + (blocks.length - 1) + '\u0000'; });
  t = t.replace(/`([^`\n]+)`/g, '<code>$1</code>').replace(/\*\*([^*\n]+)\*\*/g, '<b>$1</b>');
  t = t.split(/\n{2,}/).map(p => /^\s*[-*] /m.test(p)
    ? '<ul>' + p.split('\n').map(l => l.replace(/^\s*[-*] (.*)$/, '<li>$1</li>')).join('') + '</ul>'
    : '<p>' + p.replace(/\n/g, '<br>') + '</p>').join('');
  return t.replace(/\u0000(\d+)\u0000/g, (_m, i) => blocks[+i]);
}
const save = () => window.ma.saveChats(chats.map(c => ({ ...c, msgs: c.msgs.slice(-200) })));

function renderList() {
  $('#chatlist').innerHTML = chats.map(c => '<button data-id="' + c.id + '" class="' + (cur && cur.id === c.id ? 'on' : '') + '">' + esc(c.title) + '</button>').join('')
    || '<div class="sub">Noch keine Chats.</div>';
}
function renderMsgs() {
  const box = $('#msgs');
  if (!cur || !cur.msgs.length) {
    box.innerHTML = '<div class="hint"><b>Frag Claude auf deinem Server.</b><br>Zum Beispiel: „Wie voll ist die Backup-Platte?“, „Fasse meine Notizen zur Fahrschule zusammen“ oder „Welche neuen Dateien liegen im Eingang?“<br>Mit „Nur lesen“ kann Claude nichts verändern.</div>';
    return;
  }
  box.innerHTML = cur.msgs.map(m => {
    if (m.r === 'u') return '<div class="m u">' + esc(m.t) + '</div>';
    if (m.r === 'a') return '<div class="m' + (m.live ? ' typing' : '') + '">' + md(m.t || '…') + '</div>';
    if (m.r === 't') return '<div class="tool">' + esc(m.t) + '</div>';
    return '<div class="err">' + esc(m.t) + '</div>';
  }).join('');
  box.scrollTop = box.scrollHeight;
}
function newChat() {
  cur = { id: uid(), title: 'Neuer Chat', sid: null, msgs: [] };
  chats.unshift(cur); renderList(); renderMsgs(); $('#prompt').focus();
}
function openChat(id) { cur = chats.find(c => c.id === id); renderList(); renderMsgs(); }

function send() {
  const prompt = $('#prompt').value.trim();
  if (!prompt || running) return;
  if (!cur) newChat();
  if (cur.msgs.length === 0) cur.title = prompt.slice(0, 42);
  cur.msgs.push({ r: 'u', t: prompt }, { r: 'a', t: '', live: true });
  $('#prompt').value = '';
  running = { id: uid(), chat: cur };
  $('#send').hidden = true; $('#stop').hidden = false;
  renderList(); renderMsgs();
  window.ma.send({ id: running.id, prompt, sessionId: cur.sid, dir: $('#dir').value, mode: $('#mode').value, model: $('#model').value });
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
  }
  if (cur === c) renderMsgs();
});

async function status() {
  const el = $('#srv');
  const r = await window.ma.status();
  if (!r.ok) {
    el.innerHTML = '<span class="pill dot off">Server nicht erreichbar</span>';
    $('#srvbody').innerHTML = '<div class="empty">Server nicht erreichbar. Läuft er, und bist du im Heimnetz oder per VPN verbunden?</div>';
    return;
  }
  const L = r.out.split('\n');
  const up = parseFloat((L[0] || '').replace('up=', '')) || 0;
  const [used, size] = (L[1] || '').trim().split(/\s+/).map(Number);
  const [ru, rt] = (L[2] || '').trim().split(/\s+/).map(Number);
  const gb = n => (n / 1e9).toFixed(1) + ' GB';
  const d = Math.floor(up / 86400), h = Math.floor(up % 86400 / 3600);
  el.innerHTML = '<span class="pill dot">Server online · ' + d + ' T ' + h + ' Std</span>';
  $('#srvbody').innerHTML = '<h1>Server</h1><div class="grid">'
    + '<div class="card"><h2>Speicher</h2><div class="stat">' + gb(size - used) + ' <small>frei</small></div><div class="sub">' + gb(used) + ' von ' + gb(size) + '</div></div>'
    + '<div class="card"><h2>Arbeitsspeicher</h2><div class="stat">' + Math.round(ru / rt * 100) + '<small> %</small></div><div class="sub">' + gb(ru) + ' von ' + gb(rt) + '</div></div>'
    + '<div class="card"><h2>Backup-Timer</h2><div class="stat">' + esc((L[3] || '').trim()) + '</div></div></div>'
    + '<h2 class="mt">Rohdaten</h2><pre>' + esc(r.out.trim()) + '</pre>';
}

(async () => {
  cfg = await window.ma.config();
  $('#logo').innerHTML = '<svg viewBox="0 0 24 24"><path d="M4 18V9l8-5 8 5v9M9 18v-6h6v6"/></svg>';
  $('#dir').innerHTML = [['notizen', 'Notizen (Spiegel)'], ['bibliothek', 'Bibliothek'], ['server', 'Server-Home']].map(([v, n]) => '<option value="' + v + '">' + n + '</option>').join('');
  chats = await window.ma.loadChats(); cur = chats[0] || null; renderList(); renderMsgs();
  $('#portal').setAttribute('src', cfg.portal);
  $('#newChat').onclick = newChat;
  $('#send').onclick = send;
  $('#stop').onclick = () => { if (running) window.ma.stop(running.id); };
  $('#chatlist').onclick = e => { const b = e.target.closest('button'); if (b) openChat(b.dataset.id); };
  $('#prompt').addEventListener('keydown', e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); send(); } });
  $('#tabs').onclick = e => {
    const b = e.target.closest('button'); if (!b) return;
    document.querySelectorAll('#tabs button').forEach(x => x.removeAttribute('aria-current'));
    b.setAttribute('aria-current', 'page');
    ['chat', 'portal', 'server'].forEach(v => { $('#v-' + v).hidden = v !== b.dataset.v; });
    if (b.dataset.v === 'server') status();
  };
  status(); setInterval(status, 60000);
})();
