/* MA-HOME HQ — Sprachschnittstelle (M4, SPEC §12): deutsche Spracherkennung + natürliche Sprachausgabe (Web Speech API),
   optionales Wakeword "Jarvis", unterbrechbar, Transkripte, animierter Kern mit echtem Mikrofonpegel.
   Datenschutz: Die Browser-Spracherkennung (Chrome) sendet Audio an den Browser-Anbieter -> nur mit ausdruecklicher Einwilligung.
   Lokale Whisper/Piper-Variante ist Phase B.  Sprachaufträge sind IMMER nur lesend (kein Schreiben/Loeschen per Sprache).
   Lokale Intents (Status, Alarme, Aufgaben, Navigation, Uhrzeit) kosten keine Token; nur Freitext geht an JARVIS (haiku, lesen). */
import { toast } from './api.js';
import { S, agentState, isFresh, shortName, refresh } from './store.js';
import { ROSTER } from './roster.js';
import { voiceAsk } from './chat.js';
import { speechChunks } from './speech-text.js';
import { LOCAL_VOICE, LocalEar, localHealth, playLocal, unlockAudio } from './localvoice.js';

const getSR = () => window.SpeechRecognition || window.webkitSpeechRecognition;
export const WAKE = /\b(jarvis|dscharvis|dscharwis|dschavis|dschawis|jarwis|tscharvis|charvis|scharwis|jervis|jaris|javis|jarvi)\b/i;
const STOP = /\b(stopp|stop|halt|ruhe|sei still|abbrechen)\b/i;

export const V = {
  supported: !!getSR(), tts: 'speechSynthesis' in window,
  engine: getSR() ? 'browser' : 'none', localOk: false,   // engine: local (eigener PC) | browser | none
  enabled: false, state: 'off',            // off | wake | listening | thinking | speaking
  interim: '', transcript: [], speakOn: true, level: 0, voiceName: '', err: '', go: null
};
const listeners = new Set();
const emit = () => listeners.forEach(f => { try { f(V); } catch (e) { console.error(e); } });
export const onVoice = f => { listeners.add(f); return () => listeners.delete(f); };
const setState = s => { V.state = s; emit(); };
const say = (r, t, src) => { V.transcript.push({ r, t, src: src || '', ts: Date.now() }); V.transcript = V.transcript.slice(-40); emit(); };

/* ---------- Lokale Intents (token-frei) ---------- */
const NAV = { 'living hq': 'hq', 'hq': 'hq', 'command center': 'cc', 'kommandozentrale': 'dashboard', 'chat': 'chat', 'aufgaben': 'tasks', 'notizen': 'notes',
  'dateien': 'files', 'terminal': 'term', 'system': 'status', 'vault': 'vault', 'einstellungen': 'einstellungen', 'sprache': 'voice' };
const names = list => list.length <= 1 ? list.join('') : list.slice(0, -1).join(', ') + ' und ' + list[list.length - 1];

