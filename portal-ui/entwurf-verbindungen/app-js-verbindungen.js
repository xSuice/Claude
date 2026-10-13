// ENTWURF, nicht eingebaut. Ziel: portal-ui/web/app.js
// 1) TABS (Zeile 63): ['verbindungen', 'Verbindungen'] vor ['system', 'System'] einfuegen
// 2) ICONS (Zeile ~17): verbindungen: '<path d="M9 7V3M15 7V3M7 7h10v4a5 5 0 01-10 0zM12 16v5"/>'
// 3) ROUTES (Zeile 1598): verbindungen ergaenzen
// 4) Funktion unten einfuegen (nur Admin, die Route /api/claude/op prueft das ohnehin)
// 5) Op 'connectors' in der Portal-Route freischalten: patch-portal-claudeops.py, Liste der erlaubten Ops ergaenzen
// 6) VERSION in app.js und sw.js hochzaehlen

async function verbindungen() {
  view.innerHTML = head('Verbindungen', 'Konten, die Claude nutzen kann') + '<div class="skeleton"></div>';
  const d = await cop('connectors', {});
  if (!d.ok) { view.innerHTML = head('Verbindungen') + '<div class="empty">' + esc(d.error || 'Keine Daten') + '</div>'; return; }
  const label = { ok: 'verbunden', login: 'Anmeldung nötig', fehler: 'Fehler' };
  const rank = { login: 0, fehler: 1, ok: 2 };
  const items = d.items.slice().sort((a, b) => rank[a.state] - rank[b.state] || a.name.localeCompare(b.name));
  const need = items.filter(x => x.state !== 'ok').length;
  view.innerHTML = head('Verbindungen', items.length + ' Verbindungen · ' + need + ' brauchen Aufmerksamkeit') +
    '<div class="list">' + items.map(x => '<div class="row"><div><b>' + esc(x.name) + '</b><div class="sub">' + esc(x.url) + '</div></div><span class="tag">' + label[x.state] + '</span></div>').join('') + '</div>' +
    '<div class="empty">Anmelden geht nur in den Konnektor-Einstellungen von claude.ai, nicht hier. Im Chat gelten die Verbindungen nur im Modus „konnektoren“ und „voll“.</div>';
}
