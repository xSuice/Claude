/* MA-HOME HQ — lokale Sprachstrecke: Mikrofon -> eigener PC (faster-whisper) -> Text, Text -> eigener PC (Piper Thorsten) -> Audio.
   Kein Google/Browser-Anbieter: Audio geht nur ueber das Portal (Authelia) an den lokalen Sprachdienst des Owners.
   Sprach-Segmentierung per Pegel (VAD) im Browser; der Recorder laeuft immer schon vor dem Sprechbeginn (kein abgeschnittener Anfang). */
import { api } from './api.js';

export const LOCAL_VOICE = 'jarvis-local';

/* Reine Zustandsmaschine fuer Sprachsegmente: feed(level, now) -> null | 'speech' | 'send' | 'discard' */
export function createSegmenter({ threshold = 0.2, startMs = 120, silenceMs = 650, maxMs = 14000, idleMs = 6000 } = {}) {
  let loudSince = null, speaking = false, lastLoud = 0, segStart = null, floor = 0, born = null, peak = 0, sum = 0, n = 0;
  return {
    get speaking() { return speaking; },
    get threshold() { return Math.max(threshold, floor + 0.15); },
    begin(now) { segStart = now; loudSince = null; speaking = false; lastLoud = now; },
    feed(level, now) {
      if (segStart === null) segStart = now;
      if (born === null) born = now;
      if (now - born < 600) { floor = floor * 0.8 + level * 0.2; return null; }   // Kalibrierung auf Raumrauschen
      const thr = Math.max(threshold, floor + 0.15);
      if (!speaking) floor = floor * 0.99 + level * 0.01;   // Raumgeraeusch langsam nachfuehren (auch anhaltend lautes)
      if (speaking) { peak = Math.max(peak, level); sum += level; n++; }
      const endThr = speaking ? Math.max(thr, peak - 0.25) : thr;   // Sprechende relativ zur eigenen Lautstaerke (robust bei Raumgeraeusch)
      if (level >= endThr) {
        lastLoud = now;
        if (!speaking) { if (loudSince === null) loudSince = now; if (now - loudSince >= startMs) { speaking = true; peak = level; sum = 0; n = 0; return 'speech'; } }
      } else if (!speaking) loudSince = null;
      if (speaking && (now - lastLoud >= silenceMs || now - segStart >= maxMs)) {
        if (now - segStart >= maxMs && n) floor = Math.max(floor, sum / n - 0.1);   // Dauergeraeusch statt Sprache: Schwelle anheben
        speaking = false; return 'send';
      }
      if (!speaking && now - segStart >= idleMs) return 'discard';
      return null;
    }
  };
}

/* Pegel in dBFS auf 0..1: -65 dB (Stille) -> 0, -15 dB (laute Sprache) -> 1 */
export const dbLevel = rms => Math.max(0, Math.min(1, (20 * Math.log10(Math.max(rms, 1e-6)) + 65) / 50));

export function pickMime(MR = globalThis.MediaRecorder) {
  if (!MR || !MR.isTypeSupported) return '';
  return ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/webm', 'audio/mp4'].find(t => MR.isTypeSupported(t)) || '';
}

export async function blobToBase64(blob) {
  const buf = new Uint8Array(await blob.arrayBuffer());
  let s = '';
  for (let i = 0; i < buf.length; i += 0x8000) s += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
  return btoa(s);
}

export async function localHealth() {
  try { const d = await api('/api/voice/health'); return !!(d && d.ok); } catch (e) { return false; }
}

export async function transcribe(blob) {
  if (blob.size > 90 * 1024) throw new Error('Aufnahme zu lang');
  const d = await api('/api/voice/stt', { body: { mime: blob.type || 'audio/webm', audio_b64: await blobToBase64(blob) } });
  return String((d && d.text) || '').trim();
}

/* WAV (16 kHz PCM aus der Browser-Engine) -> eigener PC. Portal-Route erlaubt fuer STT bis 1,2 MB Audio (~37 s). */
export const MAX_WAV = 1200 * 1024;
export async function transcribeWav(blob) {
  if (blob.size > MAX_WAV) throw new Error('Aufnahme zu lang');
  const d = await api('/api/voice/stt', { body: { mime: 'audio/wav', audio_b64: await blobToBase64(blob) } });
  return String((d && d.text) || '').trim();
}

