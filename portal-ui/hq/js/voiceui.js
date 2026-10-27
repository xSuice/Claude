/* MA-HOME HQ — Sprach-Oberflaeche: Orb (animierter Kern, echter Mikrofonpegel), Steuerung, Transkript, Kopfzeilen-Knopf */
import { $, esc } from './api.js';
import { V, onVoice, setWake, talkOnce, setSpeak, setVoiceName, voices, stopAll, clearTranscript, micLevel, sayText, setThreshold, resetWakeMax, engineStats } from './voice.js';
import { localHealth } from './localvoice.js';

let stopFn = null;
export function leaveVoice() { if (stopFn) { stopFn(); stopFn = null; } }

const STATE_TXT = {
  off: 'Aus – Wakeword ist nicht aktiv', wake: 'Wartet auf „Hey Jarvis“ …', listening: 'Ich höre zu …',
  thinking: 'Denkt nach …', speaking: 'Spricht – sag „Hey Jarvis“ zum Unterbrechen'
};
const COL = { off: '138,147,160', wake: '53,196,216', listening: '255,46,77', thinking: '53,196,216', speaking: '217,191,168' };

/* ---- Kopfzeilen-Knopf (global) ---- */
export function mountVoiceButton(host, go) {
  const b = document.createElement('button');
  b.className = 'voice-btn'; b.type = 'button'; b.id = 'voice-btn';
  b.innerHTML = '<span class="vdot"></span><span class="vlbl">Sprache</span>';
  b.title = 'Sprachsteuerung: Klick = Frage stellen · Umschalt+Klick = Wakeword „Hey Jarvis“ an/aus';
  b.onclick = e => { if (e.shiftKey) setWake(!V.enabled); else talkOnce(); };
  host.insertBefore(b, host.querySelector('.palette-trigger'));
  const upd = () => { b.dataset.state = V.state; b.classList.toggle('on', V.enabled); b.querySelector('.vlbl').textContent = V.state === 'wake' ? 'Jarvis hört' : V.state === 'listening' ? 'Höre zu' : V.state === 'thinking' ? 'Denke' : V.state === 'speaking' ? 'Spricht' : 'Sprache'; };
  onVoice(upd); upd();
}

