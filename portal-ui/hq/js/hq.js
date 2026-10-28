/* MA-HOME HQ — Living HQ (M3): Canvas-2D-Welt aus echten JARVIS-Daten.
   Regeln (SPEC §10): Zustaende nur aus API-Daten (Tasks, Heartbeats, Incidents, Engine); Bewegungen nur durch echte
   Zustandsaenderungen; keine LLM-Token; clientseitig; adaptive Qualitaet. Dekoration (Atmen, LED-Ruhelicht) ist kein Aktivitaetsnachweis. */
import { $, esc } from './api.js';
import { subscribe, S, isFresh, shortName } from './store.js';
import { W, Hh, ROOMS, ROSTER, SYSTEM, slots } from './roster.js';

let stopFn = null;
export function leaveHQ() { if (stopFn) { stopFn(); stopFn = null; } }

const RE_WORK = /ACTIVE|RUNNING|IN_?PROGRESS|WORKING/i;
const RE_PLAN = /PLANNING|INBOX|PENDING|QUEUED|READY/i;
const RE_DONE = /^(?:DONE|COMPLETE|COMPLETED|CLOSED|CANCELLED|CANCELED|ARCHIVED|FAILED)$/i;
const hexA = (hex, a) => { const n = parseInt(hex.slice(1), 16); return 'rgba(' + (n >> 16) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')'; };
const hhmmss = t => new Date(t).toLocaleTimeString('de-DE');
const ago = iso => { const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000); return s < 90 ? Math.round(s) + ' s' : s < 5400 ? Math.round(s / 60) + ' min' : s < 172800 ? Math.round(s / 3600) + ' Std' : Math.round(s / 86400) + ' Tg'; };

