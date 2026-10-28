/* MA-HOME HQ — Shell: Router, Navigation, Command Palette, Favoriten, Legacy-Fallback (M2) */
import { $, $$, esc, api, toast } from './api.js';
import { renderChat, chatUi } from './chat.js';
import { renderHQ, leaveHQ } from './hq.js';
import { renderCC, leaveCC } from './cc.js';
import { renderVoice, leaveVoice, mountVoiceButton } from './voiceui.js';
import { initVoice } from './voice.js';
import { mountInstall } from './install.js';
import { setMe, renderNeu, renderMusik, renderEinstellungen, renderWissen, renderVault, renderJarvis } from './port.js';
import { closeViewer } from './viewer.js';
import * as V from './views.js';

let me = { user: '', admin: false, domain: '' };
let current = 'dashboard';

/* --- View-Registry: nativ (M2) vs. Legacy-Einbettung (Zwischenstand, keine Funktionsverluste) --- */
const NATIV = {
  dashboard: { label: 'Kommandozentrale', ico: '◈', render: (r, c) => V.renderDashboard(r, c) },
  chat:      { label: 'JARVIS-Chat',      ico: '✦', render: (r) => renderChat(r, me) },
  hq:        { label: 'Living HQ',        ico: '▣', render: (r, c) => renderHQ(r, c) },
  cc:        { label: 'Command Center',   ico: '⌬', render: (r, c) => renderCC(r, c) },
  voice:     { label: 'Sprache',          ico: '🎤', render: (r, c) => renderVoice(r, c) },
  tasks:     { label: 'Aufgaben',         ico: '☑', render: (r) => V.renderTasks(r, { go }) },
  notes:     { label: 'Notizen',          ico: '✎', render: (r) => V.renderNotes(r) },
  money:     { label: 'Geld',             ico: '€', render: (r) => V.renderMoney(r) },
  training:  { label: 'Training',         ico: '♦', render: (r) => V.renderTraining(r) },
  files:     { label: 'Dateien',          ico: '▤', render: (r) => V.renderFiles(r) },
  term:      { label: 'Terminal',         ico: '>_', render: (r) => V.renderTerm(r) },
  status:    { label: 'System',           ico: '♥', render: (r, c) => V.renderSystem(r, c) },
  verbindungen: { label: 'Verbindungen',  ico: '⇄', render: (r) => V.renderVerbindungen(r) },
  jarvis:    { label: 'JARVIS-Aufträge',  ico: '⚑', render: (r) => renderJarvis(r) },
  neu:       { label: 'Neu',              ico: '✳', render: (r) => renderNeu(r) },
  vault:     { label: 'Vault',            ico: '▦', render: (r) => renderVault(r) },
  wissen:    { label: 'Wissen',           ico: '◎', render: (r) => renderWissen(r) },
  musik:     { label: 'Musik',            ico: '♪', render: (r) => renderMusik(r) },
  einstellungen: { label: 'Einstellungen', ico: '⚒', render: (r) => renderEinstellungen(r) }
};
const LEGACY = {};   // alle Bestandsbereiche sind nativ portiert; Embed-Pfad bleibt als Fallback (/classic/)
const LOCKED = {};
const GROUPS = [
  ['Bereiche', ['dashboard', 'chat', 'voice', 'jarvis', 'hq', 'cc']],
  ['Daten', ['tasks', 'notes', 'money', 'training', 'files', 'term']],
  ['System', ['status', 'verbindungen', 'neu']],
  ['Wissen', ['vault', 'wissen']],
  ['Extras', ['musik', 'einstellungen', 'designsystem']]
];
const ALL_LABELS = {};
Object.entries(NATIV).forEach(([k, v]) => ALL_LABELS[k] = v.label);
Object.entries(LEGACY).forEach(([k, v]) => ALL_LABELS[k] = v.label);
Object.entries(LOCKED).forEach(([k, v]) => ALL_LABELS[k] = v[0]);
ALL_LABELS.designsystem = 'Design-System';

function label(v) { return ALL_LABELS[v] || v; }

/* --- Favoriten (lokal, SPEC: Favoriten/Schnellzugriff) --- */
const FKEY = 'hq-favs';
const getFavs = () => { try { return JSON.parse(localStorage.getItem(FKEY) || '[]'); } catch (e) { return []; } };
const setFavs = f => { try { localStorage.setItem(FKEY, JSON.stringify(f)); } catch (e) { /* */ } renderNav(); };

