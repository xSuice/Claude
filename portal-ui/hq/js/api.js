/* MA-HOME HQ — Basis: API, Hilfsfunktionen, mdLite (Port aus Bestands-app.js, Logik unveraendert) */
export const $ = (s, r = document) => r.querySelector(s);
export const $$ = (s, r = document) => [...r.querySelectorAll(s)];

export const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const today = () => new Date().toISOString().slice(0, 10);
export const fmtBytes = n => n >= 1e9 ? (n / 1e9).toFixed(1) + ' GB' : n >= 1e6 ? (n / 1e6).toFixed(1) + ' MB' : n >= 1e3 ? Math.round(n / 1e3) + ' KB' : n + ' B';
export const fmtUp = s => { const d = Math.floor(s / 86400), h = Math.floor(s % 86400 / 3600), m = Math.floor(s % 3600 / 60); return d ? `${d} T ${h} Std` : h ? `${h} Std ${m} Min` : `${m} Min`; };
export const lvl = d => { if (!d) return ''; const diff = (new Date(d + 'T12:00:00') - new Date()) / 864e5; return diff < 0.5 ? 'l3' : diff < 3.5 ? 'l2' : ''; };
export const fmtDate = d => d ? new Date(d + 'T12:00:00').toLocaleDateString('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit' }) : '';
export const fmtTok = n => n >= 1e6 ? (n / 1e6).toFixed(1) + ' Mio' : n >= 1000 ? Math.round(n / 1000) + 'k' : String(n || 0);
export const fmtAgo = t => { const s = Math.max(0, Math.floor(Date.now() / 1000 - t)); return s < 3600 ? Math.max(1, Math.floor(s / 60)) + ' min' : s < 86400 ? Math.floor(s / 3600) + ' Std' : Math.floor(s / 86400) + ' Tg'; };

let toastTimer;
export function toast(msg, err) {
  const t = $('#toast');
  if (!t) return;
  t.textContent = msg;
  t.className = 'toast show' + (err ? ' err' : '');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.className = 'toast', 3200);
}

export async function api(path, opts = {}) {
  const o = { credentials: 'same-origin', headers: { 'X-MA-Request': '1', ...(opts.headers || {}) }, ...opts };
  if (o.body && typeof o.body === 'object' && !(o.body instanceof FormData)) {
    o.method = o.method || 'POST';
    o.headers['Content-Type'] = 'application/json';
    o.body = JSON.stringify(o.body);
  }
  const r = await fetch(path, o);
  if (!r.ok) {
    let m = 'Fehler ' + r.status;
    try { m = (await r.json()).error || m; } catch (e) { /* leer */ }
    throw new Error(r.status === 403 ? 'Nur für Administratoren.' : m);
  }
  const ct = r.headers.get('content-type') || '';
  return ct.includes('application/json') ? r.json() : r.text();
}

export const items = k => api('/api/items/' + k).then(d => d.items);

export async function cop(op, data) {
  const r = await fetch('/api/claude/op', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-MA-Request': '1' }, body: JSON.stringify({ op, ...data }) });
  if (!r.ok) throw new Error(r.status === 403 ? 'Nur für Administratoren.' : 'Fehler ' + r.status);
  return r.json();
}

/* --- mdLite: Chat-Markdown (unveraendert aus Bestand) --- */
function mdTable(rows) {
  const cells = r => r.replace(/^\s*\||\|\s*$/g, '').split('|').map(c => c.trim());
  const body = rows.filter(r => !/^[\s|:-]+$/.test(r));
  if (!body.length) return '';
  const [head, ...rest] = body;
  return '<div class="tblwrap"><table><thead><tr>' + cells(head).map(c => '<th>' + c + '</th>').join('') + '</tr></thead><tbody>' +
    rest.map(r => '<tr>' + cells(r).map(c => '<td>' + c + '</td>').join('') + '</tr>').join('') + '</tbody></table></div>';
}

export function mdLite(src) {
  const blocks = [];
  let t = esc(src).replace(/```(\w*)\n([\s\S]*?)```/g, (_m, lang, c) => { blocks.push('<div class="codebox">' + (/^(html|svg)$/i.test(lang) ? '<button class="pvw" type="button">Vorschau</button>' : '') + '<button class="cpy" type="button">Kopieren</button><pre><code>' + c + '</code></pre></div>'); return '\u0000' + (blocks.length - 1) + '\u0000'; });
  t = t.replace(/`([^`\n]+)`/g, '<code>$1</code>').replace(/\*\*([^*\n]+)\*\*/g, '<b>$1</b>').replace(/(^|[^*\w])\*([^*\n]+)\*(?!\w)/g, '$1<i>$2</i>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  const out = [];
  let list = null, tbl = null, para = [];
  const flush = () => {
    if (para.length) { out.push('<p>' + para.join('<br>') + '</p>'); para = []; }
    if (list) { out.push('<' + list.t + '>' + list.items.join('') + '</' + list.t + '>'); list = null; }
    if (tbl) { out.push(mdTable(tbl)); tbl = null; }
  };
  for (const line of t.split('\n')) {
    let m;
    if (/^\u0000\d+\u0000$/.test(line.trim())) { flush(); out.push(line.trim()); }
    else if (/^\s*\|.*\|\s*$/.test(line)) { if (!tbl) { flush(); tbl = []; } tbl.push(line); }
    else if ((m = line.match(/^(#{1,6})\s+(.*)$/))) { flush(); out.push('<h4 class="ch">' + m[2] + '</h4>'); }
    else if (/^\s*(-{3,}|\*{3,})\s*$/.test(line)) { flush(); out.push('<hr>'); }
    else if ((m = line.match(/^\s*[-*]\s+(.*)$/))) { if (!list || list.t !== 'ul') { flush(); list = { t: 'ul', items: [] }; } list.items.push('<li>' + m[1] + '</li>'); }
    else if ((m = line.match(/^\s*\d+[.)]\s+(.*)$/))) { if (!list || list.t !== 'ol') { flush(); list = { t: 'ol', items: [] }; } list.items.push('<li>' + m[1] + '</li>'); }
    else if ((m = line.match(/^&gt;\s?(.*)$/))) { flush(); out.push('<blockquote>' + m[1] + '</blockquote>'); }
    else if (!line.trim()) flush();
    else { if (list || tbl) flush(); para.push(line); }
  }
  flush();
  return out.join('').replace(/\u0000(\d+)\u0000/g, (_m, i) => blocks[+i]);
}
