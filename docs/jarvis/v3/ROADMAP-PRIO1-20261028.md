# ROADMAP PRIO 1 – Umsetzung der Architektur-/Referenzanalyse (Owner 28.10.2026: „dieser Auftrag hat jetzt Prio 1“)

Grundlage: `ARCHITEKTUR-REFERENZANALYSE-20261028.md`. Leitsatz: kein Plattform-Neubau. Ausgebaut werden die fünf Verträge Task, Council, Capability, Router und Knowledge. Fremdprojekte dienen nur als Muster oder als Bauteil.

| # | Paket | Status | Beleg |
|---|---|---|---|
| 1 | **Auftrag ändern** (Task-ID + unveränderliche Revisionen, CAS, Fencing, neustartfest, Sprache/Portal) | ✅ **live 28.10.** | Release `20261028-074307-6245dd0`: 433/433 Tests (4 übersprungen), 10 neue Revisionstests; Live-Kette über die Brücke; Browser-E2E per Sprache; Commits `6245dd0`, `8f12241` |
| 1b | **Abbruch-Fencing** (Live-Befund: Abbruch während der Planung wurde vom späten Plan überschrieben) | ✅ live | `ae1ca74`; 3 Tests, gegen den alten Code nachweislich rot |
| 2 | **Fach-Councils**: 8 Gruppen, ≤ 5 Rollen an jarvis-*-Profile gebunden, ohne Werkzeuge, Decision Artifact je Revision, Dissens sichtbar, Block-Votum erzwingt Plan-Freigabe, Metriken | ✅ live, aktiviert | `e81f1b2`; Live: SECURITY-Council, 3 Rollen, 30 s, 16,7k Token, 4 Einwände, Konfidenz 0,83 |
| 3 | **Smart Router**: harte Filter, gewichteter Score, Aliase, Budgets mit Herkunft, Ausweichen bei Störung, Shadow-Log, Canary nur für Claude-Modelle, Backtest | ✅ live im **Shadow-Modus** | `9e6b924`; Backtest auf 180 Aufrufen: 0 Policy-Verstöße. Befunde behoben: Kontingentgrenzen galten als Modellfehler; „Markdown“ wurde als „down“ = critical erkannt; der alte Tier 1 war wirkungslos und hätte `kimi_pro` an die Claude-CLI gegeben |
| 4 | **Living HQ aus echten Ereignissen** (normalisierte AgentEvents, kein Zufall, kein Phantom-Arbeiten) | ✅ live | `f093c20` |
| 5 | **Memory Distiller** (Kandidaten nur nach bestandener Abnahme, Evidenz, Dedupe und Widerspruch, Review-Queue, Vault nur nach Freigabe) | ✅ live | `f093c20`, `707dbb8`; Live: 1 Kandidat wartet im Command Center auf dich |
| 6 | **Sprache < 4 s** | ⚠️ verbessert, nicht belegt | künstliche Stimme: 4,5–5,4 s statt 6,2–6,7 s. Dein Handytest steht aus |
| 7 | **Basis-GO-Gate** | ⏳ 9/11 ✅ | `BASIS-GO-20261028.md` |
| 8 | **Capability-Security-Kern**: Broker, Audit (redigiert), einmalige Freigabe gebunden an Revision + Schritt + Parameter, Secret-Scope, Not-Aus SOFT/EXEC/HARD ohne KI, Anti-Stagnation | ✅ live | `5ca1f27` (vom Release-Skript wegen eines roten Tests korrekt abgelehnt), `58e1c37`; Broker-Panel mit Not-Aus im Command Center |
| 9 | **Phase C** als Capability-Folge (C1 `browser.read` …) | ⏸ wartet auf Basis-GO | 26 Ziel-Fähigkeiten im Broker als „nicht registriert“ → werden abgelehnt |

Aktives Release: `20261028-092016-58e1c37` mit 486 Tests (4 übersprungen). Repo: `f7f9419`.

## Owner-Entscheidungen (nicht automatisch)
1. **Router auf Canary**: Empfehlung nach etwa 1 Woche Shadow: `router.mode=canary`, `canary_pct=10`.
2. **Moonshot und OpenRouter anbinden**: Dafür braucht es Konten und Schlüssel (Kosten).
3. **Gespräch: Claude zuerst oder Qwen zuerst**: Empfehlung Claude zuerst. Qwen 8B passt nicht ganz in den Grafikspeicher und hat in den Tests Fakten erfunden.
4. **Watchdog L3** (automatischer Neustart von Brücke oder Worker): ja oder nein.
5. **Phase C** erst nach deinem Handy- und Stimmtest.

## Paket 1 – was genau gilt jetzt
- Eine Änderung erzeugt **Revision N+1 mit derselben Auftragsnummer**. Die alte Anfrage, der Änderungstext, der Urheber (`portal:<user>`/`cli:<user>`) und der Zeitpunkt stehen in `job_revisions`. Die alten Schritte werden als Momentaufnahme gesichert (`superseded_steps`).
- **Compare-and-Set:** Eine Änderung, die von einer veralteten Revision ausgeht, wird abgewiesen („Revision veraltet: aktuell 2, erwartet 1“). Gleichzeitige Änderungen: genau eine gewinnt (Test mit 5 Threads).
- **Fencing:** Ein Schritt, ein Plan oder ein Abschluss der alten Revision schreibt nichts mehr (Ereignis `superseded`). PC-Ergebnisse einer alten Revision werden **vor** dem Entpacken abgelehnt, und die PC-Sperre wird freigegeben.
- Neue Wirkungen der Änderung (z. B. `sudo`) werden klassifiziert und erzwingen wieder eine Plan-Freigabe. Geheimnis-Muster werden abgewiesen, ebenso abgeschlossene Aufträge und Änderungen ohne bekannten Urheber.
- Unter Not-Aus sind keine Änderungen möglich.
- Der Arbeitsordner bleibt erhalten, sodass die neue Planung schon erstellte Dateien weiterverwenden kann.
- **Sprache:** „Ändere den Auftrag: …“ → JARVIS liest das Verstandene vor → nur „Ja“ ändert, mit `expected` = aktuelle Revision.
- **Portal:** Plakette „Rev. N“, Liste der Änderungen, Feld „Auftrag ändern“.
- **Sprachabbruch ≠ Auftragsabbruch** bleibt unverändert.

Kosten der Live-Tests: 2 Testaufträge, zusammen 3 Claude-Aufrufe, ca. 0,10 USD (Listenpreis-Äquivalent, im Abo enthalten).
Rückweg: `bash ~/MA-Server/server/jarvis/rollback-v16.sh`. Die neuen Spalten sind additiv mit Standardwert 1, der alte Code läuft also mit der migrierten Datenbank weiter. Die Datenbanksicherung von vor dem Release liegt unter `~/.local/share/ma-jarvis/backups/20261028-074307/`.