/* --- Navigation bauen --- */
function renderNav() {
  const nav = $('#nav');
  const favs = getFavs().filter(f => ALL_LABELS[f]);
  let html = '';
  if (favs.length) {
    html += '<div class="nav-group">Favoriten</div>' + favs.map(f =>
      '<button class="nav-item' + (f === current ? ' active' : '') + '" data-view="' + f + '"><span class="ico">★</span>' + esc(label(f)) + '</button>').join('');
  }
  GROUPS.forEach(([g, vs]) => {
    html += '<div class="nav-group">' + g + '</div>' + vs.map(v => {
      if (LOCKED[v]) return '<button class="nav-item locked" data-view="' + v + '"><span class="ico">' + LOCKED[v][1] + '</span>' + LOCKED[v][0] + '<span class="tag">' + LOCKED[v][2] + '</span></button>';
      const ico = (NATIV[v] && NATIV[v].ico) || (LEGACY[v] && LEGACY[v].ico) || '◐';
      const leg = LEGACY[v] ? '<span class="tag">klassisch</span>' : '';
      return '<button class="nav-item' + (v === current ? ' active' : '') + '" data-view="' + v + '"><span class="ico">' + ico + '</span>' + esc(label(v)) + leg + '</button>';
    }).join('');
  });
  nav.innerHTML = html;
  $$('.nav-item', nav).forEach(b => b.onclick = () => activate(b.dataset.view));
}

