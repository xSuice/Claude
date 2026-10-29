// Chat-Weiche: der Chat schickt den letzten Austausch als Kontext mit (Fachrollen haben sonst keinen Gesprächsfaden).
import test from 'node:test'; import assert from 'node:assert/strict';
import { lastExchange } from './js/chatctx.js';

test('letzter Austausch: Frage + Antwort, gekürzt, ohne Werkzeug-/Fehlerzeilen', () => {
  const msgs = [{ r: 'u', t: 'alt' }, { r: 'a', t: 'alte Antwort' }, { r: 'u', p: 'Wie sichere ich SSH ab?', t: 'x' }, { r: 't', t: 'Weiterleitung: jarvis-security' }, { r: 'a', t: 'Mit Schlüsseln statt Passwort.' }];
  assert.equal(lastExchange(msgs), 'Andrew: Wie sichere ich SSH ab? | JARVIS: Mit Schlüsseln statt Passwort.');
  assert.equal(lastExchange([]), '');
  assert.equal(lastExchange([{ r: 'u', t: 'nur Frage' }]), 'Andrew: nur Frage');
  const long = lastExchange([{ r: 'u', t: 'f' }, { r: 'a', t: 'x'.repeat(5000) }]);
  assert.ok(long.length <= 1500, long.length);
});
