/* MA-HOME HQ — PRIO2 N2: Gesprächsbezug für die Modell-Absicht. Reine Funktionen, keine Seiteneffekte.
   Idee: Eine Änderung bezieht sich auf etwas Laufendes (Bezugswörter oder Wörter aus dem laufenden Auftrag); ein neuer Auftrag
   bringt einen eigenen Gegenstand mit. Widersprechen sich Modell und Bezugs-Hinweis, fragt JARVIS nach statt zu raten. */

// Wortgrenzen Unicode-fest: \b kennt in JS keine Umlaute („\bändern“ trifft nie) -> Lookarounds mit \p{L}
const W = (alts, flags = 'iu') => new RegExp('(?<![\\p{L}\\p{N}])(?:' + alts + ')(?![\\p{L}\\p{N}])', flags);
// Bezug auf den laufenden Auftrag / das gerade Gesagte
const REF_WORDS = W('dabei|dazu|dafür|damit|davon|auch|noch|lieber|stattdessen|statt|nur|doch|sondern|ohne|auslassen|weglassen|außer|zusätzlich|anders|änder\\p{L}*|ergänz\\p{L}*|sortiert|bis|dann|(?:beim|im|am|den|dem)\\s+(?:laufenden|aktuellen|letzten)\\s+auftr\\p{L}*');
const REF_START = /^(?:und|nee|ach|nicht|nimm|lass)(?![\p{L}])/iu;
const REF = { test: t => REF_WORDS.test(t) || REF_START.test(String(t).trim()) };
// Frage nach dem Stand eines Auftrags (nicht: „prüf, ob …“)
const STATUS = W('auftr\\p{L}*|fertig|läuft|laeuft|lauf\\p{L}*|klappt|geklappt|durch\\p{L}*|dauert?|lange|brauchst|stand|status|fortschritt|weit|schief\\p{L}*|hängt|haengt|woran|neues|ergebnis|rausgekommen|geworden|fehlgeschlagen|gescheitert|abgebrochen');
// Prüf-/Nachseh-Wunsch = Arbeit für JARVIS
const CHECK = W('prüf\\p{L}*|pruef\\p{L}*|nachsehen|nachschauen|schau\\p{L}*|check\\p{L}*|übersicht|uebersicht|bericht|liste|finde?\\s+\\p{L}*\\s*raus|herausfinden');
const STOP = new Set('der die das den dem des ein eine einen einem einer und oder mit von vom zu zum zur in im auf für bitte mal mir mich du ich es ist sind auch noch nur dann'.split(' '));
const content = s => new Set((String(s).toLowerCase().match(/[a-zäöüß0-9-]{4,}/g) || []).filter(w => !STOP.has(w)));

export function refersToRun(text, run) {
  if (!run) return false;
  if (REF.test(text)) return true;
  const r = content(run);
  for (const w of content(text)) if (r.has(w)) return true;
  return false;
}

/* model: Absicht vom Modell; run: Text des laufenden Auftrags oder null.
   Liefert 'submit' | 'revise' | 'cancel' | 'progress' | 'none' | 'choose' (= nachfragen: neu oder ändern?). */
export function resolveIntent(model, text, run) {
  let k = model;
  if (k === 'progress' && !STATUS.test(text) && CHECK.test(text)) k = 'submit';      // „Kannst du nachsehen, ob …“ ist Arbeit, kein Status
  if (!run || (k !== 'submit' && k !== 'revise')) return k;
  const ref = refersToRun(text, run);
  if (k === 'revise' && !ref) return 'choose';
  if (k === 'submit' && ref) return 'choose';
  return k;
}

/* Eindeutiges Gespräch (Gruß, Dank, Lob, Wissensfrage) braucht keine Absichtserkennung – spart ~1 s bis zur Antwort.
   Bewusst eng: sobald Auftrags-, Status- oder Prüfwörter vorkommen, entscheidet das Modell. Übersehen heißt: altes Verhalten. */
const CHAT_WHOLE = /^(?:hallo|hi|hey|servus|moin|guten (?:morgen|tag|abend)|gute nacht|danke(?: dir| schön| sehr)?|vielen dank|super|cool|toll|klasse|perfekt|prima|gut gemacht|du bist .{2,40})(?:,? ?jarvis)?$/iu;
const CHAT_START = /^(?:was (?:ist|sind|bedeutet|heißt|heisst|meint|versteht man)|wer (?:ist|war|hat)|wie (?:heißt|heisst|spät|viel ist|alt|groß|gross)|warum|wieso|weshalb|erklär(?:e)? mir|erzähl(?:e)? mir|kennst du|weißt du|weisst du)(?![\p{L}])/iu;
export function obviousChat(text) {
  const t = String(text).trim().replace(/[.!?]+$/, '').trim();
  if (STATUS.test(t) || CHECK.test(t) || REF_WORDS.test(t) && !CHAT_WHOLE.test(t)) return false;
  return CHAT_WHOLE.test(t) || CHAT_START.test(t);
}

export const isNew = raw => /^(?:neu(?:e[rn]?)?(?: auftrag)?|ein neuer(?: auftrag)?|neuer auftrag bitte)(?: bitte)?$/i.test(String(raw).toLowerCase().replace(/[.,!?]/g, '').trim());
export const isChange = raw => /^(?:ändern|änder|aendern|ändere ihn|ändere den|den ändern|den laufenden(?: ändern)?|änderung)(?: bitte)?$/i.test(String(raw).toLowerCase().replace(/[.,!?]/g, '').trim());