/* ---- Ansicht ---- */
export function renderVoice(root, ctx) {
  leaveVoice();
  root.innerHTML =
    '<div class="top"><div><h1>Sprache</h1><div class="sub">Wakeword „Hey Jarvis“ im Browser · Erkennung und Stimme lokal auf deinem PC · Sprachaufträge nur lesend</div></div></div>' +
    '<div class="voice-grid"><div class="holo voice-orbcard"><canvas id="vorb" width="520" height="520" aria-label="Animierter JARVIS-Kern"></canvas>' +
    '<div class="voice-state" id="vstate" role="status" aria-live="polite"></div><div class="voice-interim" id="vint"></div>' +
    '<div class="voice-meter" id="vmeter" hidden><span>„Hey Jarvis“-Erkennung</span><div class="vm-bar"><i id="vmb"></i><b id="vmt"></b></div><span id="vmv" class="faint"></span></div>' +
    '<div class="voice-ctl"><button class="btn primary" id="vtalk">🎤 Jetzt sprechen</button><button class="btn" id="vwake"></button><button class="btn ghost" id="vstop">■ Stopp</button></div>' +
    '<div class="voice-opt"><label><input type="checkbox" id="vspk"> Antworten vorlesen</label><label>Stimme <select id="vvoice"></select></label>' +
    '<label title="Niedriger = reagiert leichter, aber öfter versehentlich">Empfindlichkeit <input type="range" id="vthr" min="0.2" max="0.8" step="0.05" aria-label="Wakeword-Schwelle"> <span id="vthrv"></span></label></div>' +
    '<form class="voice-text" id="vtf"><input id="vti" placeholder="…oder Text eingeben (gleicher Pfad wie gesprochen)" autocomplete="off"><button class="btn">Senden</button></form></div>' +
    '<div class="voice-side"><div class="holo"><h2 class="holo-title">Transkript<span class="sub">Gespräch dieser Sitzung · <a href="#" id="vclr">leeren</a></span></h2><ul id="vlog" class="voice-log"></ul></div>' +
    '<div class="holo" style="margin-top:16px"><h2 class="holo-title">Was geht<span class="sub">lokale Antworten kosten keine Token</span></h2><ul class="hql">' +
    '<li><b>„Hey Jarvis, wie ist die Lage?“</b> – Status aller Agenten</li><li><b>„Gibt es Alarme?“</b> – offene Incidents</li><li><b>„Wer arbeitet gerade?“</b> · <b>„Was macht Planner?“</b></li>' +
    '<li><b>„Welche Aufgaben sind offen?“</b></li><li><b>„Öffne Living HQ“</b> · Command Center · Chat · Aufgaben …</li><li><b>„Hey Jarvis“</b> während er spricht – unterbricht ihn</li><li>Nach einer Antwort 12 s lang Folgefragen <b>ohne</b> „Hey Jarvis“</li>' +
    '<li>Alles andere → JARVIS (Haiku, <b>nur lesend</b>)</li></ul></div>' +
    '<div class="holo danger" style="margin-top:16px"><h2 class="holo-title">Datenschutz &amp; Grenzen</h2><p class="muted" style="margin:0;font-size:var(--fs-small)">' +
    '„Hey Jarvis“ erkennt ein kleines Modell (openWakeWord) direkt hier im Browser – bis dahin verlässt kein Ton dein Gerät. Erst danach und im Gesprächsfenster geht deine Frage über dein Portal an den Sprachdienst auf deinem PC (Whisper, Piper Thorsten). Ist der PC aus, nutzt das Portal ersatzweise die Browser-Spracherkennung (Chrome/Edge sendet dann Audio an den Browser-Anbieter – nur mit deiner Bestätigung). ' +
    'Auf Handys beenden manche Browser die Dauer-Erkennung bei gesperrtem Bildschirm.</p>' +
    '<p id="vcap" class="faint" style="margin:8px 0 0;font-size:var(--fs-small)"></p></div>' +
    '<div class="holo" style="margin-top:16px"><h2 class="holo-title">Diagnose<span class="sub"><a href="#" id="vdiagrun">prüfen</a> · <a href="#" id="vdiagcp">Bericht kopieren</a></span></h2><ul id="vdiag" class="voice-diag"></ul></div></div></div>';

  const cv = $('#vorb', root), cx = cv.getContext('2d'), t0 = performance.now();
  let raf = 0, running = true, amp = 0;
  const reduced = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  function drawOrb() {
    if (!running) return;
    raf = requestAnimationFrame(drawOrb);
    if (document.hidden) return;
    const t = (performance.now() - t0) / 1000, W = cv.width, H = cv.height, c = W / 2, col = COL[V.state] || COL.off;
    const { level, bins } = micLevel();
    amp += ((V.state === 'listening' || V.state === 'wake' ? level : V.state === 'speaking' ? 0.5 + 0.4 * Math.sin(t * 9) * (V.level || .5) : V.state === 'thinking' ? 0.25 : 0.05) - amp) * 0.18;
    V.level = Math.max(0, V.level * 0.93);
    cx.clearRect(0, 0, W, H);
    const base = 120 + amp * 36 + (reduced ? 0 : Math.sin(t * (V.state === 'wake' ? 1.2 : 2.4)) * 5);
    // Glow
    const g = cx.createRadialGradient(c, c, 10, c, c, base * 1.9);
    g.addColorStop(0, 'rgba(' + col + ',.55)'); g.addColorStop(.45, 'rgba(' + col + ',.16)'); g.addColorStop(1, 'rgba(' + col + ',0)');
    cx.fillStyle = g; cx.beginPath(); cx.arc(c, c, base * 1.9, 0, 6.3); cx.fill();
    // Kern
    const k = cx.createRadialGradient(c, c + 18, 6, c, c, base);
    k.addColorStop(0, 'rgba(' + (V.state === 'off' ? '90,99,111' : '255,84,112') + ',1)'); k.addColorStop(.6, 'rgba(' + (V.state === 'off' ? '40,46,56' : '139,26,43') + ',.95)'); k.addColorStop(1, 'rgba(14,17,22,.9)');
    cx.fillStyle = k; cx.beginPath(); cx.arc(c, c, base, 0, 6.3); cx.fill();
    // Ring + Pegelbalken (echte Frequenzdaten)
    cx.strokeStyle = 'rgba(' + col + ',.85)'; cx.lineWidth = 3; cx.beginPath(); cx.arc(c, c, base + 14, 0, 6.3); cx.stroke();
    const N = 48;
    for (let i = 0; i < N; i++) {
      const a = i / N * 6.2832, v = bins ? bins[Math.floor(i / N * bins.length * .8)] / 255 : (V.state === 'speaking' ? (0.3 + 0.5 * Math.abs(Math.sin(t * 7 + i * .7))) * (V.level || .4) : 0.04);
      const len = 6 + v * 60 * (V.state === 'off' ? 0.2 : 1);
      cx.strokeStyle = 'rgba(' + col + ',' + (0.35 + v * 0.6) + ')'; cx.lineWidth = 3;
      cx.beginPath(); cx.moveTo(c + Math.cos(a) * (base + 26), c + Math.sin(a) * (base + 26)); cx.lineTo(c + Math.cos(a) * (base + 26 + len), c + Math.sin(a) * (base + 26 + len)); cx.stroke();
    }
    if (V.state === 'thinking') {
      cx.strokeStyle = 'rgba(53,196,216,.9)'; cx.lineWidth = 4;
      for (let i = 0; i < 3; i++) { const a0 = t * 2.2 + i * 2.09; cx.beginPath(); cx.arc(c, c, base + 96, a0, a0 + 0.9); cx.stroke(); }
    }
  }

  function ui() {
    $('#vstate', root).innerHTML = '<span class="dot ' + (V.state === 'off' ? 'warn' : V.state === 'listening' ? 'err' : 'live') + '"></span> ' + esc(STATE_TXT[V.state] || V.state) + (V.err ? '<div class="voice-err">' + esc(V.err) + '</div>' : '');
    $('#vint', root).textContent = V.interim ? '„' + V.interim + '“' : '';
    $('#vwake', root).textContent = V.enabled ? 'Wakeword aus' : 'Wakeword „Hey Jarvis“ an';
    $('#vspk', root).checked = V.speakOn;
    const vs = voices(), sel = $('#vvoice', root);
    const want = vs.length + 1 + (V.localOk ? 1 : 0);
    if (sel.options.length !== want) { sel.innerHTML = '<option value="">Automatisch (' + (V.localOk ? 'JARVIS-Stimme, lokal' : 'beste deutsche Stimme') + ')</option>' + (V.localOk ? '<option value="jarvis-local">JARVIS – Thorsten (lokal, eigener PC)</option>' : '') + vs.map(v => '<option>' + esc(v.name) + '</option>').join(''); }
    sel.value = V.voiceName || '';
    $('#vlog', root).innerHTML = V.transcript.length ? V.transcript.slice().reverse().map(m => '<li class="' + m.r + '"><span class="who">' + (m.r === 'u' ? 'Du' : 'JARVIS') + '</span><span>' + esc(m.t) + '</span>' + (m.src ? '<span class="src">' + esc(m.src) + '</span>' : '') + '</li>').join('') : '<li class="faint">Noch nichts gesagt. Klick auf „Jetzt sprechen“ oder tippe unten eine Frage.</li>';
    const m = $('#vmeter', root); m.hidden = !(V.engine2 === 'bereit');
  if (!m.hidden) { $('#vmb', root).style.width = Math.round(V.wakeScore * 100) + '%'; $('#vmt', root).style.left = Math.round(V.threshold * 100) + '%'; $('#vmv', root).textContent = 'aktuell ' + V.wakeScore.toFixed(2) + ' · höchster ' + V.wakeMax.toFixed(2) + ' · Schwelle ' + V.threshold.toFixed(2); }
  const th = $('#vthr', root); if (document.activeElement !== th) th.value = V.threshold; $('#vthrv', root).textContent = V.threshold.toFixed(2);
  $('#vcap', root).textContent = 'Wakeword: ' + (V.engine2 === 'bereit' ? '„Hey Jarvis“-Modell im Browser' : V.engine2 === 'lädt' ? 'Modelle werden geladen …' : V.wakeMode === 'text' ? 'Ersatz per Transkript („Jarvis“ im Text)' + (V.engErr ? ' – Modell-Fehler: ' + V.engErr : '') : 'startet beim Einschalten') + ' · Spracherkennung: ' + (V.engine === 'local' ? 'lokal auf deinem PC (Whisper)' : V.supported ? 'Browser-Dienst' : 'NICHT verfügbar') + ' · Sprachausgabe: ' + (V.localOk ? 'JARVIS-Stimme lokal + ' : '') + (('speechSynthesis' in window) ? voices().length + ' Browserstimme(n)' : 'keine Browserstimme');
  }

  const diag = async () => {
    const perm = navigator.permissions ? await navigator.permissions.query({ name: 'microphone' }).then(p => p.state).catch(() => 'unbekannt') : 'unbekannt';
    const pc = await localHealth(), es = engineStats();
    let wasm = false; try { wasm = typeof WebAssembly === 'object' && !!(await WebAssembly.instantiate(new Uint8Array([0, 97, 115, 109, 1, 0, 0, 0]))); } catch (e) { wasm = false; }
    const rows = [
      ['Sichere Verbindung (HTTPS)', window.isSecureContext, window.isSecureContext ? '' : 'Mikrofon geht nur über HTTPS'],
      ['Mikrofon-Berechtigung', perm === 'granted', perm === 'granted' ? 'erlaubt' : perm === 'denied' ? 'verweigert – in den Seiteneinstellungen erlauben' : 'wird beim Einschalten gefragt'],
      ['WebAssembly erlaubt', wasm, wasm ? '' : 'Browser/Sicherheitsrichtlinie blockiert WebAssembly'],
      ['Wakeword-Modell', V.engine2 === 'aus' ? null : V.engine2 === 'bereit', V.engine2 === 'bereit' ? 'geladen' + (es ? ' · ' + es.rate + ' Hz · ' + es.busyMs.toFixed(1) + ' ms je Rahmen' : '') : V.engErr || V.engine2],
      ['Lokaler Sprachdienst (PC)', pc, pc ? 'erreichbar (Whisper + Thorsten)' : 'nicht erreichbar – PC aus oder Tunnel getrennt'],
      ['Audioausgabe', !!(window.AudioContext || window.webkitAudioContext), ''],
      ['Mikrofonpegel', es ? es.level > 0.0005 : null, es ? 'Pegel ' + (20 * Math.log10(Math.max(es.level, 1e-6))).toFixed(0) + ' dBFS' : 'erst nach Einschalten']];
    $('#vdiag', root).innerHTML = rows.map(r => '<li><span class="vd-' + (r[1] === null ? 'n' : r[1] ? 'ok' : 'bad') + '">' + (r[1] === null ? '–' : r[1] ? '✓' : '✗') + '</span> ' + esc(r[0]) + (r[2] ? ' <span class="faint">' + esc(r[2]) + '</span>' : '') + '</li>').join('');
    return rows;
  };
  $('#vdiagrun', root).onclick = e => { e.preventDefault(); resetWakeMax(); diag(); };
  $('#vdiagcp', root).onclick = async e => { e.preventDefault(); const rows = await diag(); const txt = '## JARVIS Sprache – Diagnose ' + new Date().toISOString() + '\n' + rows.map(r => '- ' + (r[1] === null ? '–' : r[1] ? 'OK' : 'FEHLER') + ' ' + r[0] + (r[2] ? ': ' + r[2] : '')).join('\n') + '\n- Zustand: ' + V.state + ', Wakeword-Modus: ' + V.wakeMode + ', Schwelle ' + V.threshold + ', höchster Wert ' + V.wakeMax.toFixed(2) + '\n- Browser: ' + navigator.userAgent + (V.err ? '\n- Fehler: ' + V.err : ''); try { await navigator.clipboard.writeText(txt); e.target.textContent = 'kopiert ✓'; } catch (er) { prompt('Bericht kopieren:', txt); } };
  $('#vthr', root).oninput = e => setThreshold(parseFloat(e.target.value));
  diag();
  $('#vtalk', root).onclick = () => talkOnce();
  $('#vwake', root).onclick = () => setWake(!V.enabled);
  $('#vstop', root).onclick = () => stopAll();
  $('#vspk', root).onchange = e => { setSpeak(e.target.checked); try { localStorage.setItem('hq-speak', e.target.checked ? '1' : '0'); } catch (er) { /* */ } };
  $('#vvoice', root).onchange = e => setVoiceName(e.target.value);
  $('#vclr', root).onclick = e => { e.preventDefault(); clearTranscript(); };
  $('#vtf', root).onsubmit = e => { e.preventDefault(); const i = $('#vti', root), v = i.value.trim(); if (v) { i.value = ''; sayText(v); } };

  const off = onVoice(ui); ui();
  raf = requestAnimationFrame(drawOrb);
  stopFn = () => { running = false; cancelAnimationFrame(raf); off(); };
}