export function answerLocal(text) {
  const t = text.toLowerCase().replace(/[.,!?]/g, ' ').replace(/\s+/g, ' ').trim();
  const ids = ROSTER.map(r => r[0]);
  const st = ids.map(agentState);
  if (STOP.test(t) && t.split(' ').length <= 3) return { reply: '', action: 'cancel' };
  let m = t.match(/(?:öffne|zeig(?:e)?(?: mir)?|gehe? zu|wechsle zu|bring mich zu)\s+(?:den |die |das |dem )?([a-zäöü ]+)/);
  if (m) { const key = Object.keys(NAV).sort((a, b) => b.length - a.length).find(k => m[1].trim().startsWith(k)); if (key) return { reply: 'Ich öffne ' + key + '.', nav: NAV[key] }; }
  if (/(wie spät|uhrzeit|wie ?viel uhr)/.test(t)) return { reply: 'Es ist ' + new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' }) + ' Uhr.' };
  const who = ids.find(id => new RegExp('\\b' + shortName(id).replace('-', '[ -]') + '\\b').test(t));
  if (who && /(was macht|woran arbeitet|status von|wie geht|zustand)/.test(t)) {
    const a = agentState(who), word = a.status === 'working' ? 'arbeitet' : a.status === 'planning' ? 'plant' : 'hat gerade keinen Auftrag';
    return { reply: shortName(who) + ' ' + word + (a.open[0] ? ': ' + a.open[0].title + '.' : '.') + (a.alert ? ' Achtung, dort liegt ein Alarm vor.' : '') };
  }
  if (/(wer arbeitet|wer ist (gerade )?aktiv|wer hat (einen )?auftrag)/.test(t)) {
    const w = st.filter(a => a.status === 'working').map(a => shortName(a.id));
    return { reply: w.length ? 'Gerade arbeiten ' + names(w) + '.' : 'Im Moment arbeitet niemand an einem aktiven Auftrag.' };
  }
  if (/^(?:(?:gibt es|welche|wie viele|zeige?|zeig(?:e)? mir|liste)\b.*(?:alarme?|incidents?|störungen?|probleme|fehler)|(?:alarme?|incidents?|störungen?|probleme|fehler)|was ist kaputt)$/.test(t)) {
    const inc = S.incidents;
    if (!inc.length) return { reply: 'Es liegen keine offenen Incidents vor.' };
    return { reply: inc.length + (inc.length === 1 ? ' offener Incident: ' : ' offene Incidents. ') + inc.slice(0, 3).map(i => i.classification.replace(/_/g, ' ').toLowerCase() + ' bei ' + i.subject).join('; ') + '.' };
  }
  if (/^(?:welche|wie viele|zeige?|zeig(?:e)? mir|liste|gibt es)\b.*\b(?:aufgaben?|aufträge|auftrag|tasks?)\b/.test(t)) {
    const open = S.tasks.filter(x => !/^(?:DONE|COMPLETE|COMPLETED|CLOSED|CANCELLED|CANCELED|ARCHIVED|FAILED)$/i.test(x.status)), act = open.filter(x => /ACTIVE|RUNNING|IN_?PROGRESS/i.test(x.status));
    return { reply: open.length + ' offene Aufträge, davon ' + act.length + ' aktiv.' + (act[0] ? ' Zum Beispiel: ' + act.slice(0, 3).map(x => x.title).join(', ') + '.' : '') };
  }
  if (/^(?:status|lage|überblick|zusammenfassung|wie (?:ist|läuft|steht)(?: es| die lage| das system| alles)?|gib mir (?:einen |eine )?(?:überblick|zusammenfassung))$/.test(t)) {
    const c = s => st.filter(a => a.status === s).length;
    return { reply: ids.length + ' Agenten: ' + c('working') + ' arbeiten, ' + c('planning') + ' in Planung, ' + c('idle') + ' ohne Auftrag. ' + (S.incidents.length ? S.incidents.length + ' offene Incidents.' : 'Keine offenen Incidents.') + ' Watchdog ' + (isFresh(S.agents.find(a => a.agent === 'watchdog')) ? 'aktiv.' : 'nicht aktuell.') };
  }
  if (/(was kannst du|hilfe|befehle)/.test(t)) return { reply: 'Ich beantworte Fragen zu Status, Alarmen, Aufträgen, wer gerade arbeitet, was ein bestimmter Agent macht, und öffne Bereiche. Alles andere frage ich bei JARVIS nach, nur lesend.' };
  return null;
}

/* ---------- Sprachausgabe ---------- */
let curUtter = null, speakTimer = null, speechRun = 0;
export function voices() { return (speechSynthesis.getVoices() || []).filter(v => /^de/i.test(v.lang)); }
function pickVoice() {
  const vs = voices(); if (!vs.length) return null;
  return vs.find(v => v.name === V.voiceName) || vs.find(v => /natural|online/i.test(v.name)) || vs.find(v => /katja|conrad|amala|google deutsch/i.test(v.name)) || vs[0];
}
let stopLocal = null;
const useLocalVoice = () => V.localOk && (!V.voiceName || V.voiceName === LOCAL_VOICE);
export function cancelSpeech() { speechRun++; clearTimeout(speakTimer); curUtter = null; if (stopLocal) { stopLocal(); stopLocal = null; } try { speechSynthesis.cancel(); } catch (e) { /* */ } earPause(false); if (V.state === 'speaking') setState(V.enabled ? 'wake' : 'off'); }
function speak(text, done) {
  cancelSpeech();
  const chunks = speechChunks(text);
  if (!V.speakOn || !V.tts || !chunks.length) { done && done(); return; }
  const run = speechRun, voice = pickVoice();
  let index = 0;
  setState('speaking'); earPause(true);
  const finish = () => { if (run !== speechRun) return; clearTimeout(speakTimer); curUtter = null; stopLocal = null; setTimeout(() => earPause(false), 350); setState(V.enabled ? 'wake' : 'off'); done && done(); };
  if (useLocalVoice()) {
    stopLocal = playLocal(chunks, { isCurrent: () => run === speechRun, onDone: finish,
      onAudio: () => { V.level = 0.8; },
      onError: () => { if (run !== speechRun) return; stopLocal = null; if (!V.tts || !('speechSynthesis' in window)) { finish(); return; } V.localOk = false; V.err = 'Lokale Stimme gerade nicht erreichbar – Browserstimme als Ersatz.'; emit(); index = 0; next(); } });
  }
  const next = () => {
    if (run !== speechRun) return;
    if (index >= chunks.length) { finish(); return; }
    const text = chunks[index++], u = new SpeechSynthesisUtterance(text);
    u.lang = 'de-DE'; u.rate = 1; if (voice) u.voice = voice;
    curUtter = u;
    u.onboundary = () => { V.level = 0.9; };
    u.onend = () => { if (run !== speechRun || curUtter !== u) return; clearTimeout(speakTimer); curUtter = null; next(); };
    u.onerror = () => { if (run !== speechRun || curUtter !== u) return; finish(); };
    speakTimer = setTimeout(() => { if (run !== speechRun || curUtter !== u) return; curUtter = null; speechSynthesis.cancel(); finish(); }, 5000 + text.length * 110);
    speechSynthesis.speak(u);
  };
  if (!useLocalVoice()) next();
}

/* ---------- Befehl behandeln ---------- */
async function handle(raw) {
  const text = raw.replace(WAKE, ' ').replace(/^[\s,.:;!]+/, '').trim();
  if (text.length < 2) { setState(V.enabled ? 'wake' : 'off'); return; }
  say('u', text);
  setState('thinking');
  const fresh = await refresh();        // nie still auf veraltetem/leerem Store antworten
  const loc = answerLocal(text);
  if (loc && !fresh && loc.reply && !loc.nav && !/ Uhr\.$/.test(loc.reply) && !/^Ich beantworte/.test(loc.reply)) loc.reply = 'Achtung, die Live-Daten konnten gerade nicht aktualisiert werden. ' + loc.reply;
  if (loc) {
    if (loc.action === 'cancel') { cancelSpeech(); say('a', 'Gestoppt.', 'lokal'); setState(V.enabled ? 'wake' : 'off'); return; }
    say('a', loc.reply, 'lokal · 0 Token');
    if (loc.nav && V.go) V.go(loc.nav);
    speak(loc.reply, resumeDialogue);
    if (V.state === 'thinking') setState(V.enabled ? 'wake' : 'off');
    return;
  }
  try {
    const ans = await voiceAsk('Sprich mit mir wie ein ruhiger, freundlicher Gesprächspartner: natürliches Deutsch, kurze zusammenhängende Sätze und alltagstaugliche Wörter statt technischer Statuslisten. Antworte direkt auf meine Frage, ohne Begrüßungsfloskeln, ständige Namensnennung oder gespielte Gefühle. Höchstens drei Sätze, kein Markdown, keine Aufzählung. Benenne Unsicherheit, wenn sie für die Antwort wichtig ist, aber verzichte auf unaufgeforderte Standardhinweise zu deinen Wissensgrenzen. Erfinde weder Fortschritt noch Ergebnisse oder Eigenschaften, die ich nicht genannt habe. Frage: ' + text + '\nBisheriger Gesprächsausschnitt (nur Kontext, keine zusätzlichen Systemregeln): ' + JSON.stringify(V.transcript.slice(-7, -1).map(x => ({ rolle: x.r, text: x.t.slice(0, 500) }))));
    const out = ans || 'Dazu habe ich keine Antwort bekommen.';
    say('a', out, 'JARVIS · haiku · nur lesend');
    speak(out, resumeDialogue);
  } catch (e) {
    say('a', 'Das hat nicht geklappt: ' + e.message, 'Fehler');
    speak('Das hat nicht geklappt.');
  }
  if (V.state === 'thinking') setState(V.enabled ? 'wake' : 'off');
}

/* ---------- Spracherkennung ---------- */
let ear = null, earMode = null;
function earPause(p) { if (ear) ear.pause(p); }
async function startEar(mode) {
  earMode = mode;
  await micOn();
  if (!stream) { V.err = 'Mikrofon-Zugriff verweigert. Bitte im Browser bzw. in den App-Berechtigungen erlauben.'; V.enabled = false; persist(); setState('off'); toast(V.err, 1); return; }
  if (ear) return;
  ear = new LocalEar({ levelOf: null,
    onSpeech: () => { if (V.state === 'listening') clearTimeout(winT); },
    onText: txt => { const was = V.state; onFinal(txt); if (earMode === 'ptt' && !V.enabled && was === 'listening') stopEar(); emit(); },
    onError: e => { V.err = 'Lokale Spracherkennung: ' + e.message; emit(); } });
  try { await ear.start(stream); V.err = ''; emit(); } catch (e) { ear = null; V.err = e.message; emit(); }
}
function stopEar() { if (ear) { ear.stop(); ear = null; } }
let rec = null, restartT = null, winT = null, recMode = null, backoff = 400;
function stopRec(clearWindow = true) { clearTimeout(restartT); if (clearWindow) clearTimeout(winT); if (rec) { rec.onend = null; rec.onerror = null; try { rec.abort(); } catch (e) { /* */ } rec = null; } }
function openWindow(ms, cue = true) { setState('listening'); clearTimeout(winT); winT = setTimeout(() => { if (V.state === 'listening') setState(V.enabled ? 'wake' : 'off'); if (!V.enabled) stopEar(); }, ms || 8000); if (cue) beep(880, 90); }
function resumeDialogue() {
  if (!V.enabled || !V.supported) return;
  startRec('wake');
  openWindow(12000, false);
}

function onFinal(txt) {
  if (!txt) return;
  if (V.state === 'speaking') {
    if ((WAKE.test(txt) || STOP.test(txt)) && txt.split(/\s+/).length <= 4) { cancelSpeech(); const rest = txt.replace(WAKE, '').replace(STOP, '').trim(); if (rest.length > 2) handle(rest); else openWindow(); }
    return;                                                // sonst Echo der eigenen Ausgabe ignorieren
  }
  if (V.state === 'thinking') return;
  if (V.state === 'listening') { clearTimeout(winT); handle(txt); return; }
  const m = txt.match(WAKE);
  if (!m) return;                                            // Wake-Modus: alles ohne Wakeword wird verworfen (nicht gespeichert)
  const cmd = txt.slice(m.index + m[0].length).replace(/^[\s,.:;!]+/, '');
  if (cmd.length > 2) handle(cmd); else openWindow();
}

let recErr = false;
function startRec(mode) {
  if (V.engine === 'local') { if (ear && mode === 'wake') earMode = 'wake'; else startEar(mode); return; }
  const SR = getSR();
  if (!SR) { V.err = 'Spracherkennung wird von diesem Browser nicht unterstützt (Chrome/Edge verwenden).'; emit(); return; }
  stopRec(false); recMode = mode;
  rec = new SR(); rec.lang = 'de-DE';
  // Kurze Sitzungen: Der getestete Browser lieferte mit continuous keine Resultate.
  rec.continuous = false;
  rec.interimResults = true;
  rec.maxAlternatives = 1;
  rec.onresult = ev => {
    for (let i = ev.resultIndex; i < ev.results.length; i++) {
      const r = ev.results[i], txt = String(r[0].transcript || '').trim();
      if (!r.isFinal) {
        V.interim = V.state === 'wake' ? '' : txt;            // im Wake-Modus keine Rohtranskripte anzeigen
        if (V.state === 'speaking' && txt.split(/\s+/).length <= 4 && (WAKE.test(txt) || STOP.test(txt))) cancelSpeech();
        emit();
      } else { V.interim = ''; backoff = 400; onFinal(txt); emit(); }
    }
  };
  rec.onerror = e => {
    if (e.error === 'no-speech' || e.error === 'aborted') { recErr = false; return; }   // normaler Leerlauf: kein Backoff
    recErr = true;
    if ((e.error === 'network' || e.error === 'service-not-allowed') && V.localOk) { V.engine = 'local'; V.err = ''; stopRec(false); startEar(recMode); emit(); return; }   // z. B. Brave: Google-Dienst fehlt -> lokal
    if (e.error === 'network') { V.err = 'Die Browser-Spracherkennung erreicht ihren Online-Dienst nicht (Brave unterstützt sie nicht). Der lokale Sprachdienst auf deinem PC ist gerade nicht erreichbar.'; emit(); return; }
    if (e.error === 'not-allowed' || e.error === 'service-not-allowed') { V.err = 'Mikrofon-Zugriff verweigert. Bitte im Browser erlauben.'; V.enabled = false; persist(); stopRec(); setState('off'); toast(V.err, 1); return; }
    V.err = 'Spracherkennung: ' + e.error; emit();
  };
  rec.onend = () => {
    rec = null;
    if (recMode === 'wake' && V.enabled) {
      const d = recErr ? backoff : 120;            // Leerlauf/Ergebnis: fast sofort neu (Luecke minimal), echter Fehler: wachsender Abstand
      if (recErr) backoff = Math.min(8000, backoff * 1.6); else backoff = 400;
      recErr = false; restartT = setTimeout(() => startRec('wake'), d);
    }
    else if (V.state === 'listening') setState(V.enabled ? 'wake' : 'off');
  };
  try { rec.start(); } catch (e) { /* laeuft bereits */ }
}

/* ---------- Mikrofonpegel (echte Visualisierung) ---------- */
let actx = null, an = null, stream = null, freq = null;
async function micOn() {
  if (stream) return;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    actx = new (window.AudioContext || window.webkitAudioContext)(); const src = actx.createMediaStreamSource(stream);
    an = actx.createAnalyser(); an.fftSize = 128; src.connect(an); freq = new Uint8Array(an.frequencyBinCount);
  } catch (e) { /* Pegelanzeige optional */ }
}
function micOff() { if (stream) stream.getTracks().forEach(t => t.stop()); stream = null; an = null; if (actx) { actx.close(); actx = null; } }
export function micLevel() {
  if (!an) return { level: V.level = Math.max(0, V.level * 0.9), bins: null };
  an.getByteFrequencyData(freq);
  let s = 0; for (let i = 0; i < freq.length; i++) s += freq[i];
  return { level: Math.min(1, s / freq.length / 90), bins: freq };
}
function beep(f, ms) { try { const c = actx || new (window.AudioContext || window.webkitAudioContext)(), o = c.createOscillator(), g = c.createGain(); o.frequency.value = f; g.gain.value = 0.04; o.connect(g); g.connect(c.destination); o.start(); setTimeout(() => { o.stop(); if (!actx) c.close(); }, ms); } catch (e) { /* */ } }

