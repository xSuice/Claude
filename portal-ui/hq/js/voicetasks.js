/* MA-HOME HQ — Aufträge per Sprache (VOICE-007). Anlegen und Abbrechen NUR nach ausdrücklicher Bestätigung („Ja“).
   Fortschritt fragen ist lesend. Unterbrechen der Sprachausgabe bricht nie einen Auftrag ab. Zustände kommen aus der Engine, nicht aus dem Modell. */
import { api } from './api.js';
import { resolveIntent, isNew, isChange, obviousChat } from './dialogref.js';

const STATE = { queued: 'wartet', planning: 'wird geplant', running: 'läuft', waiting_approval: 'braucht deine Freigabe', waiting_pc: 'wartet auf den PC', done: 'ist erledigt', partial: 'ist teilweise erledigt', failed: 'ist fehlgeschlagen', cancelled: 'wurde abgebrochen' };
const FINAL = ['done', 'partial', 'failed', 'cancelled'];
const CONFIRM_MS = 30000;
const norm = t => t.toLowerCase().replace(/[!?]/g, ' ').replace(/\s+/g, ' ').trim();

export function parseTaskIntent(raw) {
  const t = norm(raw);
  const rv = raw.trim().replace(/\s+/g, ' ').match(/^(?:bitte )?(?:ändere|änder|ändern|korrigiere|ergänze|erweitere|passe)\s+(?:bitte\s+)?(?:den |meinen |bitte den )?(?:letzten |laufenden |aktuellen )?auftr\w*(?:\s+an)?\s*[:,.!-]?\s*(.*)$/i);
  if (rv) { const ch = rv[1].replace(/[!?]+$/, '').trim(); return ch.length >= 5 ? { kind: 'revise', change: ch } : { kind: 'revise_empty' }; }
  let m = t.match(/^(?:(?:neue[rn]?|nächster|weiterer) auftr\w*|(?:erstelle|erstell|mach|lege?|leg) (?:mir )?(?:einen |einen neuen |neuen )?auftr\w*(?: an)?|auftr\w* für jarvis|jarvis auftr\w*)\s*[:,.-]?\s*(.*)$/);
  if (m) { const req = raw.trim().replace(/\s+/g, ' ').replace(/^.*?\bauftr\w*(?: an| für jarvis)?\s*[:,.!-]?\s*/i, '').replace(/[!?]+$/, '').trim(); return req.length >= 8 ? { kind: 'submit', request: req } : { kind: 'submit_empty' }; }
  if (/^(?:br\w{0,3}ch\w{0,2}|richte|bericht|stopp?e?|beende) (?:den |meinen |bitte den )?(?:letzten |laufenden |aktuellen )?auftr\w*(?: bitte)?(?: ab\b|$)|^(?:den )?(?:letzten |laufenden )?auftr\w* (?:abbrechen|stoppen|beenden)/.test(t.replace(/[.,]/g, ''))) return { kind: 'cancel' };   // tolerant gegen Whisper-Varianten (Briecht, Brecht)
  if (/(?:wie weit|wie steht|fortschritt|stand)\b.*\bauftr(?!äge)\w*|^was macht (?:mein|der) (?:letzte[rn]? |aktuelle[rn]? )?auftr\w*|^(?:status|stand) (?:vom|des) (?:letzten )?auftr\w*/.test(t)) return { kind: 'progress' };
  return null;
}
export const isYes = raw => /^(?:ja|jawohl|ja bitte|ja mach|ja genau|bestätigen?|bestätigt|mach (?:das|es)|okay|ok|genau|richtig|passt)(?: bitte)?$/.test(norm(raw).replace(/[.,]/g, ''));
export const isNo = raw => /^(?:nein|nee|lieber nicht|abbrechen|nicht|lass (?:es|das)|vergiss es|stopp?)(?: bitte)?$/.test(norm(raw).replace(/[.,]/g, ''));

const jv = (cmd, extra = {}) => api('/api/jarvis', { body: { cmd, ...extra } }).then(r => { if (!r.ok) throw new Error((r.data && r.data.error) || r.error || 'JARVIS-Fehler'); return r.data; });
const rid = () => 'voice-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
const short = s => { s = String(s || ''); return s.length > 90 ? s.slice(0, 87) + '…' : s; };

export function jobSentence(j) {
  const st = STATE[j.state] || j.state;
  return 'Dein letzter Auftrag „' + short(j.request) + '“ ' + st + '.';
}