/* --- Router --- */
function go(view, opts) {
  if (opts && typeof opts.filesPath === 'string') V.setFilesPath(opts.filesPath);
  activate(view);
}
function activate(view) {
  if (LOCKED[view]) { openPalette(); return; }
  leaveHQ();                       // Living-HQ-Polling/Animation beenden, sobald die Ansicht verlassen wird
  leaveCC(); leaveVoice();
  current = view;
  if (!location.hash.startsWith('#/' + view)) { try { history.replaceState(null, '', location.pathname + '#/' + view); } catch (e) { /* */ } }   // Parameter (?p=…) bleiben erhalten
  $$('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.view === view));
  $$('#tabbar [data-tab]').forEach(b => { const on = b.dataset.tab === view; b.classList.toggle('active', on); if (on) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current'); });
  closeSheet();
  $('#view-title').textContent = label(view);
  const host = $('#view');
  try { closeViewer(); } catch (e) { /* kein Viewer offen */ }
  host.onclick = null;                // Handler der vorigen Ansicht nicht mitschleppen
  const ds = $('#static-designsystem');
  if (view === 'designsystem') { host.innerHTML = ''; host.hidden = true; ds.hidden = false; return; }
  ds.hidden = true; host.hidden = false;
  if (LEGACY[view]) {
    host.innerHTML = '<div class="legacy-note">Zwischenstand: „' + esc(label(view)) + '“ läuft hier als eingebettete klassische Ansicht — native Portierung folgt.</div>' +
      '<div class="legacy-wrap"><iframe src="/classic/#/' + view + '" title="' + esc(label(view)) + ' (klassisch)"></iframe></div>';
    const fr = host.querySelector('iframe');
    // Gleiche Origin: Alt-Navigation im Frame ausblenden, damit nur der Inhalt erscheint (kein doppeltes Menü)
    fr.addEventListener('load', () => {
      try {
        const d = fr.contentDocument, st = d.createElement('style');
        st.textContent = '.side{display:none!important}.shell{grid-template-columns:1fr!important}main{max-width:none!important}';
        d.head.appendChild(st);
      } catch (e) { /* fremde Origin: Frame bleibt unverändert */ }
    });
    return;
  }
  host.innerHTML = '<div class="skeleton"></div>';
  const def = NATIV[view];
  if (def) Promise.resolve(def.render(host, { me, go })).catch(er => { host.innerHTML = '<div class="empty">' + esc(er.message) + '</div>'; });
  else host.innerHTML = '<div class="empty">Unbekannte Ansicht.</div>';
}

/* --- Command Palette --- */
let backdrop, input, list, activeIdx = 0;
function actions() {
  const acts = [];
  Object.keys(ALL_LABELS).forEach(v => {
    const favs = getFavs();
    const isFav = favs.includes(v);
    acts.push({
      label: label(v), ico: (NATIV[v] && NATIV[v].ico) || (LEGACY[v] && LEGACY[v].ico) || (LOCKED[v] && LOCKED[v][1]) || '·',
      hint: (LEGACY[v] ? 'klassisch · ' : '') + (isFav ? '★ Favorit (entfernen: Ctrl+Klick)' : 'Favorit merken: Ctrl+Klick'),
      run: () => { if (LOCKED[v]) { openPalette(); return; } activate(v); },
      star: () => { const f = getFavs(); const i = f.indexOf(v); if (i >= 0) f.splice(i, 1); else f.push(v); setFavs(f); toast((i >= 0 ? 'Favorit entfernt: ' : 'Als Favorit gemerkt: ') + label(v)); }
    });
  });
  acts.push({ label: 'Neuer Chat', ico: '✦', hint: 'Aktion', run: () => { activate('chat'); chatUi.fresh(); } });
  acts.push({ label: 'Verläufe öffnen', ico: '✦', hint: 'Aktion', run: () => { activate('chat'); chatUi.sessionsOpen(); } });
  acts.push({ label: 'Geplante Aufgaben', ico: '✦', hint: 'Aktion', run: () => { activate('chat'); chatUi.schedOpen(); } });
  acts.push({ label: 'Chat teilen / kopieren', ico: '✦', hint: 'Aktion', run: () => { activate('chat'); chatUi.claudeExport(); } });
  return acts;
}
function renderPalette(filter) {
  const q = (filter || '').toLowerCase();
  const acts = actions().filter(a => a.label.toLowerCase().indexOf(q) !== -1);
  list.innerHTML = '';
  if (!acts.length) { list.innerHTML = '<li class="empty">Kein Treffer</li>'; list._acts = []; return; }
  activeIdx = 0;
  acts.forEach((a, i) => {
    const li = document.createElement('li');
    if (i === 0) li.className = 'active';
    li.innerHTML = '<span class="ico">' + a.ico + '</span><span>' + esc(a.label) + '</span><span class="hint">' + esc(a.hint) + '</span>';
    li.addEventListener('click', e => { if (e.ctrlKey || e.metaKey) { a.star(); renderPalette(input.value); return; } closePalette(); a.run(); });
    li.addEventListener('mousemove', () => { activeIdx = i; $$('li', list).forEach((c, j) => c.classList.toggle('active', j === i)); });
    list.appendChild(li);
  });
  list._acts = acts;
}
function openPalette() { backdrop.classList.add('open'); input.value = ''; renderPalette(''); setTimeout(() => input.focus(), 30); }
function closePalette() { backdrop.classList.remove('open'); }

function wirePalette() {
  backdrop = $('#palette'); input = $('#palette-input'); list = $('#palette-list');
  $('#palette-open').onclick = openPalette;
  backdrop.addEventListener('click', e => { if (e.target === backdrop) closePalette(); });
  input.addEventListener('input', () => renderPalette(input.value));
  input.addEventListener('keydown', e => {
    const lis = $$('li', list);
    if (e.key === 'Escape') closePalette();
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (!lis.length || lis[0].classList.contains('empty')) return;
      activeIdx = e.key === 'ArrowDown' ? (activeIdx + 1) % lis.length : (activeIdx - 1 + lis.length) % lis.length;
      lis.forEach((c, j) => c.classList.toggle('active', j === activeIdx));
      lis[activeIdx].scrollIntoView({ block: 'nearest' });
    }
    if (e.key === 'Enter' && list._acts && list._acts.length) { closePalette(); list._acts[activeIdx].run(); }
  });
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); openPalette(); }
  });
}

/* --- Design-System-Swatches (statische Ansicht) --- */
function wireSwatches() {
  const TOKENS = [
    ['--bg-deep', 'Basis tief'], ['--bg-panel', 'Panel'], ['--bg-elev', 'Erhoben'],
    ['--crimson', 'Crimson (Aktiv/Gefahr)'], ['--crimson-deep', 'Crimson tief'], ['--cyan', 'Cyan (System/OK)'],
    ['--greige', 'Greige (neutral)'], ['--sand', 'Sand (Pergament)'], ['--text', 'Text'], ['--text-muted', 'Text gedimmt'],
    ['--ok', 'OK'], ['--warn', 'Warnung']
  ];
  const sw = $('#swatches');
  if (!sw) return;
  TOKENS.forEach(t => {
    const val = getComputedStyle(document.documentElement).getPropertyValue(t[0]).trim();
    const cell = document.createElement('div');
    cell.className = 'holo';
    cell.style.padding = '12px';
    cell.innerHTML = '<div style="height:34px;border-radius:4px;border:1px solid var(--line);background:' + val + '"></div>' +
      '<div class="mono" style="font-size:11px;margin-top:8px">' + t[0] + '</div>' +
      '<div class="mono faint" style="font-size:10px">' + val + '</div>' +
      '<div class="faint" style="font-size:10px;margin-top:2px">' + t[1] + '</div>';
    sw.appendChild(cell);
  });
}

