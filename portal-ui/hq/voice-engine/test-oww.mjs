// Node-Test fuer OwwCore + VAD: echte Modelle, echte Audiodateien (Piper Thorsten + Referenzaufnahme aus openwakeword_wasm)
import * as ort from 'onnxruntime-web';
import fs from 'node:fs';
import { OwwCore } from './voice-engine.js';
import { FrameProcessor } from '@ricky0123/vad-web/dist/frame-processor.js';
import { Message } from '@ricky0123/vad-web/dist/messages.js';
import { Silero } from '@ricky0123/vad-web/dist/models/silero.js';

const A = process.env.ASSETS;
ort.env.wasm.numThreads = 1;
function readWav16k(p) {
  const b = fs.readFileSync(p); let o = 12, fmt = null, data = null;
  while (o < b.length) { const id = b.toString('ascii', o, o + 4), sz = b.readUInt32LE(o + 4); if (id === 'fmt ') fmt = { ch: b.readUInt16LE(o + 10), rate: b.readUInt32LE(o + 12), bits: b.readUInt16LE(o + 22) }; if (id === 'data') data = b.subarray(o + 8, o + 8 + sz); o += 8 + sz + (sz & 1); }
  const n = data.length / 2 / fmt.ch, x = new Float32Array(n);
  for (let i = 0; i < n; i++) x[i] = data.readInt16LE(i * 2 * fmt.ch) / 32768;
  if (fmt.rate === 16000) return x;
  const r = fmt.rate / 16000, m = Math.floor(n / r), y = new Float32Array(m);
  for (let i = 0; i < m; i++) { const p = i * r, k = Math.floor(p), f = p - k; y[i] = x[k] * (1 - f) + (x[Math.min(k + 1, n - 1)] || 0) * f; }
  return y;
}
const sess = async f => ort.InferenceSession.create(fs.readFileSync(A + '/' + f).buffer.slice(0), { executionProviders: ['wasm'] });
const core = new OwwCore(ort, { mel: await sess('melspectrogram.onnx'), emb: await sess('embedding_model.onnx'), kw: await sess('hey_jarvis_v0.1.onnx') });
await core.warmup();
const silent = new Float32Array(16000);
async function maxScore(x) {
  core.reset(); await core.warmup();
  const all = new Float32Array(silent.length * 2 + x.length); all.set(silent); all.set(x, silent.length);
  let mx = 0, fired = 0, t0 = Date.now();
  for (let i = 0; i < all.length; i += 512) for (const r of await core.push(all.subarray(i, i + 512))) { mx = Math.max(mx, r.score); fired += r.fired; }
  return { max: +mx.toFixed(3), fired, msPerSec: Math.round((Date.now() - t0) / (all.length / 16000)) };
}
const files = process.argv.slice(2);
const out = {};
for (const f of files) out[f.split(/[\\/]/).pop()] = await maxScore(readWav16k(f));
// VAD-Segmentierung auf der ersten Datei
const vadBuf = fs.readFileSync(process.env.VADMODEL).buffer.slice(0);
const sil = await Silero.new(ort, async () => vadBuf);
const fp = new FrameProcessor(sil.process, sil.reset_state, { positiveSpeechThreshold: 0.5, negativeSpeechThreshold: 0.35, preSpeechPadMs: 480, redemptionMs: 900, minSpeechMs: 250, submitUserSpeechOnPause: false }, 32);
fp.resume();
const ev = [];
const x = readWav16k(files[0]); const all = new Float32Array(16000 + x.length + 32000); all.set(x, 16000);
for (let i = 0; i + 512 <= all.length; i += 512) await fp.process(all.slice(i, i + 512), e => { if (e.msg === Message.SpeechStart) ev.push(['start', i / 16000]); if (e.msg === Message.SpeechEnd) ev.push(['end', i / 16000, e.audio.length / 16000]); });
out.vad = ev.map(e => e.map(v => typeof v === 'number' ? +v.toFixed(2) : v));
console.log(JSON.stringify(out));
