import test from 'node:test'; import assert from 'node:assert/strict';
globalThis.sessionStorage = { getItem: () => null, setItem() {} };
globalThis.document = { hidden: false, addEventListener() {} };
const m = await import('./js/store.js');
test('adaptive poll: 2 s while something runs, 5 s idle', () => {
  assert.equal(m.pollDelay({ engine: { active: [{ id: 'j' }] }, tasks: [] }), 2000);
  assert.equal(m.pollDelay({ engine: { active: [] }, tasks: [{ status: 'IN_PROGRESS' }] }), 2000);
  assert.equal(m.pollDelay({ engine: { active: [] }, tasks: [{ status: 'DONE' }] }), 5000);
});
test('unified state vocabulary', () => {
  const M = { done: 'DONE_VERIFIED', failed: 'FAILED', waiting_approval: 'WAITING_APPROVAL', waiting_pc: 'BLOCKED', running: 'RUNNING', planning: 'RUNNING', INBOX: 'IDLE', cancelled: 'CANCELLED', partial: 'PARTIAL' };
  for (const [k, v] of Object.entries(M)) assert.equal(m.unifiedState(k), v, k);
});
