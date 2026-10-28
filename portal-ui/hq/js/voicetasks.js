/* MA-HOME HQ — Aufträge per Sprache (VOICE-007). Anlegen und Abbrechen NUR nach ausdrücklicher Bestätigung („Ja“).
   Fortschritt fragen ist lesend. Unterbrechen der Sprachausgabe bricht nie einen Auftrag ab. Zustände kommen aus der Engine, nicht aus dem Modell. */
import { api } from './api.js';

const STATE = { queued: 'wartet', planning: 'wird geplant', running: 'läuft', waiting_approval: 'braucht deine Freigabe', waiting_pc: 'wartet auf den PC', done: 'ist erledigt', partial: 'ist teilweise erledigt', failed: 'ist fehlgeschlagen', cancelled: 'wurde abgebrochen' };
const FINAL = ['done', 'partial', 'failed', 'cancelled'];
const CONFIRM_MS = 30000;
const norm = t => t.toLowerCase().replace(/[!?]/g, ' ').replace(/\s+/g, ' ').trim();

export function parseTaskIntent(raw) {
  const t = norm(raw);
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

let pending = null;   // { kind, request|job, until }
export const pendingTask = (now = Date.now()) => (pending && now < pending.until ? pending : null);
export function clearPending() { pending = null; }

/* Liefert {reply, meta} oder null (= nicht zuständig). */
export async function handleTaskVoice(text, deps = { jv, now: Date.now }) {
  const p = pendingTask(deps.now());
  if (p) {
    if (isYes(text)) {
      pending = null;
      if (p.kind === 'submit') { const r = await deps.jv('submit', { request: p.request, client_id: p.client_id }); return { reply: 'Auftrag ist angelegt' + (r.job_id ? ', Nummer ' + String(r.job_id).slice(-6) : '') + '. Frag mich jederzeit nach dem Fortschritt.', meta: 'Auftrag angelegt' }; }
      if (p.kind === 'cancel') { await deps.jv('cancel', { job: p.job }); return { reply: 'Der Auftrag wird abgebrochen.', meta: 'Auftrag abgebrochen' }; }
    }
    if (isNo(text)) { pending = null; return { reply: 'Okay, ich mache nichts.', meta: 'verworfen' }; }
    pending = null;   // etwas anderes gesagt: Rückfrage verfällt, normal weiter
  }
  const it = parseTaskIntent(text);
  if (!it) return null;
  if (it.kind === 'submit_empty') return { reply: 'Was soll der Auftrag sein? Sag zum Beispiel: Neuer Auftrag, fasse die Serverlogs von heute zusammen.' };
  if (it.kind === 'submit') {
    pending = { kind: 'submit', request: it.request, client_id: rid(), until: deps.now() + CONFIRM_MS };
    return { reply: 'Ich habe verstanden: „' + short(it.request) + '“. Soll ich den Auftrag anlegen? Sag Ja oder Nein.', meta: 'wartet auf Bestätigung', confirm: true };
  }
  const { jobs } = await deps.jv('list', { limit: 5 });
  const list = jobs || [];
  if (it.kind === 'progress') return { reply: list[0] ? jobSentence(list[0]) : 'Es gibt noch keinen Auftrag.' };
  const run = list.find(j => !FINAL.includes(j.state));
  if (!run) return { reply: 'Es läuft gerade kein Auftrag, den ich abbrechen könnte.' };
  pending = { kind: 'cancel', job: run.id, until: deps.now() + CONFIRM_MS };
  return { reply: 'Soll ich den Auftrag „' + short(run.request) + '“ wirklich abbrechen? Sag Ja oder Nein.', meta: 'wartet auf Bestätigung', confirm: true };
}
