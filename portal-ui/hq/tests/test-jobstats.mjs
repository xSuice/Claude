// D1: Erfolgsquote der Engine-Jobs (letzte 24 h) – ehrlich: nur abgeschlossene, Abbrüche zählen nicht als Fehler.
import test from 'node:test'; import assert from 'node:assert/strict';
import { jobStats, jobStatsText } from './js/jobstats.js';

const NOW = 1_800_000_000, h = 3600;
const J = (state, ago) => ({ state, finished: ago == null ? null : NOW - ago });

test('zählt nur die letzten 24 h, Quote = erledigt / (erledigt + fehlgeschlagen)', () => {
  const s = jobStats([J('done', h), J('done', 2 * h), J('done', 3 * h), J('failed', 4 * h), J('cancelled', 5 * h), J('done', 30 * h), J('running', null)], NOW);
  assert.deepEqual(s, { done: 3, failed: 1, cancelled: 1, total: 5, rate: 75, truncated: false });
});

test('ohne abgeschlossene Jobs keine erfundene Quote', () => {
  assert.equal(jobStats([J('cancelled', h)], NOW).rate, null);
  assert.equal(jobStats([], NOW).rate, null);
  assert.match(jobStatsText(jobStats([], NOW)), /keine abgeschlossenen/);
});

test('Hinweis, wenn die Liste das 24-h-Fenster abschneidet', () => {
  const list = Array.from({ length: 20 }, (_, i) => J('done', i * 60));
  const s = jobStats(list, NOW, 20);
  assert.equal(s.truncated, true);
  assert.match(jobStatsText(s), /nur letzte 20 Jobs/);
});

test('Text', () => {
  assert.equal(jobStatsText({ done: 4, failed: 1, cancelled: 2, total: 7, rate: 80, truncated: false }), '24 h: 80 % erfolgreich · 4 erledigt · 1 fehlgeschlagen · 2 abgebrochen');
});