/* --- Mobile Schnellnavigation (<= 720 px): untere Tab-Leiste mit 4 Zielen + "Mehr" (öffnet das vollständige Menü als Vollbild-Blatt) --- */
function closeSheet() {
  document.body.classList.remove('nav-open');
  const m = $('#tab-more'); if (m) m.setAttribute('aria-expanded', 'false');
}
function toggleSheet() {
  const open = !document.body.classList.contains('nav-open');
  document.body.classList.toggle('nav-open', open);
  const m = $('#tab-more'); if (m) m.setAttribute('aria-expanded', String(open));
  if (open) { const f = $('#nav .nav-item'); if (f) f.focus(); }
}
function mountTabbar() {
  const tb = document.createElement('nav');
  tb.id = 'tabbar'; tb.setAttribute('aria-label', 'Schnellnavigation');
  const items = [['dashboard', '⌂', 'Zentrale'], ['chat', '✎', 'Chat'], ['tasks', '☑', 'Aufgaben'], ['hq', '◈', 'Agenten']];
  tb.innerHTML = items.map(([v, i, l]) => '<button type="button" data-tab="' + v + '"><span class="ti" aria-hidden="true">' + i + '</span><span class="tl">' + l + '</span></button>').join('') +
    '<button type="button" id="tab-more" aria-expanded="false" aria-controls="nav"><span class="ti" aria-hidden="true">☰</span><span class="tl">Mehr</span></button>';
  document.body.appendChild(tb);
  tb.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.id === 'tab-more') toggleSheet(); else activate(b.dataset.tab);
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && document.body.classList.contains('nav-open')) { closeSheet(); const m = $('#tab-more'); if (m) m.focus(); } });
  // Bildschirmtastatur: Tab-Leiste ausblenden, solange ein Eingabefeld fokussiert ist (Eingabefeld bleibt sichtbar)
  const isField = t => t && /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName);
  document.addEventListener('focusin', e => { if (isField(e.target) && matchMedia('(max-width: 720px), (max-height: 500px)').matches) document.body.classList.add('kb'); });
  document.addEventListener('focusout', () => { setTimeout(() => { if (!isField(document.activeElement)) document.body.classList.remove('kb'); }, 50); });
}

/* --- Boot --- */
(async function boot() {
  wirePalette();
  wireSwatches();
  renderNav();
  mountTabbar();
  mountVoiceButton($('.topbar'), go);
  mountInstall($('.topbar'), toast);
  initVoice(v => go(v));
  try { me = await api('/api/me'); setMe(me); } catch (e) { /* Gast: Admin-Schalter bleiben aus */ }
  // Teilen-Menue (PWA share_target, GET /?title=&text=&url=): geteilter Text/Link landet als Entwurf im Chat
  try {
    const sp = new URLSearchParams(location.search), shared = ['title', 'text', 'url'].map(k => sp.get(k)).filter(Boolean).join('\n');
    if (shared) { sessionStorage.setItem('ma-claude-draft', shared.slice(0, 4000)); history.replaceState(null, '', location.pathname + '#/chat'); }
  } catch (e) { /* ohne Speicher */ }
  routeFromHash();
  window.addEventListener('hashchange', routeFromHash);
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => { /* PWA optional */ });
})();

/* Alte Lesezeichen/Links (#/claude, #/home, #/files?p=…) auf die neuen Ansichten abbilden */
function routeFromHash() {
  const ALIAS = { home: 'dashboard', claude: 'chat', system: 'status' };
  const raw = (location.hash.match(/^#\/([a-z]+)/) || [])[1] || 'dashboard';
  let v = ALIAS[raw] || raw;
  if (!ALL_LABELS[v] || LOCKED[v]) v = 'dashboard';
  if (v === 'files') { const p = new URLSearchParams(location.hash.split('?')[1] || '').get('p'); if (p) V.setFilesPath(p); }
  activate(v);
}
