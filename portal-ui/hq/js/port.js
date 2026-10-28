/* MA-HOME HQ — Port der Bestandsbereiche Neu, Musik, Einstellungen, Wissen (Graph), Vault (Editor), JARVIS-Auftraege.
   GENERIERT von build_port.py aus legacy/app.js: Logik und API-Vertraege 1:1 uebernommen (nur Adapter: view/head/ico/me). */
import { $, esc, api, cop, toast, mdLite, items, fmtBytes, fmtDate, fmtTok, fmtUp, fmtAgo, today } from './api.js';
import { openViewer, pushLayer, closeViewer } from './viewer.js';

let view = null;                              // aktuelles Wurzelelement (#view der Shell)
let me = { user: '', admin: false, domain: '' };
export const setMe = m => { me = m || me; };
const VERSION = '2026-10-27';
const CTX_MAX = 200000;
const head = (title, sub, extra = '') => '<div class="top"><div><h1>' + title + '</h1><div class="sub">' + (sub || '') + '</div></div>' + extra + '</div>';

const ICONS = {
  home: '<path d="M3 11l9-8 9 8M5 10v10h14V10"/>',
  neu: '<path d="M6 17V11a6 6 0 0112 0v6l1.5 2h-15zM10 21h4"/>',
  musik: '<path d="M9 18V6l10-2v12"/><circle cx="7" cy="18" r="2.2"/><circle cx="17" cy="16" r="2.2"/>',
  tasks: '<path d="M9 11l3 3 8-8M4 12v7a1 1 0 001 1h14"/>',
  notes: '<path d="M6 3h9l4 4v14H6zM14 3v5h5M9 13h7M9 17h5"/>',
  money: '<rect x="3" y="6" width="18" height="12" rx="2"/><circle cx="12" cy="12" r="2.5"/>',
  training: '<path d="M3 9v6M6 7v10M18 7v10M21 9v6M6 12h12"/>',
  files: '<path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>',
  term: '<path d="M4 6l6 6-6 6M13 18h7"/>',
  vault: '<path d="M5 4h11a3 3 0 013 3v13H8a3 3 0 01-3-3zM5 17a3 3 0 013-3h11M9 8h6"/>',
  verbindungen: '<path d="M9 7V3M15 7V3M7 7h10v4a5 5 0 01-10 0zM12 16v5"/>',
  einstellungen: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>',
  system: '<rect x="3" y="4" width="18" height="6" rx="1.5"/><rect x="3" y="14" width="18" height="6" rx="1.5"/><path d="M7 7h.01M7 17h.01"/>',
  trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
  check: '<path d="M5 12l5 5 9-10"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  down: '<path d="M12 4v11m0 0l-4-4m4 4l4-4M5 20h14"/>',
  ha: '<path d="M3 11l9-8 9 8M6 10v9h12v-9M10 19v-5h4v5"/>',
  bell: '<path d="M6 16V11a6 6 0 1112 0v5l2 2H4zM10 20a2 2 0 004 0"/>',
  sync: '<path d="M20 11a8 8 0 00-14-4M4 4v4h4M4 13a8 8 0 0014 4M20 20v-4h-4"/>',
  claude: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM18 16l.8 2.2L21 19l-2.2.8L18 22l-.8-2.2L15 19l2.2-.8z"/>',
  jarvis: '<circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="9"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3"/>',
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

function mdDoc(src) {
  let fm = '';
  src = src.replace(/^---\n([\s\S]*?)\n---\n?/, (_m, y) => { fm = '<pre class="fm">' + esc(y) + '</pre>'; return ''; });
  const blocks = [];
  let t = esc(src).replace(/```[^\n]*\n([\s\S]*?)```/g, (_m, c) => { blocks.push('<pre><code>' + c + '</code></pre>'); return '\u0000' + (blocks.length - 1) + '\u0000'; });
  if (typeof V !== 'undefined' && V.att && V.att.size) {      // Bilder und PDFs aus dem Vault: ![[bild.png]] und ![alt](bild.png)
    const url = n => { const rel = V.att.get(n.split('/').pop().toLowerCase().replace(/&amp;/g, '&')); return rel ? '/api/file?path=' + encodeURIComponent('Bibliothek/vault-notizen/' + rel) : ''; };
    t = t.replace(/!\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]/g, (m, n) => { const u = url(n); return u ? (/\.pdf$/i.test(n) ? '<a class="chip" href="' + u + '" target="_blank" rel="noopener">📄 ' + n + '</a>' : '<img class="vimg2" loading="lazy" src="' + u + '" alt="' + n + '">') : m; });
    t = t.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (m, alt, n) => { if (/^https?:/i.test(n)) return m; const u = url(n); return u ? '<img class="vimg2" loading="lazy" src="' + u + '" alt="' + alt + '">' : m; });
  }
  t = t.replace(/!\[\[([^\]|#]+?)(#[^\]|]*)?(?:\|[^\]]*)?\]\]/g, (m, n, h) => '<div class="embed" data-t="' + n + (h || '') + '"><span class="sub">lädt …</span></div>');
  t = t.replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g, '<span class="wl" data-t="$1">$2</span>').replace(/\[\[([^\]]+)\]\]/g, '<span class="wl" data-t="$1">$1</span>');
  t = t.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  t = t.replace(/`([^`\n]+)`/g, '<code>$1</code>').replace(/\*\*([^*\n]+)\*\*/g, '<b>$1</b>').replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<i>$2</i>');
  // Obsidian-Tags (#tag) anklickbar, nicht innerhalb von Code und nicht in Überschriften (dort steht nach # ein Leerzeichen)
  t = t.split(/(<code>.*?<\/code>)/).map((x, i) => i % 2 ? x : x.replace(/(^|[\s(>])#([\p{L}][\p{L}\p{N}_\/-]{1,40})/gu, '$1<span class="ntag" data-tag="$2">#$2</span>')).join('');
  const out = [];
  let list = null;
  const flush = () => { if (list) { out.push('<' + list.t + '>' + list.items.join('') + '</' + list.t + '>'); list = null; } };
  for (const line of t.split('\n')) {
    let m;
    if ((m = line.match(/^(#{1,6})\s+(.*)$/))) { flush(); out.push('<h' + m[1].length + '>' + m[2] + '</h' + m[1].length + '>'); }
    else if (/^\s*(-{3,}|\*{3,})\s*$/.test(line)) { flush(); out.push('<hr>'); }
    else if ((m = line.match(/^\s*[-*]\s+(?:\[( |x)\]\s+)?(.*)$/))) { if (!list || list.t !== 'ul') { flush(); list = { t: 'ul', items: [] }; } list.items.push('<li>' + (m[1] ? (m[1] === 'x' ? '☑ ' : '☐ ') : '') + m[2] + '</li>'); }
    else if ((m = line.match(/^\s*\d+\.\s+(.*)$/))) { if (!list || list.t !== 'ol') { flush(); list = { t: 'ol', items: [] }; } list.items.push('<li>' + m[1] + '</li>'); }
    else if ((m = line.match(/^&gt;\s?(.*)$/))) {
      flush();
      const co = m[1].match(/^\[!(\w+)\][+-]?\s*(.*)$/);                 // Obsidian-Callout: > [!note] Titel
      out.push(co ? '<blockquote class="callout c-' + co[1].toLowerCase() + '"><b>' + (co[2] || co[1]) + '</b></blockquote>' : '<blockquote>' + m[1] + '</blockquote>');
    }
    else if (!line.trim()) { flush(); }
    else { flush(); out.push('<p>' + line + '</p>'); }
  }
  flush();
  return fm + out.join('').replace(/\u0000(\d+)\u0000/g, (_m, i) => blocks[+i]);
}

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
  const w = e.target.closest('.wl'); if (!w || w.closest('#vread')) return;   // Vault-Leser navigiert selbst
  try { const g = await loadGraph(); const k = (w.dataset.t || w.textContent).toLowerCase().replace(/\.md$/, ''); const i = g.byName[k] ?? g.byName[k.split('/').pop()]; if (i !== undefined) openNote(i); else toast('Notiz „' + w.textContent + '“ nicht gefunden', 1); } catch (er) { toast(er.message, 1); }
});
const GCOL = ['#e5173f', '#3d8bfd', '#2fbf71', '#f59e0b', '#a78bfa', '#22c1c3', '#c9ced9', '#ff7ab6', '#84cc16', '#fb923c'];

async function wissen() {
  view.innerHTML = head('Wissen', 'Deine Notizen und ihre Verbindungen', '<div class="gtools"><input id="gq" placeholder="Notiz suchen …"><button class="btn small ghost" id="greset">Ansicht zurücksetzen</button></div>') +
    '<div class="gwrap"><canvas id="gc"></canvas><div class="gtip" id="gtip" hidden></div><button class="glegtog" id="glegtog" type="button" aria-expanded="false">Legende</button><div class="glegend" id="glegend"></div><div class="ginfo" id="ginfo"></div>' +
    '<div class="gzoom"><button type="button" id="gzin" aria-label="Hineinzoomen">+</button><button type="button" id="gzout" aria-label="Herauszoomen">−</button></div></div>';
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
  const pick = (sx, sy, margin = 6) => { const w = toWorld(sx, sy); let best = -1, bd = 1e9; P.forEach((p, i) => { const d = (p.x - w.x) ** 2 + (p.y - w.y) ** 2; if (d < bd && d < (p.r + margin / cam.k) ** 2) { bd = d; best = i; } }); return best; };
  const pos = e => { const r = cv.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
  // Zeiger: eine Maus oder ein Finger zieht Knoten oder Ansicht, zwei Finger zoomen (um die Fingermitte) und verschieben.
  // Tippen öffnet die Notiz; auf dem Handy mit kurzer Verzögerung, damit Doppeltippen (hineinzoomen) nicht zugleich öffnet.
  const ptrs = new Map();
  let moved = false, pinch = null, lastTap = null, openTimer = null;
  const clampK = k => Math.min(6, Math.max(0.15, k));
  const zoomAt = (sx, sy, f) => { const before = toWorld(sx, sy); cam.k = clampK(cam.k * f); const after = toWorld(sx, sy); cam.x += before.x - after.x; cam.y += before.y - after.y; };
  const startPan = (m) => { drag = { pan: true, sx: m.x, sy: m.y, cx: cam.x, cy: cam.y }; };
  cv.addEventListener('pointerdown', e => {
    try { cv.setPointerCapture(e.pointerId); } catch (er) { /* Zeiger schon weg */ }
    const m = pos(e); ptrs.set(e.pointerId, m);
    if (ptrs.size === 2) {
      const [a, b] = [...ptrs.values()], mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
      pinch = { d0: Math.hypot(a.x - b.x, a.y - b.y) || 1, k0: cam.k, w: toWorld(mid.x, mid.y) };
      drag = null; moved = true; clearTimeout(openTimer); return;
    }
    if (ptrs.size > 2) return;
    const i = pick(m.x, m.y, e.pointerType === 'mouse' ? 6 : 16); moved = false;
    drag = i >= 0 ? { i, sx: m.x, sy: m.y, touch: e.pointerType !== 'mouse' } : { pan: true, sx: m.x, sy: m.y, cx: cam.x, cy: cam.y, touch: e.pointerType !== 'mouse' };
  });
  cv.addEventListener('pointermove', e => {
    const m = pos(e);
    if (ptrs.has(e.pointerId)) ptrs.set(e.pointerId, m);
    if (pinch && ptrs.size >= 2) {
      const [a, b] = [...ptrs.values()], mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
      cam.k = clampK(pinch.k0 * (Math.hypot(a.x - b.x, a.y - b.y) || 1) / pinch.d0);
      cam.x = pinch.w.x - (mid.x - W / 2) / cam.k; cam.y = pinch.w.y - (mid.y - H / 2) / cam.k;   // der Punkt unter den Fingern bleibt dort
      return;
    }
    if (drag && (Math.abs(m.x - drag.sx) > 6 || Math.abs(m.y - drag.sy) > 6)) moved = true;
    if (drag && drag.i !== undefined) { if (!moved) return; const w = toWorld(m.x, m.y); P[drag.i].x = w.x; P[drag.i].y = w.y; alpha = Math.max(alpha, 0.3); return; }
    if (drag && drag.pan) { if (!moved) return; cam.x = drag.cx - (m.x - drag.sx) / cam.k; cam.y = drag.cy - (m.y - drag.sy) / cam.k; return; }
    if (e.pointerType !== 'mouse') return;
    hover = pick(m.x, m.y); const tip = $('#gtip');
    if (hover >= 0) { const n = g.nodes[hover]; tip.hidden = false; tip.textContent = n.n + ' · ' + n.d + ' Verbindungen · ' + n.g; tip.style.left = (m.x + 14) + 'px'; tip.style.top = (m.y + 10) + 'px'; } else tip.hidden = true;
    cv.style.cursor = hover >= 0 ? 'pointer' : 'grab';
  });
  const release = e => {
    const m = pos(e), wasPinch = !!pinch, d = drag;
    ptrs.delete(e.pointerId);
    if (wasPinch) {
      if (ptrs.size < 2) { pinch = null; const rest = [...ptrs.values()][0]; if (rest) startPan(rest); else drag = null; moved = true; }
      return;
    }
    drag = null;
    if (e.type === 'pointercancel' || !d || moved) return;
    // Tippen ohne Ziehen
    const now = Date.now(), dbl = lastTap && now - lastTap.t < 320 && Math.hypot(m.x - lastTap.x, m.y - lastTap.y) < 30;
    if (dbl) { clearTimeout(openTimer); lastTap = null; zoomAt(m.x, m.y, 2); return; }
    lastTap = { t: now, x: m.x, y: m.y };
    if (d.i !== undefined) {
      if (d.touch) { clearTimeout(openTimer); const i = d.i; openTimer = setTimeout(() => { lastTap = null; openNote(i); }, 330); } else openNote(d.i);
    }
  };
  cv.addEventListener('pointerup', release);
  cv.addEventListener('pointercancel', release);
  cv.addEventListener('dblclick', e => { const m = pos(e); if (pick(m.x, m.y) < 0) zoomAt(m.x, m.y, 2); });
  $('#gzin').onclick = () => { cam.k = clampK(cam.k * 1.4); };
  $('#gzout').onclick = () => { cam.k = clampK(cam.k / 1.4); };
  const leg = $('#glegend'), legtog = $('#glegtog');
  const legSet = open => { leg.hidden = !open; legtog.setAttribute('aria-expanded', open ? 'true' : 'false'); };
  legSet(window.innerWidth > 820);
  legtog.onclick = () => legSet(leg.hidden);
  cv.addEventListener('wheel', e => { e.preventDefault(); const m = pos(e), before = toWorld(m.x, m.y); cam.k = clampK(cam.k * (e.deltaY < 0 ? 1.15 : 0.87)); const after = toWorld(m.x, m.y); cam.x += before.x - after.x; cam.y += before.y - after.y; }, { passive: false });
  $('#gq').addEventListener('input', e => { query = e.target.value.trim().toLowerCase(); if (query) { const i = g.nodes.findIndex(n => n.n.toLowerCase().includes(query)); if (i >= 0) { cam.x = P[i].x; cam.y = P[i].y; cam.k = Math.max(cam.k, 1.6); } } });
  $('#gq').addEventListener('keydown', e => { if (e.key === 'Enter') { const i = g.nodes.findIndex(n => n.n.toLowerCase().includes(query)); if (i >= 0) openNote(i); } });
  $('#greset').onclick = () => { cam = { x: 0, y: 0, k: 0.9 }; query = ''; $('#gq').value = ''; alpha = 0.6; };
}

/* ---------- Vault (Obsidian-Ersatz, nur Admin): Notizen lesen, schreiben, verlinken ---------- */
// Arbeitet auf dem Server-Spiegel des Vaults (Brücke, Op „note“). Speichern mit Konflikterkennung und Versionsverlauf; der PC gleicht per server-to-vault.py ab.
const V = { items: null, prot: [], map: null, att: new Map(), bm: [], cur: null, timer: null, recent: [] };
try { V.recent = JSON.parse(localStorage.getItem('ma-vault-recent') || '[]'); } catch (e) { V.recent = []; }
async function vnote(act, p = {}) {
  const r = await cop('note', { data: JSON.stringify({ act, ...p }) });
  if (r.ok === false && !r.conflict) throw new Error(r.error || 'Fehler');
  return r;
}
async function vindex(force) {
  if (V.items && !force) return V.items;
  const r = await vnote('index');
  V.items = r.items || []; V.prot = r.protected || []; V.map = new Map();
  V.att = new Map((r.att || []).map(p => [p.split('/').pop().toLowerCase(), p])); V.bm = r.bookmarks || [];   // Anhänge (Bilder, PDFs) nach Dateiname
  for (const it of V.items) {
    const low = it.p.toLowerCase(), base = low.slice(low.lastIndexOf('/') + 1, -3), cur = V.map.get(base);
    if (!cur || it.p.length < cur.length) V.map.set(base, it.p);
    V.map.set(low.slice(0, -3), it.p);
  }
  return V.items;
}
const vname = p => p.slice(p.lastIndexOf('/') + 1, -3);
const vopen = (p, edit) => { location.hash = '#/vault?p=' + encodeURIComponent(p) + (edit ? '&e=1' : ''); };
const vresolve = n => { n = String(n).trim().toLowerCase().replace(/\.md$/, ''); return V.map && (V.map.get(n) || V.map.get(n.slice(n.lastIndexOf('/') + 1))); };
function vrecent(p) { V.recent = [p, ...V.recent.filter(x => x !== p)].slice(0, 12); try { localStorage.setItem('ma-vault-recent', JSON.stringify(V.recent)); } catch (e) { /* ohne Speicher */ } }
const vrow = (p, extra) => '<div class="row" data-p="' + esc(p) + '"><div class="grow"><b>' + esc(vname(p)) + '</b><span>' + esc(p.split('/').slice(0, -1).join(' / ') || 'Wurzel') + (extra ? ' · ' + extra : '') + '</span></div></div>';
async function vflush() { if (V.cur && V.cur.dirty) await vsave(false); }
async function vsave(force) {
  const S = V.cur; if (!S || (!S.dirty && !force)) return;
  clearTimeout(V.timer);
  const st = $('#vstat');
  try {
    const r = await vnote('write', { path: S.path, content: S.content, etag: S.etag, force: !!force });
    if (r.conflict) { S.conflict = r; if (st) vconflict(); return; }
    S.etag = r.etag; S.dirty = false; S.conflict = null;
    if (st) st.textContent = 'Gespeichert ' + new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
    V.stale = true;                                    // Index beim nächsten Öffnen neu laden (Änderungszeit); im Editor bleibt er für die Vorschläge nutzbar
  } catch (er) { if (st) st.textContent = 'Fehler: ' + er.message; toast(er.message, 1); }
}
function vconflict() {
  const S = V.cur, st = $('#vstat'); if (!st) return;
  st.innerHTML = 'Auf dem Server geändert. <button class="btn small ghost" id="vkeep">Meine Version behalten</button> <button class="btn small ghost" id="vtheirs">Serverversion laden</button>';
  $('#vkeep').onclick = () => { S.etag = S.conflict.etag; vsave(true); };
  $('#vtheirs').onclick = () => { S.content = S.conflict.content; S.etag = S.conflict.etag; S.dirty = false; S.conflict = null; vdraw(); };
}
document.addEventListener('visibilitychange', () => { if (document.hidden) vflush(); });
window.addEventListener('pagehide', () => { vflush(); });

async function vault() {
  const q = new URLSearchParams(location.hash.split('?')[1] || '');
  await vflush(); clearTimeout(V.timer);
  try { await vindex(V.stale); V.stale = false; } catch (er) { view.innerHTML = head('Vault', 'Notizen') + '<div class="empty">' + esc(er.message) + '</div>'; return; }
  if (q.get('p')) return vnoteView(q.get('p'), q.get('e') === '1');
  if (q.get('t')) return vtagView(q.get('t'));
  return vbrowse(q.get('d') || '');
}
function vbrowse(dir) {
  const prefix = dir ? dir + '/' : '', folders = new Map(), notes = [];
  for (const it of V.items) {
    if (!it.p.startsWith(prefix)) continue;
    const rest = it.p.slice(prefix.length), i = rest.indexOf('/');
    if (i < 0) notes.push(it); else folders.set(rest.slice(0, i), (folders.get(rest.slice(0, i)) || 0) + 1);
  }
  const crumbs = '<button data-d="">Vault</button>' + dir.split('/').filter(Boolean).map((x, i, a) => ' / <button data-d="' + esc(a.slice(0, i + 1).join('/')) + '">' + esc(x) + '</button>').join('');
  const recent = !dir ? V.recent.filter(p => V.map && [...V.map.values()].includes(p)).slice(0, 6) : [];
  const marks = !dir ? V.bm.filter(p => V.map && [...V.map.values()].includes(p)) : [];
  view.innerHTML = head('Vault', V.items.length + ' Notizen · wie Obsidian', '<button class="btn ghost small" id="vtags">Tags</button> <button class="btn ghost small" id="vdaily">Heute</button> <button class="btn ghost small" id="vnew">Neu</button>') +
    '<form class="quick" id="vsf"><input name="q" placeholder="Notiz suchen … (Enter = Volltext)" autocomplete="off" enterkeyhint="search"><button class="btn">Volltext</button></form>' +
    '<div class="list" id="vres" hidden></div>' +
    (marks.length ? '<h2 class="vh">★ Lesezeichen</h2><div class="list" id="vmk">' + marks.map(p => vrow(p)).join('') + '</div>' : '') +
    (recent.length ? '<h2 class="vh">Zuletzt geöffnet</h2><div class="list" id="vrec">' + recent.map(p => vrow(p)).join('') + '</div>' : '') +
    '<div class="crumbs" id="vcr">' + crumbs + '</div><div class="list" id="vlist">' +
    [...folders].sort((a, b) => a[0].localeCompare(b[0], 'de')).map(([n, c]) => '<div class="row" data-d="' + esc(prefix + n) + '"><div class="grow"><b>📁 ' + esc(n) + '</b><span>' + c + ' Notiz' + (c > 1 ? 'en' : '') + '</span></div></div>').join('') +
    notes.map(it => vrow(it.p, new Date(it.m * 1000).toLocaleDateString('de-DE'))).join('') + (folders.size + notes.length ? '' : '<div class="empty">Leer.</div>') + '</div>';
  const go = e => { const r = e.target.closest('.row'); if (!r) return; if (r.dataset.d !== undefined) location.hash = '#/vault' + (r.dataset.d ? '?d=' + encodeURIComponent(r.dataset.d) : ''); else if (r.dataset.p) vopen(r.dataset.p); };
  $('#vlist').onclick = go; $('#vres').onclick = go; if ($('#vrec')) $('#vrec').onclick = go; if ($('#vmk')) $('#vmk').onclick = go;
  $('#vcr').onclick = e => { const b = e.target.closest('button'); if (b) location.hash = '#/vault' + (b.dataset.d ? '?d=' + encodeURIComponent(b.dataset.d) : ''); };
  const box = $('#vres'), inp = $('#vsf').q;
  inp.oninput = () => {                                 // Schnellwechsler: Dateinamen filtern
    const w = inp.value.toLowerCase().split(/\s+/).filter(Boolean).map(x => x.replace(/^(path|datei|ordner):/, ''));      // path:Projekte wirkt wie Projekte
    if (!w.length) { box.hidden = true; return; }
    const hits = V.items.filter(it => w.every(x => it.p.toLowerCase().includes(x))).slice(0, 30);
    box.hidden = false; box.innerHTML = hits.map(it => vrow(it.p)).join('') || '<div class="empty">Keine Notiz mit diesem Namen. Enter sucht im Text.</div>';
  };
  $('#vsf').onsubmit = async e => {                     // Volltextsuche (Op „search“)
    e.preventDefault(); const t = inp.value.trim(); if (t.length < 2) return;
    const tg = t.match(/^tag:#?(\S+)$/i); if (tg) { location.hash = '#/vault?t=' + encodeURIComponent(tg[1]); return; }      // tag:projekt öffnet die Tag-Liste
    box.hidden = false; box.innerHTML = '<div class="empty">Suche läuft …</div>';
    try {
      const d = await cop('search', { q: t });
      const hits = (d.hits || []).filter(h => h.path.startsWith('vault-notizen/')).map(h => ({ ...h, path: h.path.slice(14) }));
      box.innerHTML = hits.length ? hits.map(h => '<div class="row" data-p="' + esc(h.path) + '"><div class="grow"><b>' + esc(vname(h.path)) + '</b><span>' + esc(h.path.split('/').slice(0, -1).join(' / ')) + ' · Zeile ' + h.line + '</span><span>' + esc(h.text) + '</span></div></div>').join('') : '<div class="empty">Nichts gefunden.</div>';
    } catch (er) { box.innerHTML = '<div class="empty">' + esc(er.message) + '</div>'; }
  };
  $('#vtags').onclick = async () => {
    try {
      const t = (await vnote('tags')).tags || {};
      box.hidden = false;
      box.innerHTML = '<div class="chips">' + Object.entries(t).map(([k, v]) => '<a class="chip" href="#/vault?t=' + encodeURIComponent(k) + '">#' + esc(k) + ' (' + v.length + ')</a>').join('') + '</div>';
    } catch (er) { toast(er.message, 1); }
  };
  $('#vdaily').onclick = async () => { try { vopen((await vnote('daily')).path, true); } catch (er) { toast(er.message, 1); } };
  $('#vnew').onclick = async () => {
    const tpl = (prompt('Vorlage: leer, projekt, lernnotiz, meeting, tagesnotiz', 'leer') || '').trim().toLowerCase(); if (!tpl) return;
    let n = (prompt('Name der neuen Notiz (mit Ordner, z. B. 10 Leben/Idee):', (dir || '00 Inbox') + '/') || '').trim(); if (!n) return;
    if (!n.endsWith('.md')) n += '.md';
    try { vopen((await vnote('create', { path: n, template: tpl })).path, true); } catch (er) { toast(er.message, 1); }
  };
}
async function vtagView(tag) {
  view.innerHTML = head('Vault', '#' + esc(tag)) + '<div class="skeleton"></div>';
  try {
    const t = (await vnote('tags')).tags || {};
    view.innerHTML = head('Vault', '#' + esc(tag), '<a class="btn ghost small" href="#/vault">Zurück</a>') + '<div class="list" id="vlist">' + ((t[tag] || []).map(p => vrow(p)).join('') || '<div class="empty">Keine Notizen mit diesem Tag.</div>') + '</div>';
    $('#vlist').onclick = e => { const r = e.target.closest('.row'); if (r) vopen(r.dataset.p); };
  } catch (er) { view.innerHTML = head('Vault') + '<div class="empty">' + esc(er.message) + '</div>'; }
}
async function vnoteView(p, edit) {
  view.innerHTML = head('Vault', esc(p)) + '<div class="skeleton"></div>';
  let r;
  try { r = await vnote('read', { path: p }); }
  catch (er) {
    view.innerHTML = head('Vault', esc(p), '<a class="btn ghost small" href="#/vault">Zurück</a>') + '<div class="empty">' + esc(er.message) + '</div>';
    return;
  }
  V.cur = { path: p, etag: r.etag, content: r.content, ro: r.readonly, big: r.big, dirty: false, backlinks: r.backlinks || [], outgoing: r.outgoing || [], edit: edit && !r.readonly };
  vrecent(p); vdraw();
}
// Lokale Graph-Ansicht der Notiz: Mitte = diese Notiz, Kreis = ausgehende Links und Rückverweise (Tippen öffnet die Notiz)
function vgraph(S) {
  const box = $('#vgraph'); box.hidden = !box.hidden; if (box.hidden) return;
  const out = S.outgoing || [], inn = S.backlinks || [], all = [...new Set([...out, ...inn])].slice(0, 24);
  if (!all.length) { box.innerHTML = '<div class="empty">Diese Notiz hat keine Verknüpfungen.</div>'; return; }
  const W = 340, H = 340, cx = W / 2, cy = H / 2, R = 120;
  const nodes = all.map((p, i) => { const a = 2 * Math.PI * i / all.length - Math.PI / 2; return { p, x: Math.round(cx + R * Math.cos(a)), y: Math.round(cy + R * Math.sin(a)), both: out.includes(p) && inn.includes(p), inn: inn.includes(p) }; });
  box.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" class="vsvg">' +
    nodes.map(n => '<line x1="' + cx + '" y1="' + cy + '" x2="' + n.x + '" y2="' + n.y + '" class="ve' + (n.both ? ' both' : '') + '"/>').join('') +
    nodes.map(n => '<g class="vn' + (n.inn && !n.both ? ' inn' : '') + '" data-p="' + esc(n.p) + '"><circle cx="' + n.x + '" cy="' + (n.y + 6) + '" r="24" fill="transparent"/><circle cx="' + n.x + '" cy="' + n.y + '" r="8"/><text x="' + n.x + '" y="' + (n.y + 19) + '" text-anchor="middle">' + esc(vname(n.p).slice(0, 15)) + '</text></g>').join('') +
    '<circle cx="' + cx + '" cy="' + cy + '" r="12" class="vc"/><text x="' + cx + '" y="' + (cy + 4) + '" text-anchor="middle" class="vct">' + esc(vname(S.path).slice(0, 12)) + '</text></svg><div class="sub">Rot: verlinkt von dir · Grau: verlinkt hierher · Linie dick: beides</div>';
  box.onclick = e => { const g = e.target.closest('.vn'); if (g) vopen(g.dataset.p); };
}
// Gliederung (Überschriften) einer Notiz, ohne Codeblöcke
function vOutline(text) {
  const heads = [...text.replace(/```[\s\S]*?```/g, '').matchAll(/^(#{1,4})\s+(.+)$/gm)].map(m => ({ l: m[1].length, t: m[2].trim() }));
  if (heads.length < 2) return '';
  return '<details class="mt"><summary>Gliederung (' + heads.length + ')</summary><div id="vol" class="vol">' + heads.map(h => '<button type="button" style="margin-left:' + (h.l - 1) * 14 + 'px" data-h="' + esc(h.t) + '">' + esc(h.t) + '</button>').join('') + '</div></details>';
}
function vdraw() {
  const S = V.cur, dir = S.path.split('/').slice(0, -1).join('/');
  view.innerHTML = head('Vault', esc(S.path), '<a class="btn ghost small" href="#/vault' + (dir ? '?d=' + encodeURIComponent(dir) : '') + '">Ordner</a> ' +
    (S.ro ? '' : '<button class="btn ghost small" id="vmode">' + (S.edit ? 'Lesen' : 'Bearbeiten') + '</button> ') + '<button class="btn ghost small" id="vbm" title="Lesezeichen">' + (V.bm.includes(S.path) ? '★' : '☆') + '</button> <button class="btn ghost small" id="vgb">Graph</button> <button class="btn ghost small" id="vmore">⋯</button>') +
    '<div id="vgraph" hidden></div>' +
    (S.ro ? '<div class="sub">' + (S.big ? 'Zu lang für den Editor (nur Lesen).' : 'Geschützter Bereich (nur Lesen).') + '</div>' : '') +
    '<div id="vmenu" class="vmenu" hidden><button type="button" data-m="rename">Umbenennen / verschieben</button><button type="button" data-m="versions">Versionen</button><button type="button" data-m="delete">Löschen</button><button type="button" data-m="copy">Link kopieren</button></div><div id="vvers" class="list" hidden></div>' +
    (S.edit
      ? '<div class="vtool">' + [['**', '**', 'F'], ['*', '*', 'K'], ['[[', ']]', '[[ ]]'], ['`', '`', '`'], ['- [ ] ', '', '☐'], ['## ', '', 'H2'], ['> ', '', '❝']].map(([a, b, l]) => '<button type="button" data-w="' + esc(a) + '" data-x="' + esc(b) + '">' + l + '</button>').join('') + '</div>' +
        '<textarea id="ved" class="ved" spellcheck="false" autocapitalize="sentences">' + esc(S.content) + '</textarea><div id="vsug" class="vsug" hidden></div><div id="vstat" class="sub">' + (S.dirty ? 'Ungespeichert …' : 'Bereit') + '</div>'
      : '<article class="md" id="vread">' + mdDoc(S.content) + '</article>') +
    (S.edit ? '' : vOutline(S.content)) +
    '<details class="mt" id="vbl"><summary>Rückverweise (' + S.backlinks.length + ')</summary><div class="list">' + (S.backlinks.map(p => vrow(p)).join('') || '<div class="empty">Keine Notiz verlinkt hierher.</div>') + '</div></details>';
  if ($('#vmode')) $('#vmode').onclick = async () => { await vflush(); S.edit = !S.edit; vdraw(); };
  $('#vgb').onclick = () => vgraph(S);
  $('#vbm').onclick = async () => { try { V.bm = (await vnote('bookmark', { path: S.path })).bookmarks; $('#vbm').textContent = V.bm.includes(S.path) ? '★' : '☆'; } catch (er) { toast(er.message, 1); } };
  if ($('#vol')) $('#vol').onclick = e => { const b = e.target.closest('button'); if (!b) return; const h = [...$('#vread').querySelectorAll('h1,h2,h3,h4')].find(x => x.textContent.trim() === b.dataset.h); if (h) h.scrollIntoView({ behavior: 'smooth', block: 'start' }); };
  $('#vbl').onclick = e => { const r = e.target.closest('.row'); if (r) vopen(r.dataset.p); };
  $('#vmore').onclick = () => { const m = $('#vmenu'); m.hidden = !m.hidden; };
  $('#vmenu').onclick = async e => {
    const b = e.target.closest('button'); if (!b) return;
    try {
      if (b.dataset.m === 'copy') { await navigator.clipboard.writeText('[[' + vname(S.path) + ']]'); toast('Link kopiert'); }
      else if (S.ro) toast('Nur lesen', 1);
      else if (b.dataset.m === 'rename') {
        const to = (prompt('Neuer Pfad (mit Ordner und .md):', S.path) || '').trim(); if (!to || to === S.path) return;
        await vflush(); const r = await vnote('rename', { path: S.path, to: to.endsWith('.md') ? to : to + '.md', links: true });
        toast('Verschoben · ' + r.links_updated + ' Links angepasst' + (r.links_skipped ? ', ' + r.links_skipped + ' in geschützten Ordnern unverändert' : '')); V.items = null; vopen(r.path);
      } else if (b.dataset.m === 'delete') {
        if (!confirm('Notiz „' + vname(S.path) + '“ in den Papierkorb des Servers verschieben? (Die PC-Kopie bleibt bestehen.)')) return;
        await vnote('delete', { path: S.path }); V.cur = null; V.items = null; location.hash = '#/vault' + (dir ? '?d=' + encodeURIComponent(dir) : '');
      } else if (b.dataset.m === 'versions') {
        const vs = (await vnote('versions', { path: S.path })).versions || [], box = $('#vvers');
        box.hidden = false;
        box.innerHTML = vs.length ? vs.map(v => '<div class="row" data-t="' + esc(v.t) + '"><div class="grow"><b>' + new Date(+v.t).toLocaleString('de-DE') + '</b><span>' + v.s + ' Bytes</span></div><button class="btn small ghost">Wiederherstellen</button></div>').join('') : '<div class="empty">Noch keine früheren Versionen.</div>';
        box.onclick = async ev => { const row = ev.target.closest('.row'); if (!row || !ev.target.closest('button')) return; const r = await vnote('restore', { path: S.path, t: row.dataset.t }); S.content = r.content; S.etag = r.etag; S.dirty = false; toast('Wiederhergestellt'); vdraw(); };
      }
    } catch (er) { toast(er.message, 1); }
  };
  if (S.edit) {
    const ta = $('#ved');
    ta.oninput = () => {
      S.content = ta.value; S.dirty = true; $('#vstat').textContent = 'Ungespeichert …';
      clearTimeout(V.timer); V.timer = setTimeout(() => vsave(false), 1500);
      const m = ta.value.slice(0, ta.selectionStart).match(/\[\[([^\]\n|]*)$/), box = $('#vsug');
      if (!m) { box.hidden = true; return; }
      const w = m[1].toLowerCase().split(/\s+/).filter(Boolean), hits = V.items.filter(it => w.every(x => it.p.toLowerCase().includes(x))).slice(0, 8);
      box.hidden = !hits.length;
      box.innerHTML = hits.map(it => '<button type="button" data-n="' + esc(vname(it.p)) + '">' + esc(it.p.slice(0, -3)) + '</button>').join('');
      box.onclick = ev => { const b = ev.target.closest('button'); if (!b) return; ta.setRangeText(b.dataset.n + ']]', ta.selectionStart - m[1].length, ta.selectionStart, 'end'); box.hidden = true; ta.dispatchEvent(new Event('input')); ta.focus(); };
    };
    ta.onblur = () => vsave(false);
    document.querySelector('.vtool').onclick = e => {
      const b = e.target.closest('button'); if (!b) return;
      const a = b.dataset.w, x = b.dataset.x, s = ta.selectionStart, en = ta.selectionEnd, sel = ta.value.slice(s, en);
      ta.setRangeText(a + sel + x, s, en, 'end'); if (!sel && x) ta.setSelectionRange(s + a.length, s + a.length);
      ta.dispatchEvent(new Event('input')); ta.focus();
    };
    if (S.conflict) vconflict();
  } else {
    document.querySelectorAll('#vread .embed').forEach(async el => {     // ![[Notiz]]: Inhalt der anderen Notiz einblenden (eine Ebene)
      const target = vresolve(el.dataset.t.split('#')[0]);
      if (!target) { el.innerHTML = '<span class="sub">Notiz „' + esc(el.dataset.t) + '“ nicht gefunden</span>'; return; }
      try {
        const r = await vnote('read', { path: target });
        el.innerHTML = '<div class="embh"><a href="#/vault?p=' + encodeURIComponent(target) + '">' + esc(vname(target)) + '</a></div>' + mdDoc(r.content.replace(/!\[\[/g, '[['));
      } catch (er) { el.innerHTML = '<span class="sub">' + esc(er.message) + '</span>'; }
    });
    $('#vread').onclick = e => {
      const wl = e.target.closest('.wl'), tg = e.target.closest('.ntag');
      if (tg) { location.hash = '#/vault?t=' + encodeURIComponent(tg.dataset.tag); return; }
      if (!wl) return;
      const name = wl.dataset.t.split('|')[0].split('#')[0], target = vresolve(name);
      if (target) vopen(target);
      else if (confirm('Die Notiz „' + name + '“ gibt es noch nicht. Anlegen?')) {
        const dir0 = S.path.split('/').slice(0, -1).join('/'), np = (dir0 ? dir0 + '/' : '') + name.replace(/[\\/:*?"<>|]/g, '-') + '.md';
        vnote('create', { path: np, template: 'leer' }).then(r => { V.items = null; vopen(r.path, true); }).catch(er => toast(er.message, 1));
      }
    };
  }
}

async function neu() {
  view.innerHTML = head('Neu', 'Wichtiges, Mails, Updates und Stand des Servers', '<button class="btn small ghost" id="nrf" type="button">Aktualisieren</button>') + '<div id="nb"><div class="empty">Lade …</div></div>';
  const ul = a => a && a.length ? '<ul class="nl">' + a.map(x => '<li>' + esc(x) + '</li>').join('') + '</ul>' : '<div class="sub">nichts</div>';
  const card = (t, body, cls = '') => '<div class="card mt ' + cls + '"><h2>' + t + '</h2>' + body + '</div>';
  const draw = async () => {
    let d;
    try {
      const r = await fetch('/api/file?path=' + encodeURIComponent('Bibliothek/status.json') + '&t=' + Date.now(), { credentials: 'same-origin' });
      if (!r.ok) throw new Error('kein Bericht');
      d = await r.json();
    } catch (er) { $('#nb').innerHTML = '<div class="empty">Noch kein Statusbericht. Er entsteht täglich um 07:00, 13:00 und 19:00.</div>'; return; }
    const w = d.wichtig || {}, up = d.updates || {}, v = d.version || {}, s = d.system || {};
    const bad = (d.probleme || []).length;
    $('#nb').innerHTML =
      card('Status · ' + esc(d.stand || ''), bad ? '<span class="tag bad">' + bad + ' Hinweis(e)</span>' + ul(d.probleme) : '<span class="tag">alles in Ordnung</span>', bad ? 'nwarn' : '') +
      card('Wichtig', '<h3>Fristen diese Woche</h3>' + ul(w.fristen_woche) + '<h3>Bald</h3>' + ul(w.fristen_bald) +
        '<h3>Mails (Bericht vom ' + esc(w.mails_bericht_datum || '?') + ')</h3>' + ul(w.mails_bericht) +
        '<div class="sub">Eingang: ' + (d.eingang ? d.eingang.anzahl : 0) + ' Datei(en)</div>') +
      ((w.geplante_ergebnisse || []).length ? card('Ergebnisse geplanter Aufgaben', ul(w.geplante_ergebnisse.map(g => g.datei.replace(/\.md$/, '') + ' · vor ' + (g.alter_min < 90 ? g.alter_min + ' Min' : Math.round(g.alter_min / 60) + ' Std')))) : '') +
      card('Updates', '<div>' + (up.anzahl || 0) + ' Pakete aktualisierbar (' + (up.sicherheit || 0) + ' Sicherheit)' + (up.neustart_noetig ? ' · <span class="tag warn">Neustart nötig</span>' : '') + '</div>' + (up.beispiele && up.beispiele.length ? '<div class="sub">' + esc(up.beispiele.join(', ')) + '</div>' : '') +
        '<div class="mt">Portal: ' + esc(v.portal_laufend || '?') + (v.aktuell ? ' (aktuell)' : ' · Projekt hat ' + esc(v.portal_repo || '?') + ' <span class="tag warn">Einspielung offen</span>') + '</div>' +
        '<div class="sub">Brücke: ' + (v.bruecke_aktuell ? 'aktuell' : 'Einspielung offen') + '</div>') +
      card('Neu am System', ul((d.neues || []).map(n => n.titel + (n.text ? ': ' + n.text : '')))) +
      card('Offen (hohe Priorität)', ul((d.offen || []).map(o => o.id + ' ' + o.titel + ' — ' + o.status))) +
      card('Server', '<div>Laufzeit ' + esc(s.uptime_h) + ' h · RAM frei ' + esc(s.ram_frei_mb) + ' MB · Platte ' + esc(s.platte_belegt_prozent) + ' % belegt (' + esc(s.platte_frei_gb) + ' GB frei)</div><div class="sub">Wachhund ' + esc(s.wachhund_stand || '') + ': ' + esc(s.wachhund || '') + ' · Akku ' + esc(s.akku || '-') + '</div>' +
        '<div class="sub mt">' + Object.entries(d.dienste || {}).map(([k, x]) => esc(k) + ': ' + esc(x)).join(' · ') + '</div>');
  };
  $('#nrf').onclick = () => { draw(); toast('Aktualisiert'); };
  draw();
}

// Musik (Spotify-Ersatz ohne Abo): spielt Audiodateien aus Bibliothek/media/musik ueber /api/audio (spulbar). Der Player lebt ausserhalb der
// Ansicht, die Musik laeuft beim Wechsel der Reiter weiter; Sperrbildschirm-Steuerung ueber MediaSession. Wiedergabelisten liegen im Browser.
const MUS_ROOT = 'Bibliothek/media/musik';
const MUS_EXT = /\.(mp3|m4a|aac|ogg|oga|opus|flac|wav|webm)$/i;
const MUS = { a: new Audio(), q: [], i: -1, shuffle: false, repeat: 0, seeking: false, all: null };
MUS.a.preload = 'metadata';
const musName = p => p.split('/').pop().replace(MUS_EXT, '');
const musUrl = p => '/api/audio?path=' + encodeURIComponent(MUS_ROOT + '/' + p);
const musTime = s => isFinite(s) ? Math.floor(s / 60) + ':' + String(Math.floor(s % 60)).padStart(2, '0') : '0:00';
const musSave = () => { try { localStorage.setItem('ma.mus.q', JSON.stringify({ q: MUS.q, i: MUS.i, s: MUS.shuffle, r: MUS.repeat })); } catch (er) { /* Speicher voll: egal */ } };
try { const s = JSON.parse(localStorage.getItem('ma.mus.q') || '{}'); if (Array.isArray(s.q)) { MUS.q = s.q.filter(x => typeof x === 'string').slice(0, 2000); MUS.i = Math.min(+s.i || 0, MUS.q.length - 1); MUS.shuffle = !!s.s; MUS.repeat = +s.r || 0; } } catch (er) { /* kaputter Stand: leer starten */ }
const musPl = () => { try { return JSON.parse(localStorage.getItem('ma.mus.pl') || '{}'); } catch (er) { return {}; } };

function musRefresh() {
  const now = $('#mnow'); if (!now) return;
  const cur = MUS.q[MUS.i], a = MUS.a;
  now.innerHTML = cur ? '<b>' + esc(musName(cur)) + '</b><div class="sub">' + esc(cur.includes('/') ? cur.split('/').slice(0, -1).join(' / ') : 'Musik') + '</div>' : '<div class="sub">Nichts ausgewählt. Wähle unten einen Titel oder einen Ordner.</div>';
  $('#mplay').textContent = a.paused ? '▶' : '❚❚'; $('#mplay').setAttribute('aria-label', a.paused ? 'Abspielen' : 'Pause');
  $('#mshuf').classList.toggle('on', MUS.shuffle); $('#mrep').classList.toggle('on', MUS.repeat > 0); $('#mrep').textContent = MUS.repeat === 2 ? '↻1' : '↻';
  if (!MUS.seeking) { $('#mseek').value = a.duration ? Math.round(a.currentTime / a.duration * 1000) : 0; $('#mt1').textContent = musTime(a.currentTime); $('#mt2').textContent = musTime(a.duration); }
  const ql = $('#mqueue');
  if (ql && ql.dataset.n !== MUS.q.length + ':' + MUS.i) {
    ql.dataset.n = MUS.q.length + ':' + MUS.i;
    ql.innerHTML = MUS.q.length ? MUS.q.slice(0, 300).map((p, k) => '<div class="row mqrow' + (k === MUS.i ? ' cur' : '') + '" data-k="' + k + '"><div class="grow"><b>' + esc(musName(p)) + '</b></div><button class="btn small ghost" data-x="' + k + '" aria-label="Entfernen">×</button></div>').join('') + (MUS.q.length > 300 ? '<div class="sub">… und ' + (MUS.q.length - 300) + ' weitere</div>' : '') : '<div class="empty">Die Warteschlange ist leer.</div>';
  }
}
function musPlay(i, start = true) {
  if (i < 0 || i >= MUS.q.length) return;
  MUS.i = i; MUS.a.src = musUrl(MUS.q[i]); musSave();
  if ('mediaSession' in navigator) { try { navigator.mediaSession.metadata = new MediaMetadata({ title: musName(MUS.q[i]), artist: 'MA Home Musik' }); } catch (er) { /* alter Browser */ } }
  if (start) MUS.a.play().catch(() => toast('Wiedergabe nicht möglich (Format oder Verbindung)', 1));
  musRefresh();
}
function musStep(dir, auto) {
  const n = MUS.q.length; if (!n) return;
  let k;
  if (MUS.shuffle && n > 1) { do { k = Math.floor(Math.random() * n); } while (k === MUS.i); }
  else { k = MUS.i + dir; if (k >= n || k < 0) { if (MUS.repeat === 1 || !auto) k = (k + n) % n; else { MUS.a.pause(); MUS.a.currentTime = 0; musRefresh(); return; } } }
  musPlay(k);
}
function musToggle() {
  const a = MUS.a;
  if (!MUS.q.length) { toast('Erst einen Titel wählen'); return; }
  if (!a.src) { musPlay(Math.max(MUS.i, 0)); return; }
  a.paused ? a.play().catch(() => toast('Wiedergabe nicht möglich', 1)) : a.pause();
}
function musSet(list, start) { MUS.q = list.slice(0, 2000); musPlay(Math.max(0, Math.min(start || 0, MUS.q.length - 1))); }
MUS.a.addEventListener('ended', () => { if (MUS.repeat === 2) { MUS.a.currentTime = 0; MUS.a.play(); } else musStep(1, true); });
['play', 'pause', 'timeupdate', 'loadedmetadata'].forEach(ev => MUS.a.addEventListener(ev, musRefresh));
MUS.a.addEventListener('error', () => { if (MUS.a.src) toast('Datei lässt sich nicht abspielen: ' + (MUS.q[MUS.i] ? musName(MUS.q[MUS.i]) : ''), 1); });
if ('mediaSession' in navigator) {
  const ms = (k, f) => { try { navigator.mediaSession.setActionHandler(k, f); } catch (er) { /* nicht unterstuetzt */ } };
  ms('play', musToggle); ms('pause', musToggle); ms('previoustrack', () => musStep(-1)); ms('nexttrack', () => musStep(1));
}
// alle Audiodateien unter einem Ordner (tiefste Ebene begrenzt), Stand der Liste "rel" ist der Pfad unterhalb von MUS_ROOT
async function musWalk(rel, cap = 3000, out = []) {
  let d; try { d = await api('/api/files?path=' + encodeURIComponent(MUS_ROOT + (rel ? '/' + rel : ''))); } catch (er) { return out; }
  for (const e of d.entries) {
    if (out.length >= cap) break;
    if (e.directory) await musWalk((rel ? rel + '/' : '') + e.name, cap, out);
    else if (MUS_EXT.test(e.name)) out.push((rel ? rel + '/' : '') + e.name);
  }
  return out;
}
async function musik() {
  view.innerHTML = head('Musik', 'Deine eigene Musik ohne Abo, läuft beim Wechseln der Reiter weiter') +
    '<div class="card" id="mus"><div id="mnow" class="mnow"></div><input type="range" id="mseek" min="0" max="1000" value="0" aria-label="Position"><div class="mtime"><span id="mt1">0:00</span><span id="mt2">0:00</span></div>' +
    '<div class="mctl"><button class="btn ghost" id="mshuf" type="button" aria-label="Zufall">⇄</button><button class="btn ghost" id="mprev" type="button" aria-label="Zurück">⏮</button><button class="btn" id="mplay" type="button">▶</button><button class="btn ghost" id="mnext" type="button" aria-label="Weiter">⏭</button><button class="btn ghost" id="mrep" type="button" aria-label="Wiederholen">↻</button></div></div>' +
    '<div class="card mt"><div class="gtools"><input id="mq" placeholder="Suchen (Titel oder Ordner) …" autocomplete="off"></div><div class="crumbs" id="mcrumb"></div><div class="cacts" id="mact"></div><div id="mlist"><div class="empty">Lädt …</div></div></div>' +
    '<div class="card mt"><h2>Warteschlange</h2><div id="mqueue"></div><div class="cacts"><button class="btn small ghost" id="mclear" type="button">Leeren</button><button class="btn small ghost" id="msave" type="button">Als Liste speichern</button></div><h2 class="mt">Wiedergabelisten</h2><div id="mpl"></div></div>';
  $('#mplay').onclick = musToggle; $('#mprev').onclick = () => musStep(-1); $('#mnext').onclick = () => musStep(1);
  $('#mshuf').onclick = () => { MUS.shuffle = !MUS.shuffle; musSave(); musRefresh(); };
  $('#mrep').onclick = () => { MUS.repeat = (MUS.repeat + 1) % 3; musSave(); musRefresh(); };
  const sk = $('#mseek');
  sk.oninput = () => { MUS.seeking = true; $('#mt1').textContent = musTime(MUS.a.duration * sk.value / 1000); };
  sk.onchange = () => { if (MUS.a.duration) MUS.a.currentTime = MUS.a.duration * sk.value / 1000; MUS.seeking = false; };
  $('#mqueue').onclick = e => {
    const x = e.target.closest('[data-x]'), r = e.target.closest('.mqrow');
    if (x) { const k = +x.dataset.x; MUS.q.splice(k, 1); if (k < MUS.i) MUS.i--; else if (k === MUS.i) { MUS.a.pause(); MUS.a.removeAttribute('src'); MUS.i = Math.min(MUS.i, MUS.q.length - 1); } musSave(); $('#mqueue').dataset.n = ''; musRefresh(); }
    else if (r) musPlay(+r.dataset.k);
  };
  $('#mclear').onclick = () => { MUS.a.pause(); MUS.a.removeAttribute('src'); MUS.q = []; MUS.i = -1; musSave(); $('#mqueue').dataset.n = ''; musRefresh(); };
  const drawPl = () => {
    const pl = musPl(), names = Object.keys(pl);
    $('#mpl').innerHTML = names.length ? names.map(n => '<div class="row"><div class="grow"><b>' + esc(n) + '</b><span>' + pl[n].length + ' Titel</span></div><button class="btn small" data-pl="' + esc(n) + '" type="button">Abspielen</button><button class="btn small ghost" data-pd="' + esc(n) + '" type="button" aria-label="Liste löschen">×</button></div>').join('') : '<div class="sub">Noch keine gespeicherte Liste.</div>';
  };
  $('#msave').onclick = () => {
    if (!MUS.q.length) { toast('Die Warteschlange ist leer'); return; }
    const n = (prompt('Name der Liste') || '').trim().slice(0, 60); if (!n) return;
    const pl = musPl(); pl[n] = MUS.q.slice(); try { localStorage.setItem('ma.mus.pl', JSON.stringify(pl)); toast('Liste gespeichert'); } catch (er) { toast('Speichern nicht möglich', 1); }
    drawPl();
  };
  $('#mpl').onclick = e => {
    const b = e.target.closest('button'); if (!b) return;
    const pl = musPl();
    if (b.dataset.pl && pl[b.dataset.pl]) musSet(pl[b.dataset.pl], 0);
    if (b.dataset.pd && confirm('Liste „' + b.dataset.pd + '“ löschen?')) { delete pl[b.dataset.pd]; localStorage.setItem('ma.mus.pl', JSON.stringify(pl)); drawPl(); }
  };
  drawPl();
  let rel = '', timer = 0;
  const crumb = () => {
    const parts = rel ? rel.split('/') : [];
    $('#mcrumb').innerHTML = '<button type="button" data-r="">Musik</button>' + parts.map((p, k) => ' / <button type="button" data-r="' + esc(parts.slice(0, k + 1).join('/')) + '">' + esc(p) + '</button>').join('');
  };
  $('#mcrumb').onclick = e => { const b = e.target.closest('button[data-r]'); if (b) { $('#mq').value = ''; browse(b.dataset.r); } };
  async function browse(r) {
    rel = r; crumb();
    $('#mlist').innerHTML = '<div class="empty">Lädt …</div>'; $('#mact').innerHTML = '';
    const listNode = $('#mlist');
    const stillHere = () => listNode && listNode.isConnected && $('#mlist') === listNode;
    let d;
    try { d = await api('/api/files?path=' + encodeURIComponent(MUS_ROOT + (rel ? '/' + rel : ''))); }
    catch (er) { if (!stillHere()) return; $('#mlist').innerHTML = '<div class="empty">Noch keine Musik. Lege Musikdateien (mp3, m4a, flac, ogg, wav, opus) im Server-Ordner <code>/srv/ma-home/library/media/musik</code> ab, zum Beispiel über den Eingang oder die Dateien-Ansicht.</div>'; return; }
    if (!stillHere()) return;
    const dirs = d.entries.filter(e => e.directory), files = d.entries.filter(e => !e.directory && MUS_EXT.test(e.name));
    const base = rel ? rel + '/' : '';
    $('#mlist').innerHTML = (dirs.length || files.length) ? dirs.map(e => '<div class="row" data-d="' + esc(base + e.name) + '"><div class="ic c2">' + ico('files') + '</div><div class="grow"><b>' + esc(e.name) + '</b><span>Ordner</span></div></div>').join('') +
      files.map((e, k) => '<div class="row" data-f="' + k + '"><div class="grow"><b>' + esc(e.name.replace(MUS_EXT, '')) + '</b><span>' + fmtBytes(e.size) + '</span></div><button class="btn small ghost" data-add="' + k + '" type="button" aria-label="Zur Warteschlange">＋</button></div>').join('') : '<div class="empty">Dieser Ordner enthält keine Musik.</div>';
    $('#mact').innerHTML = (files.length || dirs.length) ? '<button class="btn small" id="mall" type="button">Ordner abspielen</button><button class="btn small ghost" id="mmix" type="button">Mischen (mit Unterordnern)</button>' : '';
    const paths = files.map(e => base + e.name);
    $('#mlist').onclick = e => {
      const add = e.target.closest('[data-add]'), f = e.target.closest('[data-f]'), dd = e.target.closest('[data-d]');
      if (add) { MUS.q.push(paths[+add.dataset.add]); musSave(); $('#mqueue').dataset.n = ''; musRefresh(); toast('In die Warteschlange gelegt'); }
      else if (f) musSet(paths, +f.dataset.f);
      else if (dd) browse(dd.dataset.d);
    };
    if ($('#mall')) $('#mall').onclick = async () => { const all = paths.length ? paths : await musWalk(rel, 500); if (!all.length) { toast('Keine Musik gefunden'); return; } MUS.shuffle = false; musSet(all, 0); };
    if ($('#mmix')) $('#mmix').onclick = async () => { const all = await musWalk(rel, 1000); if (!all.length) { toast('Keine Musik gefunden'); return; } MUS.shuffle = true; musSet(all, Math.floor(Math.random() * all.length)); };
  }
  $('#mq').oninput = () => {
    clearTimeout(timer);
    const q = $('#mq').value.trim().toLowerCase();
    if (q.length < 2) { browse(rel); return; }
    timer = setTimeout(async () => {
      $('#mlist').innerHTML = '<div class="empty">Suche …</div>';
      if (!MUS.all) MUS.all = await musWalk('', 3000);
      const hits = MUS.all.filter(p => p.toLowerCase().includes(q)).slice(0, 200);
      $('#mact').innerHTML = hits.length ? '<button class="btn small" id="mhall" type="button">Treffer abspielen</button>' : '';
      $('#mlist').innerHTML = hits.length ? hits.map((p, k) => '<div class="row" data-h="' + k + '"><div class="grow"><b>' + esc(musName(p)) + '</b><span>' + esc(p.includes('/') ? p.split('/').slice(0, -1).join(' / ') : 'Musik') + '</span></div></div>').join('') : '<div class="empty">Nichts gefunden.</div>';
      $('#mlist').onclick = e => { const h = e.target.closest('[data-h]'); if (h) musSet(hits, +h.dataset.h); };
      if ($('#mhall')) $('#mhall').onclick = () => musSet(hits, 0);
    }, 300);
  };
  musRefresh(); browse('');
}

// Reiter "Einstellungen": Anmeldung (Passkey/Code legt Authelia selbst an), Chat-Grenze, Version. Die Admin-Schalter bleiben im Reiter Claude (Code greift per ID zu).
async function einstellungen() {
  const row = (t, s, extra = '') => '<div class="row"><div><b>' + t + '</b><div class="sub">' + s + '</div></div>' + extra + '</div>';
  view.innerHTML = head('Einstellungen', 'Anmeldung, Claude-Chat und Portal') +
    '<div class="list">' +
    row('Anmeldung', 'Passkey ist serverseitig eingeschaltet. Ob du schon einen angelegt hast, zeigt die Seite dort. Im Menü oben links „Sicherheit“ wählen, dann Passkey oder Code (TOTP) hinzufügen.', '<a class="btn small ghost" href="/auth/settings" target="_blank" rel="noopener">Öffnen</a>') +
    row('Claude-Chat', 'Neuer Chat wird ab ' + fmtTok(CTX_MAX) + ' Kontext vorgeschlagen (fest eingestellt). Auto-Einspielung und Sudo-Schalter (nur Admin) stehen im Reiter Claude.') +
    row('Portal', 'Version ' + esc(VERSION) + (me.admin ? ' · Administrator' : ' · Benutzer')) +
    '</div>';
}

/* ---------- JARVIS V16 (Aufträge, Fortschritt, Freigaben, Ergebnisse; dieselbe Steuerung wie jarvis_cli.py und der PC-Client) ---------- */
const JV_STATE = { queued: 'wartet', planning: 'plant', running: 'läuft', waiting_approval: 'braucht Freigabe', waiting_pc: 'wartet auf PC', done: 'erledigt', partial: 'teilweise', failed: 'fehlgeschlagen', cancelled: 'abgebrochen' };
const JV_FINAL = ['done', 'partial', 'failed', 'cancelled'];
const jv = (cmd, extra = {}) => api('/api/jarvis', { body: { cmd, ...extra } }).then(r => { if (!r.ok) throw new Error(r.error || (r.data && r.data.error) || 'JARVIS-Fehler'); return r.data; });
let jvTimer, jvVis = false, jarvisTick = null;
async function jarvis() {
  clearTimeout(jvTimer);
  if (!me.admin) { view.innerHTML = head('JARVIS') + '<div class="empty">Nur für Administratoren.</div>'; return; }
  let sel = new URLSearchParams(location.hash.split('?')[1] || '').get('j') || '', cursor = 0, evs = [];
  view.innerHTML = head('JARVIS', 'Aufträge an den Server-Kern. Er arbeitet im Takt von einer Minute, nicht im Chat.') + `
  <div class="card"><h2>${ico('claude')} Neuer Auftrag</h2><form id="jvf"><textarea name="r" maxlength="8000" placeholder="Was soll JARVIS erledigen? (Ergebnisse landen unter Bibliothek/JARVIS)" style="min-height:84px"></textarea><div class="mt"><button class="btn">${ico('send')} Starten</button></div></form></div>
  <div class="card mt"><h2>Zustand</h2><div id="jvst" class="pills"></div></div>
  <div class="card mt"><h2>Agenten &amp; Watchdog</h2><div id="jvag">…</div><div id="jvinc" class="mt"></div></div>
  <!-- jvagents-a5-2 -->
  <div class="card mt"><h2>Aufträge</h2><div class="list" id="jvlist"></div></div>
  <div id="jvdet"></div>
  <details class="card mt" id="jvmore"><summary class="sub">Fähigkeiten und Gelerntes</summary><div id="jvmb" class="mt"></div></details>`;
  const alive = () => location.hash.startsWith('#/jarvis') && view.querySelector('#jvlist');
  const pill = s => `<span class="pill ${s === 'done' ? 'dot' : s === 'failed' || s === 'cancelled' ? 'dot off' : ''}">${esc(JV_STATE[s] || s)}</span>`;
  const when = t => t ? new Date(t * 1000).toLocaleString('de-DE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '';
  async function usage() {
    const u = await jv('usage'), l = u.ledger.claude;
    $('#jvst').innerHTML = `<span class="pill">Claude-Aufrufe ${l.calls_24h}/${l.limits.calls_per_day} (24 h)</span><span class="pill">Token ${Math.round(l.tokens_24h / 1000)}k/${Math.round(l.limits.tokens_per_day / 1000)}k</span>` +
      (u.ledger.plan_block ? `<span class="pill dot off">Plan-Schutz: ${esc(String(u.ledger.plan_block).slice(0, 60))}</span>` : '') +
      `<button class="btn small ghost" id="jvkill">Not-Aus</button><button class="btn small ghost" id="jvlive">Not-Aus aufheben</button>`;
    $('#jvkill').onclick = async () => { if (confirm('Not-Aus: keine neuen Aufträge, laufende werden nicht fortgesetzt. Sicher?')) { try { await jv('kill', { state: 'on' }); toast('Not-Aus gesetzt'); } catch (er) { toast(er.message, 1); } } };
    $('#jvlive').onclick = async () => { try { await jv('kill', { state: 'off' }); toast('Not-Aus aufgehoben'); } catch (er) { toast(er.message, 1); } };
  }
  async function list() {
    const { jobs } = await jv('list', { limit: 15 });
    $('#jvlist').innerHTML = jobs.length ? jobs.map(j => `<div class="row ${j.id === sel ? 'l2' : ''}" data-j="${esc(j.id)}" style="cursor:pointer"><div class="grow"><b>${esc(j.request)}</b><span>${when(j.created)} · ${j.claude_calls} Aufr. · ${Math.round(j.tokens_new / 1000)}k Token</span></div>${pill(j.state)}</div>`).join('') : '<div class="empty">Noch keine Aufträge.</div>';
    return jobs;
  }
  async function detail() {
    const box = $('#jvdet'); if (!sel) { box.innerHTML = ''; return null; }
    const st = await jv('status', { job: sel });
    const ev = await jv('events', { job: sel, since: cursor });
    if (ev.events.length) { evs = evs.concat(ev.events); cursor = evs[evs.length - 1].id; }
    const fin = JV_FINAL.includes(st.state);
    let files = '';
    if (fin) { const r = await jv('result', { job: sel }); files = r.files.map(f => `<button class="chip" data-f="${esc(f)}">${esc(f)}</button>`).join(''); }
    const waiting = (st.steps || []).filter(s => s.state === 'waiting');
    const revs = st.revisions || [];
    box.innerHTML = `<div class="card mt"><h2>${esc(st.id)} ${pill(st.state)} <span class="chip" title="Jede Änderung erzeugt eine neue Revision; die Auftragsnummer bleibt">Rev. ${esc(String(st.revision || 1))}</span></h2>
      <div class="sub">${esc(st.request || '')}</div>${st.summary ? `<div class="mt"><b>${esc(st.summary)}</b></div>` : ''}
      ${st.attribution && fin ? `<div class="mt sub" id="jvattr" title="Herkunft laut Ausführungsprotokoll (Schritte, Modellaufrufe, Ereignisse)">${esc(st.attribution.line)}</div>` : ''}
      <div class="list mt">${(st.steps || []).map(s => `<div class="row"><div class="grow"><b>${esc(s.title)}</b><span>${esc(s.kind)}${s.capability ? ' · ' + esc(s.capability) : ''}${s.detail ? ' · ' + esc(String(s.detail).split('\n')[0].slice(0, 90)) : ''}</span></div>${pill(s.state === 'waiting' ? 'waiting_approval' : s.state)}</div>`).join('')}</div>
      ${st.state === 'waiting_approval' ? `<div class="mt"><div class="sub">${(st.effects || []).length ? 'Geplante Wirkung: ' + esc(JSON.stringify(st.effects).slice(0, 300)) : 'Der Auftrag wartet auf deine Freigabe.'}</div><input id="jvans" placeholder="${waiting.length ? 'Antwort auf die Rückfrage (erforderlich)' : 'Hinweis (optional)'}" class="mt"><div class="mt"><button class="btn" id="jvok">Freigeben</button></div></div>` : ''}
      ${revs.length > 1 ? `<details class="mt"><summary class="sub">Änderungen (${revs.length - 1})</summary><div class="list mt">${revs.slice(1).map(v => `<div class="row"><div class="grow"><b>Rev. ${esc(String(v.revision))}</b><span>${esc(v.change)} · ${esc(v.by)} · ${when(v.created)}</span></div></div>`).join('')}</div></details>` : ''}
      ${!fin ? `<div class="mt"><textarea id="jvrev" rows="2" maxlength="8000" placeholder="Auftrag ändern, z. B. „nimm Java 25 und teste erneut“ – Nummer bleibt, Plan wird neu erstellt"></textarea><div class="mt"><button class="btn small" id="jvrevok">Ändern</button> <button class="btn small ghost" id="jvno">Abbrechen</button></div></div>` : ''}
      ${files ? `<div class="mt sub">Ergebnisse</div><div class="chips mt">${files}</div>` : ''}
      <details class="mt"><summary class="sub">Verlauf (${evs.length})</summary><div class="sub mt" style="white-space:pre-wrap">${evs.slice(-60).map(e => `${when(e.ts)} ${esc(e.kind)}: ${esc(e.text)}`).join('\n')}</div></details></div>`;
    const ok = $('#jvok'); if (ok) ok.onclick = async () => { try { if (waiting.length && !$('#jvans').value.trim()) { toast('Bitte die Rückfrage beantworten', 1); return; } for (const s of waiting.length ? waiting : [{}]) await jv('approve', { job: sel, step: s.sid || '', answer: $('#jvans').value }); toast(waiting.length ? 'Antwort gesendet' : 'Freigegeben'); tick(true); } catch (er) { toast(er.message, 1); } };
    const rv = $('#jvrevok'); if (rv) rv.onclick = async () => { const ch = $('#jvrev').value.trim(); if (ch.length < 3) { toast('Bitte beschreiben, was sich ändern soll', 1); return; } if (!confirm('Auftrag ändern? Offene Schritte werden neu geplant, erstellte Dateien bleiben.')) return; try { const r = await jv('revise', { job: sel, request: ch, expected: st.revision || 1 }); toast('Geändert: Revision ' + r.revision); evs = []; cursor = 0; tick(true); } catch (er) { toast(er.message, 1); } };
    const no = $('#jvno'); if (no) no.onclick = async () => { if (!confirm('Auftrag abbrechen?')) return; try { await jv('cancel', { job: sel }); toast('Abgebrochen'); tick(true); } catch (er) { toast(er.message, 1); } };
    box.querySelectorAll('[data-f]').forEach(b => { b.onclick = () => openViewer('Bibliothek/JARVIS/' + sel + '/' + b.dataset.f, b.dataset.f.split('/').pop()); });
    return st;
  }
  async function agentsView() {
    const box = $('#jvag'); if (!box) return;
    try {
      const r = await fetch('/api/jarvis/agents', { credentials: 'same-origin' });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const d = await r.json();
      const mins = iso => { const s = (Date.now() - new Date(iso).getTime()) / 60000; return !isFinite(s) ? '?' : s < 2 ? 'jetzt' : s < 60 ? Math.round(s) + ' min' : Math.round(s / 60) + ' h'; };
      const hb = (d.agents || []).map(a => { const t = (d.tasks || {})[a.agent] || { active: 0, total: 0 }; const stale = (Date.now() - new Date(a.last_heartbeat).getTime()) > 10 * 60000; return `<div class="row"><div class="grow"><b>${esc(a.agent)}</b><span>${esc(a.status)} · Herzschlag vor ${mins(a.last_heartbeat)}${t.total ? ' · Tasks aktiv ' + t.active + ' von ' + t.total : ''}</span></div><span class="pill ${stale ? 'dot off' : 'dot'}">${stale ? 'still' : 'aktiv'}</span></div>`; }).join('');
      const eng = (d.engine && d.engine.active || []).map(j => `<div class="row"><div class="grow"><b>${esc(j.id)}</b><span>${Math.round((j.tokens_new || 0) / 1000)}k Token</span></div>${pill(j.state)}</div>`).join('');
      box.innerHTML = (hb || '<div class="empty">Keine Agenten-Meldungen.</div>') + (eng ? `<div class="sub mt">Engine-Aufträge</div>` + eng : '') + ((d.engine && d.engine.error) ? `<div class="sub mt">Engine: ${esc(d.engine.error)}</div>` : '');
      const inc = $('#jvinc');
      inc.innerHTML = (d.incidents || []).length ? `<div class="sub">Watchdog-Incidents (offen)</div><div class="list mt">` + d.incidents.map(i => `<div class="row"><div class="grow"><b>${esc(i.classification)}</b><span>${esc(i.subject)} · seit ${i.age_min} min</span></div><span class="pill dot off">${esc(i.adapter)}</span></div>`).join('') + '</div>' : '<div class="sub mt">Watchdog: keine offenen Incidents.</div>';
    } catch (er) { box.innerHTML = `<div class="empty">${esc(er.message)}</div>`; }
  }

  // Abfrage nur solange der Reiter offen und sichtbar ist und ein Auftrag noch läuft: spart Last und Token auf dem Server.
  // Jeder Aufruf startet auf dem Server einen Python-Prozess (ca. 0,35 s CPU): Liste und Verbrauch deshalb nur beim Öffnen, nach Aktionen und alle 5. Runde.
  let n = 0;
  async function tick(once) {
    clearTimeout(jvTimer);
    if (!alive()) return;
    let busy = false;
    try {
      const full = once || n++ % 5 === 0;
      const st = await detail();
      const jobs = full || !st ? await list() : null;
      if (full) await usage();
      if (full) await agentsView();
      busy = (st && !JV_FINAL.includes(st.state)) || (jobs || []).some(j => !JV_FINAL.includes(j.state)) || (!jobs && !st);
    } catch (er) { toast(er.message, 1); }
    if (busy && !document.hidden) jvTimer = setTimeout(() => tick(), 6000);
    else if (!once) jvTimer = setTimeout(() => tick(true), 30000);
  }
  if (!jvVis) { jvVis = true; document.addEventListener('visibilitychange', () => { if (!document.hidden && location.hash.startsWith('#/jarvis') && jarvisTick) jarvisTick(true); }); }
  jarvisTick = tick;
  const rid = () => (self.crypto && crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random().toString(16).slice(2)).replace(/[^A-Za-z0-9_.-]/g, '').slice(0, 40);
  let key = rid();
  $('#jvf').onsubmit = async e => {
    e.preventDefault(); const t = String(new FormData(e.target).get('r')).trim(); if (!t) return;
    try { const r = await jv('submit', { request: t, client_id: key }); key = rid(); e.target.reset(); sel = r.job_id || ''; cursor = 0; evs = []; toast('Auftrag übergeben'); tick(true); } catch (er) { toast(er.message, 1); }
  };
  view.onclick = e => { const r = e.target.closest('[data-j]'); if (r) { sel = r.dataset.j; cursor = 0; evs = []; history.replaceState(null, '', '#/jarvis?j=' + sel); tick(true); } };
  $('#jvmore').addEventListener('toggle', async ev => {
    if (!ev.target.open) return;
    try {
      const [caps, learned] = await Promise.all([jv('caps'), jv('learned')]);
      const tpl = learned.templates || learned.vorlagen || [], les = learned.lessons || [];
      $('#jvmb').innerHTML = `<div class="chips">${caps.caps.map(c => `<span class="chip" title="${esc((c.title || '') + ' (' + (c.host || '') + ')')}">${esc(c.name)} · ${esc(c.status)}</span>`).join('')}</div>` +
        `<div class="sub mt">Gelernte Vorlagen: ${tpl.length} · Lehren: ${les.length}. Löschen: <code>jarvis forget template|lesson ID</code> (CLI) oder POST /api/jarvis {cmd:"forget"}.</div>`;
    } catch (er) { $('#jvmb').textContent = er.message; }
  });
  tick();
}

/* ---- Exporte: je Ansicht das Wurzelelement setzen, dann die Bestandsfunktion starten ---- */
export const renderNeu = r => { view = r; return neu(); };
export const renderMusik = r => { view = r; return musik(); };
export const renderEinstellungen = r => { view = r; return einstellungen(); };
export const renderWissen = r => { view = r; return wissen(); };
export const renderVault = r => { view = r; return vault(); };
export const renderJarvis = r => { view = r; return jarvis(); };
