/* MA-HOME HQ — Sprach-Oberflaeche: Orb (animierter Kern, echter Mikrofonpegel), Steuerung, Transkript, Kopfzeilen-Knopf */
import { $, esc } from './api.js';
import { V, onVoice, setWake, talkOnce, setSpeak, setVoiceName, voices, stopAll, clearTranscript, micLevel, sayText } from './voice.js';

let stopFn = null;
export function leaveVoice() { if (stopFn) { stopFn(); stopFn = null; } }

const STATE_TXT = {
  off: 'Aus – Wakeword ist nicht aktiv', wake: 'Wartet auf „Jarvis“ …', listening: 'Ich höre zu …',
  thinking: 'Denkt nach …', speaking: 'Spricht – sag „Jarvis stopp“ zum Unterbrechen'
};
const COL = { off: '138,147,160', wake: '53,196,216', listening: '255,46,77', thinking: '53,196,216', speaking: '217,191,168' };

/* ---- Kopfzeilen-Knopf (global) ---- */
export function mountVoiceButton(host, go) {
  const b = document.createElement('button');
  b.className = 'voice-btn'; b.type = 'button'; b.id = 'voice-btn';
  b.innerHTML = '<span class="vdot"></span><span class="vlbl">Sprache</span>';
  b.title = 'Sprachsteuerung: Klick = Satz diktieren · Umschalt+Klick = Wakeword an/aus';
  b.onclick = e => { if (e.shiftKey) setWake(!V.enabled); else talkOnce(); };
  host.insertBefore(b, host.querySelector('.palette-trigger'));
  const upd = () => { b.dataset.state = V.state; b.classList.toggle('on', V.enabled); b.querySelector('.vlbl').textContent = V.state === 'wake' ? 'Jarvis hört' : V.state === 'listening' ? 'Höre zu' : V.state === 'thinking' ? 'Denke' : V.state === 'speaking' ? 'Spricht' : 'Sprache'; };
  onVoice(upd); upd();
}

/* ---- Ansicht ---- */
export function renderVoice(root, ctx) {
  leaveVoice();
  root.innerHTML =
    '<div class="top"><div><h1>Sprache</h1><div class="sub">Deutsche Spracherkennung und Sprachausgabe · Wakeword „Jarvis“ optional · Sprachaufträge nur lesend</div></div></div>' +
    '<div class="voice-grid"><div class="holo voice-orbcard"><canvas id="vorb" width="520" height="520" aria-label="Animierter JARVIS-Kern"></canvas>' +
    '<div class="voice-state" id="vstate"></div><div class="voice-interim" id="vint"></div>' +
    '<div class="voice-ctl"><button class="btn primary" id="vtalk">🎤 Jetzt sprechen</button><button class="btn" id="vwake"></button><button class="btn ghost" id="vstop">■ Stopp</button></div>' +
    '<div class="voice-opt"><label><input type="checkbox" id="vspk"> Antworten vorlesen</label><label>Stimme <select id="vvoice"></select></label></div>' +
    '<form class="voice-text" id="vtf"><input id="vti" placeholder="…oder Text eingeben (gleicher Pfad wie gesprochen)" autocomplete="off"><button class="btn">Senden</button></form></div>' +
    '<div class="voice-side"><div class="holo"><h2 class="holo-title">Transkript<span class="sub">Gespräch dieser Sitzung · <a href="#" id="vclr">leeren</a></span></h2><ul id="vlog" class="voice-log"></ul></div>' +
    '<div class="holo" style="margin-top:16px"><h2 class="holo-title">Was geht<span class="sub">lokale Antworten kosten keine Token</span></h2><ul class="hql">' +
    '<li><b>„Jarvis, wie ist die Lage?“</b> – Status aller Agenten</li><li><b>„Gibt es Alarme?“</b> – offene Incidents</li><li><b>„Wer arbeitet gerade?“</b> · <b>„Was macht Planner?“</b></li>' +
    '<li><b>„Welche Aufgaben sind offen?“</b></li><li><b>„Öffne Living HQ“</b> · Command Center · Chat · Aufgaben …</li><li><b>„Jarvis stopp“</b> – Ausgabe unterbrechen</li>' +
    '<li>Alles andere → JARVIS (Haiku, <b>nur lesend</b>)</li></ul></div>' +
    '<div class="holo danger" style="margin-top:16px"><h2 class="holo-title">Datenschutz &amp; Grenzen</h2><p class="muted" style="margin:0;font-size:var(--fs-small)">' +
    'Wenn dein PC an ist, erkennt und spricht JARVIS lokal: Aufnahmen gehen über dein Portal nur an den Sprachdienst auf deinem PC (Whisper und Piper), nicht an Google. Ist der PC aus, nutzt das Portal die Browser-Spracherkennung (Chrome/Edge), die Audio an den Browser-Anbieter sendet – im Wake-Modus dauerhaft, deshalb nur mit deiner Bestätigung. Im bestätigten Wake-Modus hört JARVIS nach einer Antwort bis zu zwölf Sekunden auf eine Folgefrage, ohne dass du erneut „Jarvis“ sagen musst. Sonstige Äußerungen außerhalb dieses Gesprächsfensters werden ohne Wakeword verworfen und nicht im Portaltranskript gespeichert. ' +
    'Auf Handys beenden manche Browser die Dauer-Erkennung bei gesperrtem Bildschirm.</p>' +
    '<p id="vcap" class="faint" style="margin:8px 0 0;font-size:var(--fs-small)"></p></div></div></div>';

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
    $('#vwake', root).textContent = V.enabled ? 'Wakeword aus' : 'Wakeword „Jarvis“ an';
    $('#vspk', root).checked = V.speakOn;
    const vs = voices(), sel = $('#vvoice', root);
    const want = vs.length + 1 + (V.localOk ? 1 : 0);
    if (sel.options.length !== want) { sel.innerHTML = '<option value="">Automatisch (' + (V.localOk ? 'JARVIS-Stimme, lokal' : 'beste deutsche Stimme') + ')</option>' + (V.localOk ? '<option value="jarvis-local">JARVIS – Thorsten (lokal, eigener PC)</option>' : '') + vs.map(v => '<option>' + esc(v.name) + '</option>').join(''); }
    sel.value = V.voiceName || '';
    $('#vlog', root).innerHTML = V.transcript.length ? V.transcript.slice().reverse().map(m => '<li class="' + m.r + '"><span class="who">' + (m.r === 'u' ? 'Du' : 'JARVIS') + '</span><span>' + esc(m.t) + '</span>' + (m.src ? '<span class="src">' + esc(m.src) + '</span>' : '') + '</li>').join('') : '<li class="faint">Noch nichts gesagt. Klick auf „Jetzt sprechen“ oder tippe unten eine Frage.</li>';
    $('#vcap', root).textContent = 'Spracherkennung: ' + (V.engine === 'local' ? 'lokal auf deinem PC (Whisper)' : V.supported ? 'Browser-Dienst' : 'NICHT verfügbar') + ' · Sprachausgabe: ' + (V.localOk ? 'JARVIS-Stimme lokal + ' : '') + (('speechSynthesis' in window) ? voices().length + ' Browserstimme(n)' : 'keine Browserstimme');
  }

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
