// Misst, wann das Wakeword feuert relativ zum Ende von „Hey Jarvis“ (fuer das Abschneiden vor Whisper)
import * as ort from 'onnxruntime-web';
import fs from 'node:fs';
import { OwwCore } from './voice-engine.js';
const A = process.env.ASSETS;
ort.env.wasm.numThreads = 1;
function readWav16k(p) {
  const b = fs.readFileSync(p); let o = 12, fmt = null, data = null;
  while (o < b.length) { const id = b.toString('ascii', o, o + 4), sz = b.readUInt32LE(o + 4); if (id === 'fmt ') fmt = { ch: b.readUInt16LE(o + 10), rate: b.readUInt32LE(o + 12) }; if (id === 'data') data = b.subarray(o + 8, o + 8 + sz); o += 8 + sz + (sz & 1); }
  const n = data.length / 2 / fmt.ch, x = new Float32Array(n);
  for (let i = 0; i < n; i++) x[i] = data.readInt16LE(i * 2 * fmt.ch) / 32768;
  const r = fmt.rate / 16000, m = Math.floor(n / r), y = new Float32Array(m);
  for (let i = 0; i < m; i++) { const p = i * r, k = Math.floor(p), f = p - k; y[i] = x[k] * (1 - f) + (x[Math.min(k + 1, n - 1)] || 0) * f; }
  return y;
}
const lastLoud = x => { let e = 0; for (let i = 0; i < x.length; i += 160) { let q = 0; for (let j = i; j < Math.min(i + 160, x.length); j++) q += x[j] * x[j]; if (Math.sqrt(q / 160) > 0.01) e = i; } return e / 16000; };
const sess = async f => ort.InferenceSession.create(fs.readFileSync(A + '/' + f).buffer.slice(0), { executionProviders: ['wasm'] });
const core = new OwwCore(ort, { mel: await sess('melspectrogram.onnx'), emb: await sess('embedding_model.onnx'), kw: await sess('hey_jarvis_v0.1.onnx') });
for (const f of process.argv.slice(2)) {
  core.reset(); await core.warmup();
  const x = readWav16k(f), pad = 16000, all = new Float32Array(pad + x.length + 16000); all.set(x, pad);
  let fireAt = null, peakAt = null, peak = 0, t = 0;
  for (let i = 0; i < all.length; i += 512) for (const r of await core.push(all.subarray(i, i + 512))) {
    t = (i + 512) / 16000; if (r.score > peak) { peak = r.score; peakAt = t; } if (r.fired && fireAt === null) fireAt = t; }
  console.log(f, JSON.stringify({ phraseEnd: +(pad / 16000 + lastLoud(x)).toFixed(2), fireAt, peakAt, peak: +peak.toFixed(2) }));
}
