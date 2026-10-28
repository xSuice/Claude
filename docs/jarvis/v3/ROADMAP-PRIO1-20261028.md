# ROADMAP PRIO 1 – Umsetzung der Architektur-/Referenzanalyse (Owner 28.10.2026: „dieser Auftrag hat jetzt Prio 1“)

Grundlage: `ARCHITEKTUR-REFERENZANALYSE-20261028.md`. Leitsatz: kein Plattform-Neubau. Ausgebaut werden die fünf Verträge Task, Council, Capability, Router und Knowledge. Fremdprojekte dienen nur als Muster oder als Bauteil.

| # | Paket | Status | Beleg |
|---|---|---|---|
| 1 | **Auftrag ändern** (Task-ID + unveränderliche Revisionen, CAS, Fencing, neustartfest, Sprache/Portal) | ✅ **live 28.10.** | Release `20261028-074307-6245dd0`: 433/433 Tests (4 übersprungen), 10 neue Revisionstests; Live-Kette über die Brücke; Browser-E2E per Sprache; Commits `6245dd0`, `8f12241` |
| 2 | Fach-Councils (8 Gruppen, Decision Artifact, nur beratend technisch erzwungen, Metriken) | offen – nächstes Paket | – |
| 3 | Smart Router aktivieren (Policy-Score, harte Filter, Provider-Aliase, Quoten-Ledger mit `confidence`, Shadow-Eval → Canary) | offen | – |
| 4 | Living HQ mit normalisierten AgentEvents (Pixel-Agents-Muster, eigene Figuren) | offen | – |
| 5 | Memory Distiller (Kandidaten aus abgenommenen Aufträgen, Provenienz, Dedupe, Review-Queue) | offen | – |
| 6 | Sprache < 4 s (Streaming-Überlappung STT/LLM/TTS) | teilweise: 5–6 s | APPROVAL_MATRIX VOICE-004 |
| 7 | Basis-GO-Gate | offen | Kriterien siehe Analyse |
| 8 | Capability-Broker + Approval + Audit + Secrets-Refs + 3-stufiger Kill | offen (vor Phase C Pflicht) | – |
| 9 | Phase C als Capability-Folge | nicht begonnen | – |

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