/* PRIO2 N1: Rückfallebene, wenn kein Satzmuster greift: das lokale Qwen (PC) ordnet die Äußerung einer Absicht zu.
   Nur Zuordnung, nie Ausführung: Anlegen/Ändern/Abbrechen laufen weiter über dieselbe Ja-Rückfrage. Fehler/503/Zeitlimit -> null (altes Verhalten). */
const MODEL_INTENTS = ['submit', 'revise', 'cancel', 'progress', 'none'];
export async function modelIntent(text, run, ms = 2500) {
  const ac = new AbortController(), t = setTimeout(() => ac.abort(), ms);
  try {
    const d = await api('/api/voice/intent', { body: { text, run: run || null }, signal: ac.signal });
    return d && MODEL_INTENTS.includes(d.intent) ? d.intent : null;
  } catch (e) {
    return null;
  } finally {
    clearTimeout(t);
  }
}
const words = s => String(s).trim().replace(/\s+/g, ' ').replace(/[!?.]+$/, '').trim();

let pending = null;   // { kind, request|job, until }
let recent = null;    // N2: Auftragsliste der letzten Äußerung { at, jobs } – nur als Kontext für die parallele Erkennung
const RECENT_MS = 30000;
export const pendingTask = (now = Date.now()) => (pending && now < pending.until ? pending : null);
export function clearPending() { pending = null; recent = null; }
// Kontext fürs Modell: laufender Auftrag, sonst „zuletzt: …“ (Bezug für „Bist du fertig?“), sonst null
function context(list) {
  const run = list.find(j => !FINAL.includes(j.state));
  if (run) return run.request;
  return list[0] ? 'zuletzt: ' + short(list[0].request) + ' (' + (STATE[list[0].state] || list[0].state) + ')' : null;
}

