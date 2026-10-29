// PRIO2 N4: Gedächtnis per Sprache – Merken/Vergessen nur nach „Ja“, Auflisten lesend, Fakten als Gesprächskontext.
import test from 'node:test'; import assert from 'node:assert/strict';
globalThis.localStorage = { getItem: () => null, setItem: () => {} };
globalThis.document = globalThis.document || { cookie: '' };
const M = await import('./js/memoryvoice.js');

test('parseMemory: merken, vergessen, auflisten – und was NICHT dazugehört', () => {
  assert.deepEqual(M.parseMemory('Merk dir, dass ich Java 21 bevorzuge'), { kind: 'remember', text: 'ich Java 21 bevorzuge' });
  assert.deepEqual(M.parseMemory('Merke dir bitte: Mein Server heißt ma-server.'), { kind: 'remember', text: 'Mein Server heißt ma-server' });
  assert.deepEqual(M.parseMemory('Notier dir, dass ich morgens Tee trinke'), { kind: 'remember', text: 'ich morgens Tee trinke' });
  assert.deepEqual(M.parseMemory('Vergiss, dass ich Tee trinke'), { kind: 'forget', text: 'ich Tee trinke' });
  for (const s of ['Was weißt du über mich?', 'Was hast du dir alles gemerkt?', 'Was hast du dir über mich gemerkt']) assert.equal(M.parseMemory(s).kind, 'list', s);
  for (const s of ['Vergiss es', 'Vergiss den Auftrag', 'vergiss das', 'Merk dir', 'Wie spät ist es?', 'Ich merke mir das selbst']) assert.equal(M.parseMemory(s), null, s);
});

function deps(items = []) {
  const calls = [];
  return { calls, now: () => 1000, jv: async (cmd, x) => {
    calls.push([cmd, x]);
    if (cmd === 'memories') return { items };
    if (cmd === 'remember') { if (/sk-/.test(x.request)) throw new Error('Das sieht nach einem Zugangsdatum aus – so etwas speichere ich nicht.'); return { id: 'm1', status: 'confirmed' }; }
    if (cmd === 'forget') return { id: x.ident, status: 'retracted' };
    return {};
  } };
}

test('merken: erst Rückfrage, nach Ja gespeichert, nach Nein nichts', async () => {
  M.clearMemoryPending(); let d = deps();
  const r = await M.handleMemoryVoice('Merk dir, dass ich Java 21 bevorzuge', d);
  assert.ok(r.confirm); assert.match(r.reply, /Java 21/);
  assert.equal(d.calls.length, 0);
  assert.match((await M.handleMemoryVoice('Ja', d)).reply, /gemerkt/i);
  assert.deepEqual(d.calls[0], ['remember', { request: 'ich Java 21 bevorzuge' }]);
  M.clearMemoryPending(); d = deps();
  await M.handleMemoryVoice('Merk dir: Ich mag Tee', d);
  assert.match((await M.handleMemoryVoice('Nein', d)).reply, /nicht/);
  assert.equal(d.calls.length, 0);
});

test('merken: Ablehnung der Engine (Zugangsdatum) wird ehrlich gesagt', async () => {
  M.clearMemoryPending(); const d = deps();
  await M.handleMemoryVoice('Merk dir, mein Key ist sk-ant-xyz123456', d);
  assert.match((await M.handleMemoryVoice('Ja', d)).reply, /Zugangsdatum/);
});

test('auflisten: lesend, höchstens fünf, ohne Einträge ehrlich', async () => {
  M.clearMemoryPending();
  assert.match((await M.handleMemoryVoice('Was weißt du über mich?', deps([]))).reply, /noch nichts/);
  const items = Array.from({ length: 7 }, (_, i) => ({ id: 'm' + i, content: 'Fakt ' + i }));
  const r = await M.handleMemoryVoice('Was weißt du über mich?', deps(items));
  assert.match(r.reply, /7 Dinge/); assert.match(r.reply, /Fakt 0/); assert.doesNotMatch(r.reply, /Fakt 5/);
  assert.ok(!r.confirm);
});

test('vergessen: passende Erinnerung finden, Rückfrage, nach Ja zurückgezogen', async () => {
  M.clearMemoryPending();
  const d = deps([{ id: 'a1', content: 'ich morgens Tee trinke' }, { id: 'b2', content: 'Mein Server heißt ma-server' }]);
  const r = await M.handleMemoryVoice('Vergiss, dass ich Tee trinke', d);
  assert.ok(r.confirm); assert.match(r.reply, /morgens Tee/);
  await M.handleMemoryVoice('Ja', d);
  assert.deepEqual(d.calls.find(c => c[0] === 'forget')[1], { kind: 'memory', ident: 'a1' });
  M.clearMemoryPending();
  assert.match((await M.handleMemoryVoice('Vergiss, dass ich Fahrrad fahre', d)).reply, /nichts gemerkt/);
});

test('Gesprächskontext: Fakten werden gecacht und nach Merken/Vergessen neu geladen', async () => {
  M.clearMemoryPending(); let t = 1000;
  const d = deps([{ id: 'a1', content: 'ich Java 21 bevorzuge' }]); d.now = () => t;
  assert.deepEqual(await M.memoryFacts(d), ['ich Java 21 bevorzuge']);
  await M.memoryFacts(d);
  assert.equal(d.calls.filter(c => c[0] === 'memories').length, 1, 'Cache');
  await M.handleMemoryVoice('Merk dir: Ich mag Tee', d); await M.handleMemoryVoice('Ja', d);
  await M.memoryFacts(d);
  assert.equal(d.calls.filter(c => c[0] === 'memories').length, 2, 'nach Merken neu geladen');
  assert.match(M.factsPrefix(['ich Java 21 bevorzuge']), /Andrew/);
  assert.equal(M.factsPrefix([]), '');
});
