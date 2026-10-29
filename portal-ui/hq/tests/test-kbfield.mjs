// Regression: Auswahlfeld im Chat schloss sich auf dem Handy sofort (SELECT setzte body.kb -> Optionen ausgeblendet).
import test from 'node:test'; import assert from 'node:assert/strict';
import { raisesKeyboard } from './js/kbfield.js';

const el = (tagName, extra = {}) => ({ tagName, ...extra });

test('Auswahlliste, Häkchen und Knöpfe öffnen keine Tastatur', () => {
  for (const e of [el('SELECT'), el('INPUT', { type: 'checkbox' }), el('INPUT', { type: 'radio' }), el('INPUT', { type: 'range' }), el('BUTTON'), el('INPUT', { type: 'file' })])
    assert.equal(raisesKeyboard(e), false, e.tagName + ' ' + (e.type || ''));
});

test('Textfelder öffnen die Tastatur', () => {
  for (const e of [el('TEXTAREA'), el('INPUT', { type: 'text' }), el('INPUT', { type: 'search' }), el('INPUT', { type: 'time' }), el('INPUT', {}), el('DIV', { isContentEditable: true })])
    assert.equal(raisesKeyboard(e), true, e.tagName + ' ' + (e.type || ''));
});

test('gesperrte oder schreibgeschützte Felder nicht', () => {
  assert.equal(raisesKeyboard(el('TEXTAREA', { readOnly: true })), false);
  assert.equal(raisesKeyboard(el('INPUT', { type: 'text', disabled: true })), false);
  assert.equal(raisesKeyboard(null), false);
});

test('app.js nutzt die Prüfung (kein SELECT mehr in der kb-Logik)', async () => {
  const src = (await import('node:fs')).readFileSync(new URL('./js/app.js', import.meta.url), 'utf8');
  assert.match(src, /raisesKeyboard/);
  assert.doesNotMatch(src, /INPUT\|TEXTAREA\|SELECT\)\$\/\.test\(t\.tagName\)/);
});
