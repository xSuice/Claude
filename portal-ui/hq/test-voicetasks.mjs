// voicetasks.js: Absichten erkennen, Bestätigung erzwingen, Abbruch nur nach Ja
import test from 'node:test'; import assert from 'node:assert/strict';
globalThis.localStorage = { getItem: () => null, setItem: () => {} };
globalThis.document = globalThis.document || { cookie: '' };
const m = await import('./js/voicetasks.js');

test('parse intents', () => {
  assert.deepEqual(m.parseTaskIntent('Neuer Auftrag: fasse die Serverlogs von heute zusammen'), { kind: 'submit', request: 'fasse die Serverlogs von heute zusammen' });
  assert.equal(m.parseTaskIntent('Erstelle einen Auftrag prüfe die Backups').kind, 'submit');
  assert.equal(m.parseTaskIntent('neuer Auftrag').kind, 'submit_empty');
  assert.deepEqual(m.parseTaskIntent('Neue Auftrag. Fasse die Logs von heute zusammen.'), { kind: 'submit', request: 'Fasse die Logs von heute zusammen.' });   // echtes Whisper-Transkript
  for (const c of ['Brich den Auftrag ab', 'Briecht den Auftrag ab', 'Brecht den Auftrag ab.', 'Richte den Auftrag ab.', 'Bericht den Auftrag ab', 'Auftrag abbrechen', 'Stopp den Auftrag']) assert.equal((m.parseTaskIntent(c) || {}).kind, 'cancel', c);
  assert.equal(m.parseTaskIntent('Brauchst du den Auftrag noch'), null);
  assert.equal(m.parseTaskIntent('Wie weit ist mein Auftrag?').kind, 'progress');
  assert.equal(m.parseTaskIntent('Wie weit ist mein Auftrat?').kind, 'progress');   // echtes Whisper-Transkript
  assert.deepEqual(m.parseTaskIntent('Neuer Auftrag, fasset die sehr Verlogs von heute zusammen!'), { kind: 'submit', request: 'fasset die sehr Verlogs von heute zusammen' });
  assert.equal(m.parseTaskIntent('Was macht der letzte Auftrag').kind, 'progress');
  assert.equal(m.parseTaskIntent('Wie spät ist es?'), null);
  assert.equal(m.parseTaskIntent('Welche Aufträge sind offen?'), null);   // bleibt bei der lokalen Übersicht
});
test('yes/no', () => {
  for (const y of ['Ja', 'ja bitte.', 'Okay', 'Bestätigen', 'Mach das']) assert.ok(m.isYes(y), y);
  for (const n of ['Nein', 'nein.', 'Lass es', 'Vergiss es']) assert.ok(m.isNo(n), n);
  assert.ok(!m.isYes('Ja aber ändere vorher den Titel'));
});
function deps() {
  const calls = [];
  return { calls, now: () => 1000, jv: async (cmd, x) => { calls.push([cmd, x]); if (cmd === 'list') return { jobs: [{ id: 'j1', request: 'Logs zusammenfassen', state: 'running' }] }; if (cmd === 'submit') return { job_id: 'j20261027-abcdef' }; return {}; } };
}
test('submit only after yes', async () => {
  m.clearPending(); const d = deps();
  const a = await m.handleTaskVoice('Neuer Auftrag: prüfe die Backups von heute', d);
  assert.ok(a.confirm); assert.equal(d.calls.length, 0);
  const b = await m.handleTaskVoice('Ja', d);
  assert.equal(d.calls[0][0], 'submit'); assert.equal(d.calls[0][1].request, 'prüfe die Backups von heute'); assert.ok(d.calls[0][1].client_id);
  assert.match(b.reply, /angelegt.*abcdef/);
});
test('no / other speech drops the pending action', async () => {
  m.clearPending(); const d = deps();
  await m.handleTaskVoice('Neuer Auftrag: prüfe die Backups von heute', d);
  assert.match((await m.handleTaskVoice('Nein', d)).reply, /nichts/);
  assert.equal(await m.handleTaskVoice('Ja', d), null);
  await m.handleTaskVoice('Neuer Auftrag: prüfe die Backups von heute', d);
  assert.equal(await m.handleTaskVoice('Wie spät ist es', d), null);
  assert.equal(await m.handleTaskVoice('Ja', d), null);
  assert.ok(!d.calls.some(c => c[0] === 'submit'));
});
test('cancel asks and targets the running job; progress reads state', async () => {
  m.clearPending(); const d = deps();
  const a = await m.handleTaskVoice('Brich den Auftrag ab', d);
  assert.ok(a.confirm); assert.ok(!d.calls.some(c => c[0] === 'cancel'));
  await m.handleTaskVoice('ja', d);
  assert.deepEqual(d.calls.find(c => c[0] === 'cancel')[1], { job: 'j1' });
  assert.match((await m.handleTaskVoice('Wie weit ist mein Auftrag', d)).reply, /läuft/);
});

test('revise: parse, confirm with expected revision, nothing without yes', async () => {
  assert.deepEqual(m.parseTaskIntent('Ändere den Auftrag: nimm Java 25 und teste erneut.'), { kind: 'revise', change: 'nimm Java 25 und teste erneut.' });
  assert.equal(m.parseTaskIntent('Ergänze meinen Auftrag, auch eine README auf Englisch').kind, 'revise');
  assert.equal(m.parseTaskIntent('Ändere den Auftrag').kind, 'revise_empty');
  assert.equal(m.parseTaskIntent('Ändere die Farbe vom Licht'), null);
  m.clearPending();
  const calls = [];
  const d = { now: () => 1000, jv: async (cmd, x) => { calls.push([cmd, x]); if (cmd === 'list') return { jobs: [{ id: 'j1', request: 'Java bauen', state: 'running', revision: 3 }] }; if (cmd === 'revise') return { revision: 4 }; return {}; } };
  const a = await m.handleTaskVoice('Ändere den Auftrag: nimm Java 25', d);
  assert.ok(a.confirm); assert.ok(!calls.some(c => c[0] === 'revise'));
  const b = await m.handleTaskVoice('Ja', d);
  assert.deepEqual(calls.find(c => c[0] === 'revise')[1], { job: 'j1', request: 'nimm Java 25', expected: 3 });
  assert.match(b.reply, /Revision 4/);
  m.clearPending(); calls.length = 0;
  await m.handleTaskVoice('Ändere den Auftrag: nimm Java 25', d);
  await m.handleTaskVoice('Nein', d);
  assert.ok(!calls.some(c => c[0] === 'revise'));
});
