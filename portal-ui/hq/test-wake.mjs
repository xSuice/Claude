// Tests fuer Wakeword-Hilfen: stripWake (Anrede entfernen) und WAV-Encoder der Engine
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

globalThis.window = globalThis.window || {};
const src = fs.readFileSync(new URL('./js/localvoice.js', import.meta.url), 'utf8').replace("import { api } from './api.js';", 'const api = async () => ({});');
const lv = await import('data:text/javascript;base64,' + Buffer.from(src).toString('base64'));
const WAKE = /\b(jarvis|dscharvis|dscharwis|dschavis|dschawis|jarwis|tscharvis|charvis|scharwis|jervis|jaris|javis|jarvi)\b/i;

test('stripWake entfernt „Hey Jarvis,“ vorne', () => {
  assert.equal(lv.stripWake('Hey Jarvis, wie spät ist es?', WAKE), 'wie spät ist es?');
  assert.equal(lv.stripWake('Hey, Jarvis. Welche Aufgaben sind offen?', WAKE), 'Welche Aufgaben sind offen?');
  assert.equal(lv.stripWake('Hey Jarvis.', WAKE), '');
});
test('stripWake ohne erkanntes Wort entfernt nur die Anrede', () => {
  assert.equal(lv.stripWake('Hey Charlie, wie spät ist es', WAKE), 'Charlie, wie spät ist es');
  assert.equal(lv.stripWake('Okay, zeig mir den Status', WAKE), 'zeig mir den Status');
});
test('stripWake entfernt Reststueck „vis,“ nach Audio-Schnitt', () => {
  assert.equal(lv.stripWake('vis, wie spät ist es?', WAKE), 'wie spät ist es?');
  assert.equal(lv.stripWake('Wie spät ist es?', WAKE), 'Wie spät ist es?');
});
test('stripWake schneidet nicht mitten im Satz', () => {
  const t = 'Erzähl mir etwas über die Geschichte von Iron Man und Jarvis';
  assert.equal(lv.stripWake(t, WAKE), t);
});
test('transcribeWav lehnt zu lange Aufnahmen ab', async () => {
  await assert.rejects(lv.transcribeWav({ size: lv.MAX_WAV + 1 }), /zu lang/);
});
test('encodeWav schreibt gueltigen PCM16-Header', async () => {
  const es = fs.readFileSync(new URL('./voice-engine/voice-engine.js', import.meta.url), 'utf8');
  const fn = es.slice(es.indexOf('export function encodeWav'), es.indexOf('/* ---------- Browser-Engine'));
  const { encodeWav } = await import('data:text/javascript;base64,' + Buffer.from(fn).toString('base64'));
  const b = encodeWav(new Float32Array([0, 0.5, -1, 1]));
  const v = new DataView(await b.arrayBuffer());
  assert.equal(b.size, 44 + 8);
  assert.equal(v.getUint32(24, true), 16000);
  assert.equal(v.getInt16(44 + 2, true), Math.trunc(0.5 * 0x7fff));
  assert.equal(v.getInt16(44 + 4, true), -0x7fff);
});
