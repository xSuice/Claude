// PRIO2 N1: Modell-Absicht als Rückfallebene hinter den Satzmustern. Aktionen weiterhin NUR nach „Ja“.
import test from 'node:test'; import assert from 'node:assert/strict';
globalThis.localStorage = { getItem: () => null, setItem: () => {} };
globalThis.document = globalThis.document || { cookie: '' };
const m = await import('./js/voicetasks.js');

function deps(intent, { running = true, local = false } = {}) {
  const calls = [], asked = [];
  return {
    calls, asked, now: () => 1000, local: () => local,
    classify: async (text, run) => { asked.push([text, run]); if (intent instanceof Error) throw intent; return intent; },
    jv: async (cmd, x) => {
      calls.push([cmd, x]);
      if (cmd === 'list') return { jobs: running ? [{ id: 'j1', request: 'Logs zusammenfassen', state: 'running', revision: 2 }] : [{ id: 'j0', request: 'Backup', state: 'done' }] };
      if (cmd === 'submit') return { job_id: 'j20261028-abcdef' };
      if (cmd === 'revise') return { revision: 3 };
      return {};
    },
  };
}

test('Satzmuster haben Vorrang: Modell wird nicht gefragt', async () => {
  m.clearPending(); const d = deps('none');
  const r = await m.handleTaskVoice('Wie weit ist mein Auftrag?', d);
  assert.match(r.reply, /Logs zusammenfassen/);
  assert.equal(d.asked.length, 0);
});

test('lokale Antwort hat Vorrang: kein Modellaufruf, nicht zuständig', async () => {
  m.clearPending(); const d = deps('progress', { local: true });
  assert.equal(await m.handleTaskVoice('Welche Aufträge sind offen?', d), null);
  assert.equal(d.asked.length, 0);
});

test('Modell: neuer Auftrag nur mit Rückfrage, Wortlaut als Auftrag, erst nach Ja angelegt', async () => {
  m.clearPending(); const d = deps('submit');
  const r = await m.handleTaskVoice('Kannst du mir die Fotos vom Oktober sortieren?', d);
  assert.ok(r.confirm); assert.match(r.reply, /Fotos vom Oktober sortieren/);
  assert.deepEqual(d.asked[0], ['Kannst du mir die Fotos vom Oktober sortieren?', 'Logs zusammenfassen']);
  assert.ok(!d.calls.some(c => c[0] === 'submit'), 'nichts ohne Ja');
  const y = await m.handleTaskVoice('Ja', d);
  assert.match(y.reply, /angelegt/);
  assert.equal(d.calls.filter(c => c[0] === 'submit')[0][1].request, 'Kannst du mir die Fotos vom Oktober sortieren');
});

test('Modell: Änderung am laufenden Auftrag mit Revision und Rückfrage', async () => {
  m.clearPending(); const d = deps('revise');
  const r = await m.handleTaskVoice('Nimm doch lieber nur die Fehler', d);
  assert.ok(r.confirm); assert.match(r.reply, /Logs zusammenfassen/);
  await m.handleTaskVoice('ja', d);
  const rv = d.calls.find(c => c[0] === 'revise')[1];
  assert.deepEqual([rv.job, rv.request, rv.expected], ['j1', 'Nimm doch lieber nur die Fehler', 2]);
});

test('Modell: Abbruch nur nach Ja, Nein verwirft', async () => {
  m.clearPending(); const d = deps('cancel');
  const r = await m.handleTaskVoice('Lass das mit den Logs, brauch ich nicht', d);
  assert.ok(r.confirm);
  assert.match((await m.handleTaskVoice('Nein', d)).reply, /mache nichts/);
  assert.ok(!d.calls.some(c => c[0] === 'cancel'));
});

test('Modell: Stand-Frage liest nur', async () => {
  m.clearPending(); const d = deps('progress');
  const r = await m.handleTaskVoice('Bist du schon fertig?', d);
  assert.match(r.reply, /Logs zusammenfassen/);
  assert.ok(!r.confirm);
  assert.equal(d.calls.filter(c => c[0] === 'list').length, 1, 'Auftragsliste nur einmal geholt');
});

test('Modell: kein laufender Auftrag wird mitgeteilt', async () => {
  m.clearPending(); const d = deps('revise', { running: false });
  const r = await m.handleTaskVoice('Und nimm noch die Unterordner mit', d);
  assert.equal(d.asked[0][1], null);
  assert.match(r.reply, /läuft gerade kein Auftrag/);
});

test('Modell sagt none, liefert null oder fällt aus: nicht zuständig (altes Verhalten)', async () => {
  for (const it of ['none', null, new Error('503')]) {
    m.clearPending(); const d = deps(it);
    assert.equal(await m.handleTaskVoice('Erzähl mir einen Witz', d), null, String(it));
  }
});

test('modelIntent: Zuordnung, Fehler, unbekannte Absicht, Zeitlimit', async () => {
  const fake = (status, body, delay = 0) => async (url, o) => {
    assert.equal(url, '/api/voice/intent');
    assert.deepEqual(JSON.parse(o.body), { text: 'Sortier die Fotos', run: 'Logs' });
    await new Promise((res, rej) => { const t = setTimeout(res, delay); o.signal?.addEventListener('abort', () => { clearTimeout(t); rej(Object.assign(new Error('abort'), { name: 'AbortError' })); }); });
    return { ok: status === 200, status, headers: { get: () => 'application/json' }, json: async () => body };
  };
  globalThis.fetch = fake(200, { intent: 'submit', text: 'Sortier die Fotos' });
  assert.equal(await m.modelIntent('Sortier die Fotos', 'Logs'), 'submit');
  globalThis.fetch = fake(503, { error: 'Qwen nicht bereit' });
  assert.equal(await m.modelIntent('Sortier die Fotos', 'Logs'), null);
  globalThis.fetch = fake(200, { intent: 'delete_all' });
  assert.equal(await m.modelIntent('Sortier die Fotos', 'Logs'), null);
  globalThis.fetch = fake(200, { intent: 'submit' }, 500);
  const t0 = Date.now();
  assert.equal(await m.modelIntent('Sortier die Fotos', 'Logs', 100), null);
  assert.ok(Date.now() - t0 < 400, 'Zeitlimit greift');
});
