/* MA-HOME HQ — Sprach-Engine im Browser (lokal, kein Audio verlaesst das Geraet bis zum Wakeword):
   - Wakeword „Hey Jarvis“: openWakeWord (dscripka, Code Apache-2.0, vortrainiertes Modell CC BY-NC-SA 4.0 – privater Eigenbetrieb),
     Pipeline 1:1 wie openwakeword/utils.py: 80-ms-Bloecke (1280 Samples, int16-Skala), Mel auf 1280+480 Samples, x/10+2,
     Embedding je 8 Mel-Frames ueber 76 Frames, Klassifikator ueber die letzten 16 Embeddings.
   - Sprachende/-anfang: Silero VAD v5 ueber @ricky0123/vad-web (ISC) FrameProcessor + Silero-Klasse.
   - Inferenz: onnxruntime-web (MIT), nur WASM, 1 Thread (kein SharedArrayBuffer/COOP noetig).
   Wird nur bei aktivierter Sprache dynamisch geladen (eigenes Bundle). */
import * as ort from 'onnxruntime-web/wasm';
import { FrameProcessor } from '@ricky0123/vad-web/dist/frame-processor.js';
import { Message } from '@ricky0123/vad-web/dist/messages.js';
import { Silero } from '@ricky0123/vad-web/dist/models/silero.js';

export const VERSIONS = { ort: '1.22.0', vad: '0.0.31', oww: '0.5.1' };

/* ---------- openWakeWord-Kern (rein, auch in Node testbar) ---------- */
export class OwwCore {
  constructor(ortNs, sessions, { threshold = 0.5, cooldownMs = 1500 } = {}) {
    this.ort = ortNs; this.melS = sessions.mel; this.embS = sessions.emb; this.kw = sessions.kw;
    this.threshold = threshold; this.cooldownMs = cooldownMs;
    this.kwWindow = 16;
    const meta = this.kw.inputMetadata && (Array.isArray(this.kw.inputMetadata) ? this.kw.inputMetadata[0] : this.kw.inputMetadata[this.kw.inputNames[0]]);
    if (meta && Array.isArray(meta.shape) && typeof meta.shape[1] === 'number') this.kwWindow = meta.shape[1];
    this.reset();
  }
  reset() {
    this.raw = new Float32Array(0);                 // Rest < 1280
    this.tail = new Float32Array(480);              // 3*160 Samples Kontext fuer die Mel-Berechnung
    this.melRows = Array.from({ length: 76 }, () => new Float32Array(32).fill(1));   // wie np.ones((76,32))
    this.feat = [];                                 // Embeddings (96)
    this.nPred = 0; this.lastFire = -1e9; this.last = 0;
  }
  async warmup() {
    // wie utils.py: feature_buffer aus 4 s Zufallsrauschen (+-1000 int16)
    const n = 16000 * 4, x = new Float32Array(n);
    for (let i = 0; i < n; i++) x[i] = Math.round(Math.random() * 2000 - 1000);
    const spec = await this.melOf(x);
    for (let i = 0; i + 76 <= spec.length; i += 8) this.feat.push(await this.embOf(spec.slice(i, i + 76)));
    this.feat = this.feat.slice(-120);
  }
  async melOf(int16scaled) {
    const t = new this.ort.Tensor('float32', int16scaled, [1, int16scaled.length]);
    const out = await this.melS.run({ [this.melS.inputNames[0]]: t });
    const d = out[this.melS.outputNames[0]].data, frames = d.length / 32, rows = [];
    for (let f = 0; f < frames; f++) { const r = new Float32Array(32); for (let j = 0; j < 32; j++) r[j] = d[f * 32 + j] / 10 + 2; rows.push(r); }
    return rows;
  }
  async embOf(rows76) {
    const flat = new Float32Array(76 * 32); rows76.forEach((r, i) => flat.set(r, i * 32));
    const out = await this.embS.run({ [this.embS.inputNames[0]]: new this.ort.Tensor('float32', flat, [1, 76, 32, 1]) });
    return new Float32Array(out[this.embS.outputNames[0]].data);
  }
  /* Float32-Audio (-1..1, 16 kHz) anhaengen; gibt Liste {score, fired} je fertigem 80-ms-Block zurueck */
  async push(samples) {
    const buf = new Float32Array(this.raw.length + samples.length); buf.set(this.raw); buf.set(samples, this.raw.length);
    const res = []; let off = 0;
    while (buf.length - off >= 1280) {
      const block = new Float32Array(1280);
      for (let i = 0; i < 1280; i++) block[i] = Math.max(-32768, Math.min(32767, Math.round(buf[off + i] * 32767)));
      off += 1280;
      const inp = new Float32Array(1760); inp.set(this.tail); inp.set(block, 480);
      this.tail = block.slice(800);
      const rows = await this.melOf(inp);
      this.melRows.push(...rows); if (this.melRows.length > 970) this.melRows = this.melRows.slice(-970);
      this.feat.push(await this.embOf(this.melRows.slice(-76))); if (this.feat.length > 120) this.feat = this.feat.slice(-120);
      const win = this.feat.slice(-this.kwWindow), flat = new Float32Array(this.kwWindow * 96);
      win.forEach((e, i) => flat.set(e, i * 96));
      const out = await this.kw.run({ [this.kw.inputNames[0]]: new this.ort.Tensor('float32', flat, [1, this.kwWindow, 96]) });
      let score = out[this.kw.outputNames[0]].data[0];
      if (++this.nPred <= 5) score = 0;              // wie model.py: die ersten 5 Vorhersagen nach Start verwerfen
      this.last = score;
      const now = (globalThis.performance || Date).now();
      const fired = score >= this.threshold && now - this.lastFire > this.cooldownMs;
      if (fired) this.lastFire = now;
      res.push({ score, fired });
    }
    this.raw = buf.slice(off);
    return res;
  }
}