export function renderHQ(root, ctx) {
  leaveHQ();
  const reduced = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  root.innerHTML =
    '<div class="top"><div><h1>Living HQ</h1><div class="sub">Echte Zustände aus Tasks, Heartbeats, Incidents und Engine – keine simulierte KI-Aktivität</div></div></div>' +
    '<div class="hq-chips" id="hqchips"></div>' +
    '<div class="hq-layout"><div class="hq-stage" id="hqstage"><canvas id="hqc" aria-label="Living HQ: Agentenwelt"></canvas>' +
    '<div class="hq-drawer" id="hqd" hidden></div></div>' +
    '<aside class="hq-feed holo"><h2 class="holo-title">Ereignisse<span class="sub">nur Änderungen seit Seitenaufruf</span></h2><ul id="hqfeed"></ul>' +
    '<h2 class="holo-title" style="margin-top:16px">Engine<span class="sub">letzte Jobs</span></h2><ul id="hqjobs"></ul></aside></div>' +
    '<p class="faint hq-note">Zustand = Daten aus <span class="mono">/api/jarvis/{agents,tasks}</span> und normalisierten V16-Engine-Ereignissen (<span class="mono">cmd activity</span>; Poll 2–5 s). Figuren ohne Auftrag stehen ruhig; leichtes Atmen und LED-Ruhelicht sind Dekoration und kein Aktivitätsnachweis. Bewegung entsteht nur bei echten Ereignissen (neuer Auftrag, Statuswechsel, Incident, Engine-Job).</p>';

  const cv = $('#hqc', root), cx = cv.getContext('2d'), stage = $('#hqstage', root);
  let dpr = window.devicePixelRatio || 1, scale = 1, selected = null, hover = null, quality = 1;
  const t0 = performance.now();

  /* --- Akteure --- */
  const defs = ROSTER.concat(SYSTEM).map(([id, role, room]) => ({ id, role, room }));
  const byRoom = {};
  defs.forEach(d => { (byRoom[d.room] = byRoom[d.room] || []).push(d); });
  const actors = new Map();
  Object.entries(byRoom).forEach(([room, list]) => {
    const pts = slots(room, list.length);
    list.forEach((d, i) => {
      const home = pts[i];
      actors.set(d.id, { ...d, home, x: home.x, y: home.y, target: null, queue: [], wait: 0, phase: 0, seed: (defs.indexOf(d) * 1.7) % 6,
        status: 'idle', alert: false, tasks: [], incidents: [], hb: null, pulses: [], moving: false });
    });
  });
  const zc = { x: ROOMS.zentrale.x + ROOMS.zentrale.w / 2, y: ROOMS.zentrale.y + ROOMS.zentrale.h - 34 };
  const cc = { x: ROOMS.council.x + ROOMS.council.w / 2, y: ROOMS.council.y + ROOMS.council.h - 40 };
  const sc = { x: ROOMS.server.x + 140, y: ROOMS.server.y + ROOMS.server.h - 40 };
  [...actors.values()].forEach((a, i) => { a.idx = i; });

  function derive() {
    const tmap = Object.fromEntries(S.tasks.map(t => [t.task_id, t]));
    actors.forEach(a => { a.tasks = S.tasks.filter(t => t.assigned_to === a.id); a.incidents = []; a.hb = S.agents.find(x => x.agent === a.id) || null; });
    S.incidents.forEach(i => {
      const owner = (tmap[i.subject] || {}).assigned_to || (actors.has(i.subject) ? i.subject : null);
      if (owner && actors.has(owner)) actors.get(owner).incidents.push(i);
    });
    actors.forEach(a => {
      const open = a.tasks.filter(t => !RE_DONE.test(t.status));
      const live = (S.activity && S.activity.agents || {})[a.id];   // echter offener Engine-Aufruf (Claude/Cloud/PC/Council)
      a.live = live || null;
      a.status = live || open.some(t => RE_WORK.test(t.status)) ? 'working' : open.some(t => RE_PLAN.test(t.status)) ? 'planning' : 'idle';
      a.alert = a.incidents.length > 0 || (a.hb && !isFresh(a.hb));
    });
  }

  function react(events) {
    events.forEach(e => {
      const a = e.agent && actors.get(e.agent);
      if (!a) return;
      const col = e.sev === 'warn' ? '#FF2E4D' : e.sev === 'ok' ? '#4ADE80' : '#35C4D8';
      a.pulses.push({ t: performance.now(), col });
      if (reduced) return;
      // Bewegung nur aus echten Ereignissen; Ziel deterministisch je Figur (kein Zufall)
      const off = ((a.idx * 37) % 60) - 30;
      if ((e.type === 'task_new' || e.type === 'task_assign' || e.type === 'task_status') && a.room !== 'zentrale') {
        a.queue.push({ goto: { x: zc.x + off, y: zc.y }, wait: 2200 });
      } else if (e.type === 'agent_consult' && /gestartet/.test(e.text) && a.room !== 'council') {
        a.queue.push({ goto: { x: cc.x + off, y: cc.y }, wait: 6000 });   // Council-Rolle geht in die Konferenz
      } else if (e.type === 'agent_work' && /gestartet/.test(e.text) && a.room !== 'server') {
        a.queue.push({ goto: { x: sc.x + off, y: sc.y }, wait: 2500 });   // Ausführung holt Rechenzeit im Serverraum
      }
    });
  }

  /* --- Bewegung --- */
  function step(dt) {
    actors.forEach(a => {
      let tgt = a.target;
      if (!tgt && a.wait <= 0 && a.queue.length) { const q = a.queue.shift(); a.target = tgt = q.goto; a.afterWait = q.wait; }
      if (tgt) {
        const dx = tgt.x - a.x, dy = tgt.y - a.y, d = Math.hypot(dx, dy), sp = 140 * dt;
        if (d <= sp) { a.x = tgt.x; a.y = tgt.y; a.target = null; a.moving = false; if (tgt !== a.home) { a.wait = a.afterWait || 1500; a.queue.unshift({ goto: a.home, wait: 0 }); } }
        else { a.x += dx / d * sp; a.y += dy / d * sp; a.moving = true; a.phase += dt * 11; }
      } else if (a.wait > 0) { a.wait -= dt * 1000; a.moving = false; }
      else a.moving = false;
    });
  }

  /* --- Zeichnen --- */
  const rr = (c, x, y, w, h, r) => { c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r); c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath(); };

  function drawRoom(key, t) {
    const r = ROOMS[key], alert = [...actors.values()].some(a => a.room === key && a.alert);
    cx.save();
    rr(cx, r.x, r.y, r.w, r.h, 14);
    cx.fillStyle = hexA(r.color, 0.055); cx.fill();
    cx.lineWidth = 1.5;
    if (alert) { cx.strokeStyle = 'rgba(255,46,77,' + (0.45 + 0.25 * Math.sin(t * 3)) + ')'; cx.setLineDash([8, 6]); }
    else cx.strokeStyle = hexA(r.color, 0.45);
    cx.stroke(); cx.setLineDash([]);
    cx.font = '600 12px "Segoe UI", system-ui, sans-serif'; cx.fillStyle = hexA(r.color, 0.95);
    cx.fillText(r.name.toUpperCase(), r.x + 16, r.y + 24);
    cx.font = '10px "Cascadia Code", Consolas, monospace'; cx.fillStyle = 'rgba(138,147,160,.8)';
    const n = [...actors.values()].filter(a => a.room === key).length;
    cx.fillText(n + (n === 1 ? ' Bewohner' : ' Bewohner'), r.x + 16, r.y + 40);
    if (alert) { cx.fillStyle = '#FF2E4D'; cx.fillText('⚠ Alarm', r.x + r.w - 62, r.y + 24); }
    cx.restore();
  }

  function drawServer(t) {
    const r = ROOMS.server, active = S.engine.active.length > 0, base = r.x + 250;
    for (let i = 0; i < 6; i++) {
      const x = base + i * 62, y = r.y + 62;
      cx.fillStyle = '#10151d'; rr(cx, x, y, 44, 82, 4); cx.fill();
      cx.strokeStyle = hexA('#FF2E4D', 0.4); cx.lineWidth = 1; cx.stroke();
      for (let k = 0; k < 6; k++) {
        const on = active ? (Math.sin(t * 6 + i * 2 + k * 1.3) > 0.1) : (k === 0);
        cx.fillStyle = on ? (k % 2 ? '#35C4D8' : '#FF5470') : 'rgba(255,255,255,.07)';
        cx.fillRect(x + 7, y + 8 + k * 12, 5, 5); cx.fillRect(x + 16, y + 10 + k * 12, 20, 2);
      }
    }
    cx.font = '10px "Cascadia Code", Consolas, monospace'; cx.fillStyle = 'rgba(138,147,160,.9)';
    cx.fillText(active ? S.engine.active.length + ' Engine-Job(s) aktiv' : 'Engine: kein aktiver Job', base, r.y + r.h - 12);
    // Ressourcenfluss Server -> Zentrale: nur bei echtem aktiven Job
    if (active && !reduced) {
      cx.save(); cx.setLineDash([6, 10]); cx.lineDashOffset = -t * 40; cx.strokeStyle = 'rgba(53,196,216,.7)'; cx.lineWidth = 2;
      cx.beginPath(); cx.moveTo(base + 120, r.y); cx.bezierCurveTo(base + 120, r.y - 120, zc.x, ROOMS.zentrale.y + ROOMS.zentrale.h + 90, zc.x, ROOMS.zentrale.y + ROOMS.zentrale.h);
      cx.stroke(); cx.restore();
    }
  }

  function drawActor(a, t) {
    const room = ROOMS[a.room], col = room.color;
    // Schreibtisch + Monitor am Heimplatz
    const hx = a.home.x, hy = a.home.y;
    cx.fillStyle = 'rgba(255,255,255,.05)'; rr(cx, hx - 26, hy + 6, 52, 18, 3); cx.fill();
    const mon = a.status === 'working' ? '#35C4D8' : a.status === 'planning' ? '#D9BFA8' : null;
    cx.fillStyle = mon ? hexA(mon, 0.85) : 'rgba(255,255,255,.08)'; cx.fillRect(hx - 8, hy + 8, 16, 9);
    if (mon && quality) { cx.save(); cx.shadowColor = mon; cx.shadowBlur = 14; cx.fillRect(hx - 8, hy + 8, 16, 9); cx.restore(); }
    // Figur
    const idle = a.status === 'idle', bob = reduced ? 0 : Math.sin(t * 2 + a.seed) * (a.moving ? 1.6 : 0.7);
    const x = a.x, y = a.y + bob - 6;
    cx.fillStyle = 'rgba(0,0,0,.35)'; cx.beginPath(); cx.ellipse(a.x, a.y + 15, 11, 4, 0, 0, 6.3); cx.fill();
    const leg = a.moving ? Math.sin(a.phase) * 3 : 0;
    cx.fillStyle = '#1b222e'; cx.fillRect(x - 5, y + 10, 4, 8 + leg); cx.fillRect(x + 1, y + 10, 4, 8 - leg);
    cx.globalAlpha = idle ? 0.6 : 1;
    cx.fillStyle = col; rr(cx, x - 8, y - 4, 16, 16, 4); cx.fill();
    cx.fillStyle = '#D9BFA8'; cx.beginPath(); cx.arc(x, y - 11, 7, 0, 6.3); cx.fill();
    cx.fillStyle = '#0E1116'; cx.fillRect(x - 5, y - 13, 10, 3);                 // Visier
    cx.fillStyle = col; cx.fillRect(x - 5, y - 13, 10, 1.2);
    cx.globalAlpha = 1;
    // Statusring
    const ring = a.status === 'working' ? '#35C4D8' : a.status === 'planning' ? '#D9BFA8' : 'rgba(138,147,160,.35)';
    cx.strokeStyle = ring; cx.lineWidth = a.status === 'working' ? 2 : 1.4;
    const pr = a.status === 'working' && !reduced ? 13 + Math.sin(t * 3 + a.seed) * 1.5 : 12;
    cx.beginPath(); cx.ellipse(a.x, a.y + 15, pr, pr * 0.36, 0, 0, 6.3); cx.stroke();
    // Alarm
    if (a.alert) {
      const p = reduced ? 1 : 0.6 + 0.4 * Math.sin(t * 5);
      cx.fillStyle = 'rgba(255,46,77,' + p + ')'; cx.beginPath(); cx.moveTo(x, y - 34); cx.lineTo(x + 7, y - 21); cx.lineTo(x - 7, y - 21); cx.closePath(); cx.fill();
      cx.fillStyle = '#fff'; cx.font = 'bold 9px sans-serif'; cx.textAlign = 'center'; cx.fillText('!', x, y - 23); cx.textAlign = 'left';
    }
    // Name
    cx.font = (selected === a.id || hover === a.id ? '600 ' : '') + '10px "Cascadia Code", Consolas, monospace';
    cx.textAlign = 'center'; cx.fillStyle = selected === a.id ? '#fff' : idle ? 'rgba(138,147,160,.9)' : 'rgba(232,232,232,.95)';
    cx.fillText(shortName(a.id), a.x, a.y + 33); cx.textAlign = 'left';
    if (selected === a.id || hover === a.id) { cx.strokeStyle = hexA('#35C4D8', 0.9); cx.lineWidth = 1.5; rr(cx, a.x - 22, y - 26, 44, 66, 8); cx.stroke(); }
    // Pulse-Ringe fuer echte Ereignisse
    const now = performance.now();
    a.pulses = a.pulses.filter(p => now - p.t < 1800);
    a.pulses.forEach(p => { const k = (now - p.t) / 1800; cx.strokeStyle = hexA(p.col.length === 7 ? p.col : '#35C4D8', 1 - k); cx.lineWidth = 2; cx.beginPath(); cx.arc(a.x, a.y, 14 + k * 38, 0, 6.3); cx.stroke(); });
  }

  let bgCache = null, bgKey = '';
  function drawBg() {
    const key = cv.width + 'x' + cv.height;
    if (bgKey !== key) {
      bgCache = document.createElement('canvas'); bgCache.width = cv.width; bgCache.height = cv.height;
      const b = bgCache.getContext('2d'); b.setTransform(dpr * scale, 0, 0, dpr * scale, 0, 0);
      const g = b.createRadialGradient(W / 2, Hh / 2, 80, W / 2, Hh / 2, 760); g.addColorStop(0, '#141a24'); g.addColorStop(1, '#0a0d12');
      b.fillStyle = g; b.fillRect(0, 0, W, Hh);
      b.strokeStyle = 'rgba(255,255,255,.028)'; b.lineWidth = 1;
      for (let x = 0; x <= W; x += 40) { b.beginPath(); b.moveTo(x, 0); b.lineTo(x, Hh); b.stroke(); }
      for (let y = 0; y <= Hh; y += 40) { b.beginPath(); b.moveTo(0, y); b.lineTo(W, y); b.stroke(); }
      bgKey = key;
    }
    cx.setTransform(1, 0, 0, 1, 0, 0); cx.drawImage(bgCache, 0, 0); cx.setTransform(dpr * scale, 0, 0, dpr * scale, 0, 0);
  }

  function draw() {
    const t = (performance.now() - t0) / 1000;
    drawBg();
    Object.keys(ROOMS).forEach(k => drawRoom(k, t));
    drawServer(t);
    [...actors.values()].sort((p, q) => p.y - q.y).forEach(a => drawActor(a, t));
  }

  function resize() {
    const w = Math.max(320, stage.clientWidth);
    dpr = Math.min(window.devicePixelRatio || 1, quality ? 2 : 1);
    scale = w / W;
    cv.style.width = w + 'px'; cv.style.height = Math.round(w * Hh / W) + 'px';
    cv.width = Math.round(w * dpr); cv.height = Math.round(w * Hh / W * dpr);
    cx.setTransform(dpr * scale, 0, 0, dpr * scale, 0, 0);
    bgKey = '';
    draw();
  }

  /* --- Panels --- */
  function chips() {
    const L = [...actors.values()], c = s => L.filter(a => a.status === s).length, al = L.filter(a => a.alert).length;
    $('#hqchips', root).innerHTML =
      '<span class="chip cyan"><span class="dot live"></span> ' + c('working') + ' arbeiten</span>' +
      '<span class="chip">' + c('planning') + ' in Planung</span>' +
      '<span class="chip">' + c('idle') + ' ohne Auftrag</span>' +
      '<span class="chip' + (al ? ' crimson' : '') + '">' + al + ' Alarm' + (al === 1 ? '' : 'e') + '</span>' +
      '<span class="chip">' + S.incidents.length + ' offene Incidents</span>' +
      (S.error ? '<span class="chip crimson">Datenfehler: ' + esc(S.error) + '</span>' : '<span class="chip">Stand ' + (S.ts ? hhmmss(S.ts) : '…') + '</span>');
  }
  function feed() {
    const ev = S.events.slice(0, 30);
    $('#hqfeed', root).innerHTML = ev.length ? ev.map(e => '<li class="ev ' + e.sev + '"><span class="dot ' + (e.sev === 'warn' ? 'err' : e.sev === 'ok' ? 'ok' : 'live') + '"></span><span class="mono evt">' + hhmmss(e.t) + '</span><span>' + esc(e.text) + '</span></li>').join('')
      : '<li class="faint">Noch keine Änderungen seit dem Öffnen. Neue Aufträge, Statuswechsel und Incidents erscheinen hier, sobald sie passieren.</li>';
    const jobs = (S.engine.recent || []).slice(0, 5);
    $('#hqjobs', root).innerHTML = jobs.length ? jobs.map(j => '<li class="ev ok"><span class="dot ' + (j.state === 'done' ? 'ok' : 'warn') + '"></span><span class="mono evt">' + (j.finished ? new Date(j.finished * 1000).toLocaleTimeString('de-DE') : '') + '</span><span>' + esc(j.id) + ' · ' + esc(j.state) + ' · ' + (j.tokens_new || 0) + ' Token</span></li>').join('') : '<li class="faint">Keine Jobs.</li>';
  }
  const STATUS_TXT = { working: 'arbeitet', planning: 'in Planung', idle: 'ohne Auftrag' };
  function drawer() {
    const d = $('#hqd', root);
    if (!selected) { d.hidden = true; return; }
    const a = actors.get(selected); if (!a) { d.hidden = true; return; }
    const evs = S.events.filter(e => e.agent === a.id).slice(0, 5);
    d.hidden = false;
    d.innerHTML = '<button class="btn ghost small hqx" id="hqclose" aria-label="Schließen">✕</button>' +
      '<h3>' + esc(shortName(a.id)) + (a.alert ? ' <span class="chip crimson">Alarm</span>' : '') + '</h3>' +
      '<div class="sub">' + esc(a.role) + ' · ' + esc(ROOMS[a.room].name) + '</div>' +
      '<p><span class="chip ' + (a.status === 'working' ? 'cyan' : '') + '">' + STATUS_TXT[a.status] + '</span></p>' +
      (a.live ? '<div class="hqk">Gerade (Engine)</div><div><span class="mono">' + esc(a.live.job) + '</span> · ' + esc(a.live.text) + '</div>' : '') +
      (a.hb ? '<div class="hqk">Heartbeat</div><div>' + (isFresh(a.hb) ? '<span class="dot ok"></span> aktuell' : '<span class="dot warn"></span> veraltet') + ' · vor ' + ago(a.hb.last_heartbeat) + ' · ' + esc(a.hb.status) + '</div>' : '<div class="hqk">Heartbeat</div><div class="faint">keine Telemetrie in der Heartbeat-Tabelle</div>') +
      '<div class="hqk">Aufträge (' + a.tasks.length + ')</div>' + (a.tasks.length ? '<ul class="hql">' + a.tasks.map(t => '<li><b class="mono">' + esc(t.task_id) + '</b> ' + esc(t.title) + '<br><span class="chip">' + esc(t.status) + '</span> <span class="faint">akt. vor ' + ago(t.updated) + '</span></li>').join('') + '</ul>' : '<div class="faint">keine zugewiesen</div>') +
      (a.incidents.length ? '<div class="hqk">Incidents</div><ul class="hql">' + a.incidents.map(i => '<li><span class="chip crimson">' + esc(i.classification) + '</span> ' + esc(i.subject) + ' <span class="faint">seit ' + Math.round(i.age_min / 60) + ' Std</span></li>').join('') + '</ul>' : '') +
      (evs.length ? '<div class="hqk">Letzte Ereignisse</div><ul class="hql">' + evs.map(e => '<li><span class="mono faint">' + hhmmss(e.t) + '</span> ' + esc(e.text) + '</li>').join('') + '</ul>' : '');
    $('#hqclose', root).onclick = () => { selected = null; drawer(); if (reduced) draw(); };
  }

  /* --- Interaktion --- */
  const pick = ev => {
    const r = cv.getBoundingClientRect(), x = (ev.clientX - r.left) / scale, y = (ev.clientY - r.top) / scale;
    let best = null, bd = 28;
    actors.forEach(a => { const d = Math.hypot(a.x - x, a.y - 6 - y); if (d < bd) { bd = d; best = a.id; } });
    return best;
  };
  cv.addEventListener('mousemove', ev => { const h = pick(ev); if (h !== hover) { hover = h; cv.style.cursor = h ? 'pointer' : 'default'; if (reduced) draw(); } });
  cv.addEventListener('click', ev => { const h = pick(ev); selected = h === selected ? null : h; drawer(); if (reduced) draw(); });

  /* --- Hauptschleife mit adaptiver Qualitaet --- */
  let raf = 0, last = performance.now(), acc = 0, frames = 0, running = true;
  function frame(now) {
    if (!running) return;
    raf = requestAnimationFrame(frame);
    const dt = Math.min(0.1, (now - last) / 1000); last = now;
    acc += dt; frames++;
    if (frames >= 90) { const ft = acc / frames * 1000; if (ft > 26 && quality) { quality = 0; resize(); } acc = 0; frames = 0; }
    if (document.hidden) return;
    step(dt); draw();
  }

  const unsub = subscribe((st, fresh) => {
    derive(); react(fresh); chips(); feed(); drawer();
    if (reduced) { actors.forEach(a => { a.x = a.home.x; a.y = a.home.y; a.queue = []; a.target = null; }); draw(); }
  });
  let roRaf = 0; const ro = new ResizeObserver(() => { cancelAnimationFrame(roRaf); roRaf = requestAnimationFrame(resize); }); ro.observe(stage);   // entkoppelt: kein Resize-Loop-Warning
  window.addEventListener('resize', resize);
  resize();
  if (!reduced) raf = requestAnimationFrame(frame);

  stopFn = () => { running = false; cancelAnimationFrame(raf); ro.disconnect(); window.removeEventListener('resize', resize); unsub(); };
}
