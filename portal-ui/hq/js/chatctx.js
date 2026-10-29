/* MA-HOME HQ — Chat-Weiche: letzter abgeschlossener Austausch als Kontext für Fachrollen (die Weiche schickt Fachfragen
   an Hermes-Rollen, die den Claude-Gesprächsverlauf nicht kennen). Wird auf dem Server als „nur Kontext“ markiert. */
export function lastExchange(msgs, max = 1500) {
  const list = Array.isArray(msgs) ? msgs : [];
  let a = -1, u = -1;
  for (let i = list.length - 1; i >= 0; i--) {
    if (a < 0 && list[i].r === 'a' && list[i].t && !list[i].live) a = i;
    if (list[i].r === 'u' && (a < 0 ? true : i < a)) { u = i; break; }
  }
  const q = u >= 0 ? String(list[u].p || list[u].t || '').trim() : '';
  const ans = a > u && a >= 0 ? String(list[a].t).trim() : '';
  const out = (q ? 'Andrew: ' + q : '') + (ans ? (q ? ' | ' : '') + 'JARVIS: ' + ans : '');
  return out.length > max ? out.slice(0, max - 1) + '…' : out;
}