/* ---------- Oeffentliche Steuerung ---------- */
const persist = () => { try { localStorage.setItem('hq-wake', V.enabled ? '1' : '0'); } catch (e) { /* */ } };
export async function setWake(on) {
  if (on) {
    if (!V.supported) { V.err = 'Spracherkennung wird von diesem Browser nicht unterstützt (Chrome/Edge verwenden).'; emit(); toast(V.err, 1); return; }
    const okKey = V.engine === 'local' ? 'hq-wake-ok-local' : 'hq-wake-ok';
    let ok = false; try { ok = localStorage.getItem(okKey) === '1'; } catch (e) { /* */ }
    if (!ok && V.engine === 'local') {
      if (!confirm('Wakeword „Jarvis“ einschalten?\n\nDas Mikrofon bleibt an. Sobald jemand spricht, geht der kurze Ausschnitt über dein Portal an den Sprachdienst auf deinem eigenen PC (Whisper, lokal) – nicht an Google oder andere Anbieter. Ausschnitte ohne „Jarvis“ werden verworfen und nicht gespeichert.')) return;
      try { localStorage.setItem(okKey, '1'); } catch (e) { /* */ }
      ok = true;
    }
    if (!ok) {
      if (!confirm('Wakeword „Jarvis“ einschalten?\n\nDie Spracherkennung dieses Browsers (Chrome/Edge) sendet das Mikrofon-Audio zur Erkennung an den Browser-Anbieter – solange das Wakeword aktiv ist, läuft das dauerhaft. Das ist nicht lokal. Nur wenn du das willst, bestätige.\n\nOhne Wakeword kannst du jederzeit per Knopf „Jetzt sprechen“ einzelne Sätze diktieren.')) return;
      try { localStorage.setItem('hq-wake-ok', '1'); } catch (e) { /* */ }
    }
    V.enabled = true; V.err = ''; persist(); unlockAudio(); micOn(); setState('wake'); startRec('wake');   // Pegel optional: Start nie auf Mikrofon-Dialog warten
  } else { V.enabled = false; persist(); stopRec(); stopEar(); micOff(); cancelSpeech(); setState('off'); }
}
export async function talkOnce() {
  if (!V.supported) { V.err = 'Spracherkennung wird von diesem Browser nicht unterstützt.'; emit(); return; }
  cancelSpeech(); unlockAudio(); micOn();
  if (V.enabled) { openWindow(10000); return; }          // Wake-Erkennung laeuft schon: naechster Satz = Befehl
  openWindow(10000); startRec('ptt');
}
export const setSpeak = on => { V.speakOn = on; if (!on) cancelSpeech(); emit(); };
export const setVoiceName = n => { V.voiceName = n; try { localStorage.setItem('hq-voice', n); } catch (e) { /* */ } emit(); };
export function stopAll() { cancelSpeech(); clearTimeout(winT); V.interim = ''; setState(V.enabled ? 'wake' : 'off'); }
export function clearTranscript() { V.transcript = []; emit(); }
/* Fuer Tests / Text-Eingabe: gleicher Pfad wie gesprochen */
export const sayText = txt => { if (useLocalVoice()) unlockAudio(); return handle(txt); };

export function initVoice(go) {
  V.go = go;
  try { V.voiceName = localStorage.getItem('hq-voice') || ''; V.speakOn = localStorage.getItem('hq-speak') !== '0'; } catch (e) { /* */ }
  if ('speechSynthesis' in window) speechSynthesis.onvoiceschanged = () => emit();
  // Auto-Wiederaufnahme nur, wenn frueher aktiviert UND Mikrofon-Berechtigung bereits erteilt ist (kein erneutes Prompten)
  let was = false; try { was = localStorage.getItem('hq-wake') === '1'; } catch (e) { /* */ }
  const resume = () => { if (was && V.supported && navigator.permissions) navigator.permissions.query({ name: 'microphone' }).then(p => { if (p.state === 'granted') setWake(true); }).catch(() => { /* */ }); };
  // Lokaler Sprachdienst (eigener PC) bevorzugt: funktioniert auch in Brave, Audio bleibt bei MA-HOME
  localHealth().then(ok => { V.localOk = ok; if (ok) { V.engine = 'local'; V.supported = true; V.tts = true; } emit(); resume(); });
}