/* ---------- WAV (PCM16, 16 kHz, mono) fuer den lokalen Whisper ---------- */
export function encodeWav(f32, rate = 16000) {
  const b = new ArrayBuffer(44 + f32.length * 2), v = new DataView(b);
  const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  w(0, 'RIFF'); v.setUint32(4, 36 + f32.length * 2, true); w(8, 'WAVE'); w(12, 'fmt ');
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, rate, true);
  v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); w(36, 'data'); v.setUint32(40, f32.length * 2, true);
  for (let i = 0; i < f32.length; i++) v.setInt16(44 + i * 2, Math.max(-1, Math.min(1, f32[i])) * 0x7fff, true);
  return new Blob([b], { type: 'audio/wav' });
}

/* ---------- Browser-Engine: Mikrofonstrom -> Worklet (16 kHz) -> VAD + Wakeword ---------- */
const fetchBuf = async url => { const r = await fetch(url, { credentials: 'same-origin' }); if (!r.ok) throw new Error(url.split('/').pop() + ': HTTP ' + r.status); return r.arrayBuffer(); };

export async function createEngine({ base, stream, threshold = 0.5, onWake, onScore, onSpeechStart, onSpeechEnd, onMisfire, onError, maxSpeechMs = 25000 }) {
  const V = base + 'vendor/';
  ort.env.wasm.wasmPaths = V + 'ort-' + VERSIONS.ort + '/';
  ort.env.wasm.numThreads = 1; ort.env.wasm.proxy = false;
  const opt = { executionProviders: ['wasm'], graphOptimizationLevel: 'all' };
  const M = V + 'oww-' + VERSIONS.oww + '/';
  const [melB, embB, kwB, vadB] = await Promise.all([fetchBuf(M + 'melspectrogram.onnx'), fetchBuf(M + 'embedding_model.onnx'), fetchBuf(M + 'hey_jarvis_v0.1.onnx'), fetchBuf(V + 'vad-' + VERSIONS.vad + '/silero_vad_v5.onnx')]);
  const [mel, emb, kw] = await Promise.all([ort.InferenceSession.create(melB, opt), ort.InferenceSession.create(embB, opt), ort.InferenceSession.create(kwB, opt)]);
  const oww = new OwwCore(ort, { mel, emb, kw }, { threshold });
  await oww.warmup();
  const silero = await Silero.new(ort, async () => vadB);
  const fp = new FrameProcessor(silero.process, silero.reset_state, {
    positiveSpeechThreshold: 0.5, negativeSpeechThreshold: 0.35, preSpeechPadMs: 480, redemptionMs: 900, minSpeechMs: 250, submitUserSpeechOnPause: false
  }, 32);
  fp.resume();

  const ac = new (window.AudioContext || window.webkitAudioContext)();
  await ac.audioWorklet.addModule(V + 'pcm16k-worklet.js');
  const src = ac.createMediaStreamSource(stream), node = new AudioWorkletNode(ac, 'pcm16k'), mute = ac.createGain();
  mute.gain.value = 0; src.connect(node); node.connect(mute); mute.connect(ac.destination);

  let queue = Promise.resolve(), vadOn = true, wakeOn = true, speechFrames = 0, closed = false, level = 0;
  const st = { frames: 0, lastScore: 0, maxScore: 0, busyMs: 0 };
  const handle = ev => {
    if (ev.msg === Message.SpeechStart) { speechFrames = 0; onSpeechStart && onSpeechStart(); }
    else if (ev.msg === Message.SpeechEnd) { speechFrames = 0; onSpeechEnd && onSpeechEnd(ev.audio); }
    else if (ev.msg === Message.VADMisfire) { speechFrames = 0; onMisfire && onMisfire(); }
    else if (ev.msg === Message.FrameProcessed && fp.speaking && ++speechFrames * 32 > maxSpeechMs) fp.endSegment(handle);   // harte Obergrenze
  };
  const step = async frame => {
    if (closed) return;
    const t0 = performance.now();
    let q = 0; for (let i = 0; i < frame.length; i++) q += frame[i] * frame[i]; level = Math.sqrt(q / frame.length);
    if (vadOn) await fp.process(frame, handle);
    if (wakeOn) {
      for (const r of await oww.push(frame)) {
        st.lastScore = r.score; st.maxScore = Math.max(st.maxScore, r.score);
        onScore && onScore(r.score);
        if (r.fired && onWake) onWake(r.score, fp.speaking ? fp.audioBuffer.length * 512 : null);   // Position im laufenden Sprachsegment (Samples)
      }
    }
    st.frames++; st.busyMs = st.busyMs * 0.95 + (performance.now() - t0) * 0.05;
  };
  node.port.onmessage = e => { queue = queue.then(() => step(e.data)).catch(err => onError && onError(err)); };
  if (ac.state === 'suspended') { try { await ac.resume(); } catch (e) { /* braucht Nutzergeste */ } }

  return {
    stats: () => ({ ...st, level, vadOn, wakeOn, speaking: fp.speaking, ctx: ac.state, rate: ac.sampleRate }),
    resume: () => ac.resume(),
    setThreshold: t => { oww.threshold = t; },
    setVad: on => { if (on === vadOn) return; vadOn = on; if (on) { fp.reset(); fp.resume(); } else fp.pause(() => {}); },
    setWake: on => { wakeOn = on; },
    endSpeech: () => fp.endSegment(handle),
    resetMax: () => { st.maxScore = 0; },
    async close() { closed = true; node.port.onmessage = null; try { src.disconnect(); node.disconnect(); } catch (e) { /* */ } try { await ac.close(); } catch (e) { /* */ } }
  };
}
