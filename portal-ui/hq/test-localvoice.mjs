import test from 'node:test'; import assert from 'node:assert/strict';
import { createSegmenter, pickMime, blobToBase64, dbLevel } from './js/localvoice.js';

test('segmenter sends after speech followed by silence', () => {
  const s = createSegmenter(); s.begin(0); const ev = [];
  for (let t = 0; t <= 3000; t += 50) { const lvl = t >= 500 && t < 1500 ? 0.5 : 0.01; const e = s.feed(lvl, t); if (e) ev.push([e, t]); }
  assert.deepEqual(ev.map(x => x[0]), ['speech', 'send']);
  assert.ok(ev[1][1] >= 1500 + 900 - 50);
});
test('short click is not speech; idle segment is discarded to bound size', () => {
  const s = createSegmenter(); s.begin(0); const ev = [];
  for (let t = 0; t <= 6500; t += 50) { const e = s.feed(t === 1000 ? 0.9 : 0.01, t); if (e) { ev.push(e); s.begin(t); } }
  assert.deepEqual(ev, ['discard']);
});
test('long speech is cut at max length', () => {
  const s = createSegmenter({ maxMs: 3000 }); s.begin(0); const ev = [];
  for (let t = 0; t <= 4000; t += 50) { const e = s.feed(t < 700 ? 0.01 : 0.5, t); if (e) ev.push([e, t]); }
  assert.equal(ev[0][0], 'speech'); assert.equal(ev[1][0], 'send'); assert.ok(ev[1][1] <= 3050);
});
test('threshold adapts to steady background noise', () => {
  const s = createSegmenter(); s.begin(0);
  const ev = []; for (let t = 0; t < 5000; t += 50) { const e = s.feed(0.08, t); if (e) ev.push(e); }
  assert.deepEqual(ev, []);
  assert.ok(s.threshold > 0.06);
});
test('mime selection prefers opus and base64 encodes exactly', async () => {
  assert.equal(pickMime({ isTypeSupported: t => t === 'audio/mp4' }), 'audio/mp4');
  assert.equal(pickMime({ isTypeSupported: () => true }), 'audio/webm;codecs=opus');
  assert.equal(pickMime(undefined), '');
  assert.equal(await blobToBase64(new Blob([new Uint8Array([0, 255, 10, 65])])), 'AP8KQQ==');
});

test('speech end is detected relative to own loudness even with raised room noise', () => {
  const s = createSegmenter(); s.begin(0); const ev = [];
  for (let t = 0; t <= 6000; t += 50) { const lvl = t < 1000 ? 0.05 : t < 2500 ? 0.9 : 0.55; const e = s.feed(lvl, t); if (e) ev.push([e, t]); }
  assert.deepEqual(ev.map(x => x[0]).slice(0, 2), ['speech', 'send']);
  assert.ok(ev[1][1] < 4000);
});
test('dB level mapping', () => {
  assert.equal(dbLevel(0), 0);
  assert.ok(Math.abs(dbLevel(10 ** (-40 / 20)) - 0.5) < 1e-9);
  assert.equal(dbLevel(1), 1);
});

test('sustained loud background stops re-triggering after a while', () => {
  const s = createSegmenter(); s.begin(0); const ev = [];
  for (let t = 0; t <= 60000; t += 50) { const e = s.feed(t < 1000 ? 0.05 : 0.55, t); if (e) { ev.push([e, t]); if (e !== 'speech') s.begin(t); } }
  assert.ok(!ev.some(([e, t]) => e === 'speech' && t > 30000), JSON.stringify(ev.slice(-4)));
});
