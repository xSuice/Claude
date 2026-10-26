# JARVIS V16 – Unabhängiger Fähigkeitstest, Teil 1: Bestandsmessung (2026-10-15)

Reine Lesemessung. Nichts repariert, keine Einstellung geändert (außer der bekannten Plan-Grenze, siehe unten). Belege: `doctor`/`usage`/`learned`/`caps`/`meta`/`list` am laufenden System, Quellcode in `~/.local/share/ma-jarvis/current/brain-runtime/`, Berichte vom 2026-10-14/15.

Skala: 0 nicht vorhanden · 1 nur dokumentiert · 2 implementiert, ungeprüft · 3 teilweise funktionsfähig · 4 durch echte Tests bestätigt · 5 durch vollständigen Praxistest bestätigt.

| # | Fähigkeit | Stufe | Beleg |
|---|---|---|---|
| 1 | Sprachverständnis, Kontext | 2 | Aufgabentyp und Datenklasse per Regex (`taskengine.py` Z. 105–111) plus Claude-Planschritt. 33 von 43 Aufträgen/24 h `done`, aber alle mit klar formulierten Aufträgen. Kurze, fehlerhafte oder mehrdeutige Prompts nie getestet. |
| 2 | Auftragsplanung | 4 | Planschritt in jedem Claude-Auftrag (Ereignisse `planned`, `step_done`), Job `j20261015-6a27fc`. Bei bekanntem Typ entfällt Planung (`template:N:exact`). |
| 3 | Gedächtnis, Wissensabruf | 2 | `knowledge_index.py` (409 Zeilen), `brain.db`. Kein Beleg, dass ein Auftrag Wissen abruft; Claude-Worker lesen Vault/Auto-Memory bewusst nicht (`PORTAL.md`). |
| 4 | Autorisierte Unterlagen verknüpfen | 1–2 | Kein Datenquellenregister. Index-Code vorhanden, Nutzung ungeprüft. |
| 5 | Überprüfbares Lernen | 3 | 15 Vorlagen, davon eine `retired` (Nr. 12: 1 Erfolg, 2 Fehler) → Rückzug funktioniert. Aber: „Vorlage mit schwacher Abnahme kann Fehler als Erfolg lernen" (SCHWACHSTELLEN #6, nicht gebaut). Probelauf-Gate: `improve.probelauf_docstring` 2 von 5 ok. |
| 6 | Werkzeugerkennung/-wahl | 4 | 9 serverseitige Fähigkeiten `tested` (Sandbox-Selbsttest), Schritte s2/s3 laufen in bwrap. `ollama.ask` nur `available`, `blender.render` `missing`. |
| 7 | Zusammenarbeit mit Claude Code | 4 | `claude -p` mit Read/Write/Edit/Glob/Grep, 70 Aufrufe/24 h im Ledger. **Ohne Bash**, Tests führt JARVIS selbst aus. |
| 8 | MA Auto Router | 2 | `router: true`, `router_mode: shadow`; in Ereignissen keine Router-Entscheidung (INTEGRATIONSPRUEFUNG-V16). |
| 9 | Weitere KI-Helfer | 2 | Code vorhanden, `providers: null`, Limit 0, Doctor „not configured". Bewusst aus. |
| 10 | Fehlererkennung, Korrektur | 3 | `fix_rounds` 2 im Budget; Metakognition: `python_cli` Ø 0,23 Korrekturrunden, `probelauf` Ø 1,0. Abnahme und `check.py` weichen ab (T09, T11) – ungeklärt. |
| 11 | Fortsetzung unterbrochener Aufgaben | 2 | `recover()` (`taskengine.py` Z. 493), Gate B nur gegen Fakes. Live nie unterbrochen. |
| 12 | Wiederverwendung | 3 | `template:1:exact`: 1 statt 3 Aufrufe, −61 % Token, **n=1**; Vorlagen mit uses/successes in `learned`. Geänderte Voraussetzungen nie getestet. |
| 13 | Selbstständige Weiterentwicklung | 3 | `improve.py` mit Probelauf-Gate (max 3/Tag); 5 Läufe, 2 ok. Kein Praxisfall mit echter Änderung belegt. |
| 14 | Webportal | 3 | Brücke mit identischer Nachricht getestet; Rauchtest 82/82 nur mit Platzhaltern; Browser→Authelia→Anzeige/Download ungeprüft. |
| 15 | Benutzertrennung, Datenschutz | 3 | Identitäts-Ledger, Datenklasse-Regex, Secret-Muster blockiert; `jarvis_api` mit fremdem Benutzer getestet. Kein eigenes OS-Konto, PC-Worker ohne Sandbox (aus). |
| 16 | Token-, Kosten-, Ressourcenmanagement | 4 | Ledger live (70 Aufrufe, 1,22 Mio Token, 5,28 USD Listenpreis-Äquivalent/24 h), Job-Budget 8 Aufrufe/600 000 Token. **Plan-Guard jetzt aus (101 %) auf Anweisung von Philipp 10:2x.** Last während Jobs nie gemessen. |

## Aufträge der letzten 24 h
20 Einträge in `list`: 16 `done`, 2 `partial`, 2 `cancelled` (davon `j20261015-c9935f` mein Hook-Test, `j20261015-2080b5` der abgebrochene Mobile-Auftrag).

## Bekannte Grenzen der Messung
- A-Läufe T04/T06/T07/T09/T11 mit Standarddaten ungültig (leere Eingaben). Gültig: A2 Seed 7/11/12, Lauf B T01/T02.
- Alle Benchmark-Zahlen n=1 je Zelle. Held-out T03, T05, T08, T10 nicht angefasst.
- Herkunft nicht verifiziert: Erfolgsraten aus `meta` beruhen auf JARVIS' eigener Abnahme, nicht auf unabhängiger Prüfung.

## Zwischenfazit (Fakten vs. Schluss)
Fakten: Kern (Auftrag → Plan → Claude → Sandbox-Test → Abnahme → Vorlage) läuft live. Router, Helfer, Wissensabruf, Wiederaufnahme und Portal-Browserweg sind nicht live belegt.
Schluss: JARVIS ist ein zuverlässiger Auftragsausführer für klar formulierte Python/Daten-Aufgaben, kein belegt „intelligenter" Assistent für vage Prompts. Das ist bisher **nicht gemessen**, nicht widerlegt.
