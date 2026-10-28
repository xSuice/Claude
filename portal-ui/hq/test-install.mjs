// install.js: Standalone-Erkennung und iOS-Erkennung
import test from 'node:test'; import assert from 'node:assert/strict';
const m = await import('./js/install.js');
test('standalone detection', () => {
  assert.equal(m.isStandalone({ matchMedia: () => ({ matches: true }), navigator: {} }), true);
  assert.equal(m.isStandalone({ matchMedia: () => ({ matches: false }), navigator: { standalone: true } }), true);
  assert.equal(m.isStandalone({ matchMedia: () => ({ matches: false }), navigator: {} }), false);
});
test('iOS only for Safari', () => {
  assert.equal(m.isIOS('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit Safari'), true);
  assert.equal(m.isIOS('Mozilla/5.0 (iPhone) CriOS/130'), false);
  assert.equal(m.isIOS('Mozilla/5.0 (Linux; Android 15) Chrome/140'), false);
});