/* Liefert {reply, meta} oder null (= nicht zuständig). deps.local(text) = true: die lokale Übersicht antwortet (Modell wird nicht gefragt). */
export async function handleTaskVoice(text, deps = {}) {
  deps = { jv, now: Date.now, classify: modelIntent, local: () => false, ...deps };
  const p = pendingTask(deps.now());
  if (p && p.kind === 'choose') {   // N2: „neu“ / „ändern“ beantworten die Rückfrage ausdrücklich (Wortlaut stand in der Frage)
    if (isNew(text)) { pending = null; const r = await deps.jv('submit', { request: p.text, client_id: p.client_id }); return { reply: 'Neuer Auftrag ist angelegt' + (r.job_id ? ', Nummer ' + String(r.job_id).slice(-6) : '') + '. Der laufende Auftrag bleibt unverändert.', meta: 'Auftrag angelegt' }; }
    if (isChange(text)) { pending = null; const r = await deps.jv('revise', { job: p.job, request: p.text, expected: p.expected }); return { reply: 'Erledigt: Der Auftrag läuft jetzt als Revision ' + r.revision + ' weiter. Bereits erstellte Dateien bleiben erhalten.', meta: 'Auftrag geändert' }; }
    if (isYes(text)) { pending.until = deps.now() + CONFIRM_MS; return { reply: 'Bitte sag „neu“ für einen neuen Auftrag oder „ändern“ für den laufenden Auftrag.', meta: 'wartet auf Auswahl', confirm: true }; }
  }
  if (p && p.kind !== 'choose') {
    if (isYes(text)) {
      pending = null;
      if (p.kind === 'submit') { const r = await deps.jv('submit', { request: p.request, client_id: p.client_id }); return { reply: 'Auftrag ist angelegt' + (r.job_id ? ', Nummer ' + String(r.job_id).slice(-6) : '') + '. Frag mich jederzeit nach dem Fortschritt.', meta: 'Auftrag angelegt' }; }
      if (p.kind === 'cancel') { await deps.jv('cancel', { job: p.job }); return { reply: 'Der Auftrag wird abgebrochen.', meta: 'Auftrag abgebrochen' }; }
      if (p.kind === 'revise') { const r = await deps.jv('revise', { job: p.job, request: p.change, expected: p.expected }); return { reply: 'Erledigt: Der Auftrag läuft jetzt als Revision ' + r.revision + ' weiter. Bereits erstellte Dateien bleiben erhalten.', meta: 'Auftrag geändert' }; }
    }
    if (isNo(text)) { pending = null; return { reply: 'Okay, ich mache nichts.', meta: 'verworfen' }; }
    pending = null;   // etwas anderes gesagt: Rückfrage verfällt, normal weiter
  }
  if (p && p.kind === 'choose') {
    if (isNo(text)) { pending = null; return { reply: 'Okay, ich mache nichts.', meta: 'verworfen' }; }
    pending = null;
  }
  let it = parseTaskIntent(text), list = null, via = '';
  const jobs = async () => { if (!list) list = ((await deps.jv('list', { limit: 5 })) || {}).jobs || []; return list; };
  if (!it) {
    if (deps.local(text)) return null;
    if (obviousChat(text)) return null;   // Gruß/Dank/Wissensfrage: direkt ins Gespräch, ohne ~1 s Erkennung
    let k = null, run = null;
    try {
      // Folgeäußerung (< 30 s): Erkennung mit dem Kontext der letzten Liste parallel zur frischen Liste starten (spart ~0,4 s).
      // Aktionen nutzen immer die frische Liste.
      const now = deps.now(), warm = recent && now - recent.at < RECENT_MS ? recent.jobs : null;
      const listP = jobs();
      const kP = warm ? deps.classify(text, context(warm)) : listP.then(l => deps.classify(text, context(l)));
      const [l, kk] = await Promise.all([listP, kP]);
      recent = { at: now, jobs: l }; k = kk;
      run = l.find(j => !FINAL.includes(j.state)) || null;
    } catch (e) { k = null; }
    const w = words(text);
    k = k ? resolveIntent(k, w, run ? run.request : null) : null;   // N2: Gesprächsbezug prüfen, bei Widerspruch nachfragen
    if (k === 'choose' && run && w.length >= 5) {
      pending = { kind: 'choose', text: w, job: run.id, expected: run.revision || 1, client_id: rid(), until: deps.now() + CONFIRM_MS };
      return { reply: 'Kurze Rückfrage zu „' + short(w) + '“: Soll das ein neuer Auftrag werden oder den laufenden Auftrag „' + short(run.request) + '“ ändern? Sag „neu“, „ändern“ oder „nein“.', meta: 'wartet auf Auswahl · erkannt von Qwen lokal', confirm: true };
    }
    if (k === 'submit') it = w.length >= 8 ? { kind: 'submit', request: w } : { kind: 'submit_empty' };
    else if (k === 'revise') it = w.length >= 5 ? { kind: 'revise', change: w } : { kind: 'revise_empty' };
    else if (k === 'cancel' || k === 'progress') it = { kind: k };
    if (!it) return null;
    via = ' · erkannt von Qwen lokal';
  }
  if (it.kind === 'revise_empty') return { reply: 'Was soll ich am Auftrag ändern? Sag zum Beispiel: Ändere den Auftrag, nimm Java 25.' };
  if (it.kind === 'submit_empty') return { reply: 'Was soll der Auftrag sein? Sag zum Beispiel: Neuer Auftrag, fasse die Serverlogs von heute zusammen.' };
  if (it.kind === 'submit') {
    pending = { kind: 'submit', request: it.request, client_id: rid(), until: deps.now() + CONFIRM_MS };
    return { reply: 'Ich habe verstanden: „' + short(it.request) + '“. Soll ich den Auftrag anlegen? Sag Ja oder Nein.', meta: 'wartet auf Bestätigung' + via, confirm: true };
  }
  const all = await jobs();
  if (it.kind === 'progress') return { reply: all[0] ? jobSentence(all[0]) : 'Es gibt noch keinen Auftrag.', meta: via ? 'lesend' + via : undefined };
  const run = all.find(j => !FINAL.includes(j.state));
  if (it.kind === 'revise') {
    if (!run) return { reply: 'Es läuft gerade kein Auftrag, den ich ändern könnte. Für etwas Neues sag „Neuer Auftrag“.' };
    pending = { kind: 'revise', job: run.id, change: it.change, expected: run.revision || 1, until: deps.now() + CONFIRM_MS };
    return { reply: 'Ich ändere den Auftrag „' + short(run.request) + '“: „' + short(it.change) + '“. Der Auftrag behält seine Nummer und wird neu geplant. Soll ich? Sag Ja oder Nein.', meta: 'wartet auf Bestätigung' + via, confirm: true };
  }
  if (!run) return { reply: 'Es läuft gerade kein Auftrag, den ich abbrechen könnte.' };
  pending = { kind: 'cancel', job: run.id, until: deps.now() + CONFIRM_MS };
  return { reply: 'Soll ich den Auftrag „' + short(run.request) + '“ wirklich abbrechen? Sag Ja oder Nein.', meta: 'wartet auf Bestätigung' + via, confirm: true };
}
