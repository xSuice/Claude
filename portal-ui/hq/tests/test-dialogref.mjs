// PRIO2 N2: Gesprächsbezug – Rückfrage „neu oder ändern?“ statt Raten; Bezugslogik als reine Funktion getestet.
import test from 'node:test'; import assert from 'node:assert/strict';
globalThis.localStorage = { getItem: () => null, setItem: () => {} };
globalThis.document = globalThis.document || { cookie: '' };
const m = await import('./js/voicetasks.js');
const R = await import('./js/dialogref.js');
const RUN = 'Build des Crimson-Zone-Plugins mit Java 21';

test('Umlaute an Wortgrenzen (Regression: \\b kennt kein ä/ü)', () => {
  assert.ok(R.refersToRun('Ändere das bitte auf nächste Woche', RUN));
  assert.equal(R.resolveIntent('progress', 'Ich brauche eine Übersicht über den Speicherplatz', null), 'submit');
});

test('resolveIntent: Bezug bestätigt, Widerspruch -> Rückfrage, ohne Auftrag unverändert', () => {
  assert.equal(R.resolveIntent('revise', 'Nimm dabei lieber Java 25', RUN), 'revise');
  assert.equal(R.resolveIntent('revise', 'Räum den Eingangsordner auf', RUN), 'choose');
  assert.equal(R.resolveIntent('submit', 'Lösch die doppelten Bilder im Ordner Urlaub', RUN), 'submit');
  assert.equal(R.resolveIntent('submit', 'Und teste das Plugin dann auch', RUN), 'choose');
  assert.equal(R.resolveIntent('revise', 'Räum den Eingangsordner auf', null), 'revise');      // ohne Auftrag meldet voicetasks „läuft kein Auftrag“
  assert.equal(R.resolveIntent('progress', 'Hat das geklappt?', RUN), 'progress');
  assert.equal(R.resolveIntent('cancel', 'Stopp', RUN), 'cancel');
  assert.equal(R.resolveIntent('none', 'Danke', RUN), 'none');
});

test('neu / ändern erkennen', () => {
  for (const s of ['neu', 'Neu.', 'neuer Auftrag', 'ein neuer', 'Neu bitte']) assert.ok(R.isNew(s), s);
  for (const s of ['ändern', 'Ändern!', 'den laufenden', 'Änderung']) assert.ok(R.isChange(s), s);
  assert.ok(!R.isNew('Neuer Auftrag: fasse die Logs zusammen'));
});

function deps(intent) {
  const calls = [];
  return { calls, now: () => 1000, local: () => false, classify: async () => intent,
    jv: async (cmd, x) => { calls.push([cmd, x]); if (cmd === 'list') return { jobs: [{ id: 'j1', request: RUN, state: 'running', revision: 4 }] }; if (cmd === 'submit') return { job_id: 'j20261028-aaaaaa' }; if (cmd === 'revise') return { revision: 5 }; return {}; } };
}

test('Widerspruch -> Rückfrage nennt Wortlaut und laufenden Auftrag; „neu“ legt an', async () => {
  m.clearPending(); const d = deps('revise');
  const r = await m.handleTaskVoice('Räum den Eingangsordner auf', d);
  assert.ok(r.confirm); assert.match(r.reply, /Räum den Eingangsordner auf/); assert.match(r.reply, /Crimson-Zone/); assert.match(r.reply, /neu.*ändern/s);
  assert.equal(d.calls.filter(c => c[0] !== 'list').length, 0, 'nichts ohne Antwort');
  const y = await m.handleTaskVoice('neu', d);
  assert.match(y.reply, /angelegt/);
  assert.equal(d.calls.find(c => c[0] === 'submit')[1].request, 'Räum den Eingangsordner auf');
});

test('Rückfrage: „ändern“ ändert mit erwarteter Revision', async () => {
  m.clearPending(); const d = deps('revise');
  await m.handleTaskVoice('Räum den Eingangsordner auf', d);
  const y = await m.handleTaskVoice('ändern', d);
  assert.match(y.reply, /Revision 5/);
  assert.deepEqual(d.calls.find(c => c[0] === 'revise')[1], { job: 'j1', request: 'Räum den Eingangsordner auf', expected: 4 });
});

test('Rückfrage: „Ja“ ist mehrdeutig -> nachfragen, nichts tun; „nein“ verwirft', async () => {
  m.clearPending(); const d = deps('submit');
  await m.handleTaskVoice('Und teste das Plugin dann auch', d);
  const j = await m.handleTaskVoice('Ja', d);
  assert.match(j.reply, /neu.*ändern/s); assert.ok(j.confirm);
  assert.equal(d.calls.filter(c => c[0] === 'submit' || c[0] === 'revise').length, 0);
  assert.match((await m.handleTaskVoice('nein', d)).reply, /mache nichts/);
  assert.equal(m.pendingTask(1000), null);
});

test('Prüf-Wunsch, vom Modell als Status gelesen, wird ein Auftrag (mit Ja-Rückfrage)', async () => {
  m.clearPending(); const d = deps('progress');
  d.jv = async (cmd, x) => { d.calls.push([cmd, x]); return cmd === 'list' ? { jobs: [] } : { job_id: 'j1' }; };
  const r = await m.handleTaskVoice('Kannst du checken, ob der Minecraft-Server erreichbar ist?', d);
  assert.ok(r.confirm); assert.match(r.reply, /Soll ich den Auftrag anlegen/);
});

test('Vorfilter: eindeutiges Gespräch ohne Modell, Aufträge/Status nie', () => {
  for (const s of ['Wie heißt die Hauptstadt von Kanada?', 'Was bedeutet MKV?', 'Danke dir', 'Gute Nacht Jarvis', 'Erklär mir kurz, was ein NAS ist.', 'Hallo'])
    assert.ok(R.obviousChat(s), s);
  for (const s of ['Was ist aus meinem letzten Auftrag geworden?', 'Erzähl mir, wie weit der Auftrag ist', 'Warum ist der Build fehlgeschlagen?', 'Was ist mit dem Backup, fertig?',
    'Kannst du mir die Fotos sortieren?', 'Danke, und nimm noch die Unterordner mit', 'Erklär mir das Ergebnis', 'Weißt du, ob die Zertifikate ablaufen? Prüf das mal'])
    assert.ok(!R.obviousChat(s), s);
});

test('Vorfilter in handleTaskVoice: Wissensfrage fragt das Modell nicht', async () => {
  m.clearPending(); const d = deps('submit');
  assert.equal(await m.handleTaskVoice('Wie heißt die Hauptstadt von Kanada?', d), null);
  assert.equal(d.calls.length, 0, 'weder Liste noch Modell');
});