/* Wakeword-Anrede vorne entfernen: „Hey Jarvis, wie spät …“ -> „wie spät …“. Nur in den ersten Wörtern suchen. */
export function stripWake(text, wake) {
  const t = String(text || '').trim(), m = t.match(wake);
  if (m && m.index <= 24) return t.slice(m.index + m[0].length).replace(/^[\s,.:;!?-]+/, '').trim();
  // Reststueck der Anrede, wenn das Audio direkt nach „Hey Jarvis“ abgeschnitten wurde („vis, wie spät …“)
  return t.replace(/^(?:hey|hei|hej|he|ey|okay|ok)\b[\s,.!]*/i, '').replace(/^(?:a?r?vis|wis|vis)\b[\s,.!]*/i, '').trim();
}

export async function synthesize(text) {
  const r = await fetch('/api/voice/tts', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-MA-Request': '1' }, body: JSON.stringify({ text }) });
  if (!r.ok) throw new Error('Sprachausgabe ' + r.status);
  return r.blob();
}

/* Dauer-Mikrofon mit Segmentierung. onText(text) bekommt jede erkannte Aeusserung. */
export class LocalEar {
  constructor({ onText, onError, onSpeech, levelOf }) {
    Object.assign(this, { onText, onError, onSpeech, levelOf });
    this.stream = null; this.rec = null; this.chunks = []; this.timer = null; this.paused = false; this.busy = 0; this.on = false;
    this.seg = createSegmenter();
  }
  async start(stream) {
    if (this.on) return;
    this.stream = stream; this.mime = pickMime();
    if (!this.levelOf) {
      const ac = new (window.AudioContext || window.webkitAudioContext)(), an = ac.createAnalyser(); an.fftSize = 1024;
      ac.createMediaStreamSource(stream).connect(an); const buf = new Float32Array(an.fftSize); this.ac = ac;
      this.levelOf = () => { an.getFloatTimeDomainData(buf); let q = 0; for (let i = 0; i < buf.length; i++) q += buf[i] * buf[i]; return dbLevel(Math.sqrt(q / buf.length)); };
    }
    if (!this.mime) throw new Error('Dieser Browser kann kein Audio aufnehmen (MediaRecorder fehlt).');
    this.on = true; this.restart();
    this.timer = setInterval(() => this.tick(), 50);
  }
  restart() {
    if (!this.on) return;
    if (this.rec && this.rec.state !== 'inactive') { this.rec.ondataavailable = null; this.rec.onstop = null; try { this.rec.stop(); } catch (e) { /* */ } }
    const chunks = [];
    const rec = new MediaRecorder(this.stream, { mimeType: this.mime, audioBitsPerSecond: 24000 });
    rec.ondataavailable = e => { if (e.data && e.data.size) chunks.push(e.data); };
    rec._chunks = chunks;
    this.rec = rec; rec.start(); this.seg.begin(performance.now());
  }
  tick() {
    if (!this.on || !this.rec) return;
    const lvl = this.paused ? 0 : this.levelOf(), ev = this.seg.feed(lvl, performance.now());
    if (window.__voiceDebug) (window.__voiceTrace = window.__voiceTrace || []).push([Math.round(performance.now()), Math.round(lvl * 1000), Math.round(this.seg.threshold * 1000), ev || '']);
    if (ev === 'speech' && this.onSpeech) this.onSpeech();
    if (ev === 'discard') this.restart();
    if (ev === 'send') this.flush();
  }
  flush() {
    const rec = this.rec, mime = this.mime;
    rec.onstop = async () => {
      const blob = new Blob(rec._chunks, { type: mime.split(';')[0] });
      this.busy++;
      try { const t = await transcribe(blob); if (t && !this.paused) this.onText(t); }
      catch (e) { this.onError && this.onError(e); }
      finally { this.busy--; }
    };
    try { rec.stop(); } catch (e) { /* */ }
    this.rec = null;
    this.restart();
  }
  pause(p) { this.paused = p; if (p && this.seg.speaking) this.restart(); }
  stop() {
    this.on = false; clearInterval(this.timer); this.timer = null;
    if (this.rec && this.rec.state !== 'inactive') { this.rec.onstop = null; try { this.rec.stop(); } catch (e) { /* */ } }
    this.rec = null; this.chunks = [];
    if (this.ac) { try { this.ac.close(); } catch (e) { /* */ } this.ac = null; this.levelOf = null; }
  }
}

/* Fluessige Ausgabe ueber Web Audio (zuverlaessiges Ende-Ereignis): naechster Satz wird erzeugt, waehrend der aktuelle spielt. */
let outCtx = null;
export function unlockAudio() {
  try { if (!outCtx) outCtx = new (window.AudioContext || window.webkitAudioContext)(); if (outCtx.state === 'suspended') outCtx.resume(); } catch (e) { /* */ }
  return outCtx;
}
export function playLocal(chunks, { onDone, onError, isCurrent, onAudio }) {
  let i = 0, src = null, guard = null, stopped = false;
  const ctx = unlockAudio();
  if (!ctx) { onError(new Error('Keine Audioausgabe')); return () => {}; }
  const fetchNext = () => i < chunks.length ? synthesize(chunks[i++]).then(b => b.arrayBuffer()).then(a => ctx.decodeAudioData(a)) : null;
  let pending = fetchNext();
  const step = async () => {
    if (stopped || !isCurrent()) return;
    if (!pending && chunks.open) { setTimeout(() => { if (stopped || !isCurrent()) return; pending = fetchNext(); step(); }, 120); return; }   // Strom: auf naechsten Satz warten
    if (!pending) { onDone(); return; }
    let buf;
    try { buf = await pending; } catch (e) { if (!stopped) onError(e); return; }
    if (stopped || !isCurrent()) return;
    pending = fetchNext();
    if (ctx.state === 'suspended') { try { await ctx.resume(); } catch (e) { /* */ } }
    src = ctx.createBufferSource(); src.buffer = buf; src.connect(ctx.destination);
    let done = false;
    const next = () => { if (done) return; done = true; clearTimeout(guard); step(); };
    src.onended = next;
    guard = setTimeout(next, buf.duration * 1000 + 2500);   // Sicherheitsnetz, falls das Ende-Ereignis ausbleibt
    onAudio && onAudio(buf);
    src.start();
  };
  step();
  return () => { stopped = true; clearTimeout(guard); if (src) { src.onended = null; try { src.stop(); } catch (e) { /* */ } } };
}

/* Gespräch mit Qwen lokal auf dem PC (über das Portal). Wirft bei „nicht bereit“ (503), damit der Aufrufer Claude nimmt. */
export async function warmChat() {
  try { const r = await fetch('/api/voice/warm', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-MA-Request': '1' }, body: '{}' }); return (await r.json()).state || 'off'; } catch (e) { return 'off'; }
}
export async function qwenChat(messages, onPartial, signal) {
  const r = await fetch('/api/voice/chat', { method: 'POST', credentials: 'same-origin', signal, headers: { 'Content-Type': 'application/json', 'X-MA-Request': '1' }, body: JSON.stringify({ messages }) });
  if (!r.ok || !r.body) { let st = ''; try { st = (await r.json()).state || ''; } catch (e) { /* */ } const err = new Error('Qwen nicht bereit'); err.state = st; err.status = r.status; throw err; }
  const rd = r.body.getReader(), dec = new TextDecoder(); let buf = '', text = '';
  for (;;) {
    const { value, done } = await rd.read(); if (done) break;
    buf += dec.decode(value, { stream: true }); let i;
    while ((i = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, i); buf = buf.slice(i + 1);
      let o; try { o = JSON.parse(line); } catch (e) { continue; }
      if (o.t) { text += o.t; if (onPartial) onPartial(text); }
    }
  }
  if (!text.trim()) throw new Error('Qwen leer');
  return text.trim();
}
