/* Read-only presentation of existing /api/jarvis usage data. No provider-quota inference. */
export function renderLedger(data) {
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const count = value => Number.isFinite(value) && value >= 0 ? String(value) : '–';
  if (!data || !data.ledger) return '<div class="faint">Ledger nicht verfügbar.</div>';
  const ledger = data.ledger;
  const rows = ['claude','helper'].filter(k => ledger[k]).map(k => {
    const b=ledger[k], limits=b.limits || {};
    const cap = (v,l) => l === 0 ? 'deaktiviert' : count(v) + ' / ' + count(l);
    return '<div class="hqk">'+escape(k)+'</div><div class="ccrow"><span>Aufrufe / 24 h</span><span class="mono">'+cap(b.calls_24h,limits.calls_per_day)+'</span></div>'+
      '<div class="ccrow"><span>Token / 24 h</span><span class="mono">'+cap(b.tokens_24h,limits.tokens_per_day)+'</span></div>';
  }).join('');
  return '<h2 class="holo-title">JARVIS-Ledger<span class="sub">Lokale Limits, keine verifizierten Provider-Restkontingente</span></h2>'+rows+
    '<div class="ccrow"><span>Cache-Zähler, Jobs / 24 h</span><span class="mono">'+count(data.jobs_24h?.cache)+'</span></div>'+
    (ledger.plan_block ? '<div class="chip crimson">Plan-Schutz: '+escape(ledger.plan_block)+'</div>' : '')+
    '<div class="faint">Quelle: /api/jarvis, cmd=usage. Listenpreiswerte sind keine Rechnung.</div>';
}
