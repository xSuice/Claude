/* MA-HOME HQ — D1: Erfolgsquote der Engine-Jobs der letzten 24 h aus /api/jarvis/jobs.
   Quote = erledigt / (erledigt + fehlgeschlagen); Abbrüche durch den Owner sind keine Fehler. Ohne Daten keine Zahl. */
const DONE = /^(?:done|complete|completed)$/i, FAIL = /^(?:failed|error)$/i, CANC = /^(?:cancelled|canceled)$/i;

export function jobStats(jobs, nowSec = Date.now() / 1000, listLimit = 20) {
  const list = Array.isArray(jobs) ? jobs : [];
  const recent = list.filter(j => j && j.finished && j.finished > nowSec - 86400);
  const done = recent.filter(j => DONE.test(j.state)).length, failed = recent.filter(j => FAIL.test(j.state)).length;
  const cancelled = recent.filter(j => CANC.test(j.state)).length;
  return { done, failed, cancelled, total: recent.length,
    rate: done + failed ? Math.round(done / (done + failed) * 100) : null,
    truncated: list.length >= listLimit && recent.length >= listLimit };   // Liste ganz innerhalb 24 h -> es gab evtl. mehr
}

export function jobStatsText(s) {
  if (s.rate == null) return '24 h: keine abgeschlossenen Jobs';
  return (s.truncated ? '24 h (nur letzte ' + s.total + ' Jobs): ' : '24 h: ') + s.rate + ' % erfolgreich · ' + s.done + ' erledigt · ' + s.failed + ' fehlgeschlagen' + (s.cancelled ? ' · ' + s.cancelled + ' abgebrochen' : '');
}
