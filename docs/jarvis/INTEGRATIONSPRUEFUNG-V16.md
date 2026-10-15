# Integrationsprüfung vor dem Mobile-Test (2026-10-15, Server)

Abschnitt zum Einfügen vor den Mobile-Test. Alle Aussagen sind am laufenden Server geprüft; ein Konfigurationseintrag oder ein früherer Bericht gilt nicht als Nachweis.

## Integrationstest (klein, reversibel, isoliert)

- Auftrag `j20261015-6a27fc`, eingereicht über den Brücken-Socket `/run/ma-claude/bridge.sock` mit demselben Nachrichtenformat (`op: jarvis`, `cmd: submit`), das `POST /api/jarvis` im Portal sendet. Aufgabe: `slug.py` + `test_slug.py` (unittest) + `README.md`, nur Standardbibliothek.
- Ergebnis: `done`, 3/3 Ergebnisdateien von der unabhängigen Abnahme bestanden, 2 Claude-Aufrufe (Plan + 1 Inhaltsschritt, Modell sonnet), 21 048 neue Token, 0 Korrekturrunden.
- Unabhängig nachgeprüft (eigener `unittest`-Lauf, ohne Schreibzugriff): 7 von 7 Tests grün.
- Verlauf über `events` mit derselben Auftrags-ID: submitted → claude → planned → step_done s1–s3 → finished → attribution.
- Kennzeichnung im Ereignis `attribution`: „Jarvis + Claude: Jarvis – 2 lokale Werkzeugschritte, unabhängige Abnahme; Claude – 1 Inhaltsschritt (sonnet), Plan erstellt".
- Es wurden keine produktiven Dateien verändert; geschrieben wurde nur nach `/srv/ma-home/library/JARVIS/j20261015-6a27fc/`.

## Übersicht

| Komponente | vorhanden | konfiguriert | tatsächlich getestet | Nachweis | Einschränkung |
|---|---|---|---|---|---|
| Portal-Reiter und `POST /api/jarvis` | ja (`/opt/ma-home/portal.py`, `web/app.js`) | ja | **teilweise**: Brücken-Socket mit identischer Nachricht, nicht der HTTP-Weg | Auftrag `j20261015-6a27fc` | Flask und Authelia nicht durchlaufen (keine Sitzung vom Server aus). Browser-Rauchtest mit Platzhaltern ist älter (82/82). |
| Claude-Brücke → `jarvis_cli` | ja | ja, Dienst aktiv | ja | submit, status, events über Socket; nach dem Update (08:18) `diff` zum Repo gleich, Dienst aktiv, `status` antwortet | Update von Philipp eingespielt, Dateivergleich belegt es. `Claude:`-Kennzeichnung im Chat nach dem Update nicht gesondert getestet. |
| JARVIS-Auftragsverwaltung und Ausführung | ja | ja | ja | 15+ Aufträge heute, Cron-Takt arbeitet ab | `doctor` meldet `cron_tick: false`, weil `crontab -l` in dieser Umgebung gesperrt ist; der Takt läuft nachweislich. |
| Claude als Modellaufruf (Text) | ja | ja | ja | Plan-Schritt je Auftrag (`claude_done`, sonnet) | Plan-Guard 70/85 %, aktuell `plan_block: null`. |
| Claude Code (`claude -p` mit Dateiwerkzeugen) | ja | ja | ja | Inhaltsschritt `s1` schreibt Dateien; 9 Runden in T04 | **Nur Read/Write/Edit/Glob/Grep, ohne Bash** (`workers.py`). Kein Build, kein Testlauf durch Claude selbst. |
| Ausführbarer Test | ja | ja | ja | Schritte s2 (Syntax) und s3 (Unittests) laufen in der bwrap-Sandbox durch JARVIS | Das beweist die JARVIS-Sandbox, nicht Claude mit Entwicklungswerkzeugen. |
| MA Auto Router | ja (`router: true`) | `router_mode: shadow` | **nein** | Nur Konfiguration und `doctor` | In den Ereignissen eines Auftrags erscheint keine Router-Entscheidung; Wirkung nicht belegt. |
| Externe KI-Helfer | Code ja | **nein** (`providers: null`, Limit 0) | nein | `doctor`: „helpers: not configured" | Bewusst nicht freigegeben. Teilauftrag an einen Helfer nicht möglich. |
| Rückgabe in denselben Auftrag / dieselbe Portalkonversation | ja | ja | **teilweise** | Status und Ereignisse über dieselbe Auftrags-ID abrufbar | Portal fragt per Status und Ereignisverlauf ab; Anzeige im Browser nicht live geprüft. |
| Kennzeichnung Jarvis / Claude / Jarvis + Claude | ja | ja | ja | Ereignis `attribution` in `j20261015-70cc18` und `j20261015-6a27fc` | Nur „Jarvis + Claude" erlebt; „nur Jarvis" und „nur Claude" nicht ausgelöst. Im Claude-Chat fehlt `Claude:` bis zum Brücken-Update. |
| Ergebnisdateien und Download | ja | ja | **teilweise** | Dateien und `manifest.json` unter `/srv/ma-home/library/JARVIS/<Auftrag>/`, Pfad wie im Betrachter | Download über den Portal-Betrachter im Browser nicht geprüft. |
| Gedächtnis, Skills, Hooks, MCP-Werkzeuge | ja (Vault, `~/.claude/agents`, Hooks) | **für Worker bewusst aus** | nein | `--strict-mcp-config`, `--tools`, Minimal-Kontext (`workers.py`, `PORTAL.md`) | JARVIS nutzt eine eigene Wissensbasis (`brain.db`). Anbindung wäre eine Entscheidung und ein eigener Schritt. |
| Berechtigungen, Kostenlimits, Timeouts, Fehler | ja | ja | **teilweise** | Sandbox bwrap, ohne sudo; Budget 8 Aufrufe/600 000 Token je Auftrag; Timeout 900 s; Anbieter-Limit führte bei T04 sauber zu „ungültig, 0 Token"; T09 scheiterte ordnungsgemäß mit Fehlermeldung | Tageslimits sind seit heute aufgehoben (Entscheidung offen). `human`/`approve` live weiter ungetestet. |

## Fehler und Aufwand

- Kein Integrationsfehler im getesteten Weg gefunden. Keine produktive Datei geändert.
- Hilfsmittel nur unter `~/tmp/bench/`: `bridge_call.py` (Socket-Aufruf), `submit_task_rep.py` (Wiederholung mit neuer `client_id`), `submit_a2b.py` (A2 ohne Saison-Parameter, nötig bei T04, T06, T07, T09, T11).
- Aufwand des Integrationstests: 2 Claude-Aufrufe, 21 048 neue Token. Getrennt von den Benchmarkläufen.
- Beobachteter Mangel im Benchmark (kein Integrationsfehler): Bei T09 A übergab der Plan `text.txt` relativ an `tool.wortstatistik`; das Werkzeug meldete `file not found`.

## Einschätzung

**Für den Mobile-Test ist die Integration teilweise einsatzbereit.**

- Belegt: Auftrag annehmen, über die Brücke ausführen, Claude als Plan- und Inhaltsschritt aufrufen, Ergebnis mit Test prüfen, Status, Ereignisse und Kennzeichnung unter einer Auftrags-ID, Ergebnisdateien am erwarteten Ort.
- Nicht belegt: der HTTP-Weg Browser → Authelia → Portal, die Anzeige und der Download im Browser, die Router-Wirkung, externe Helfer (nicht freigegeben).
- Brücken-Update ist erledigt (Dateivergleich gleich, 08:18). Kleinste verbleibende Ergänzung: ein Browser-Durchlauf (Auftrag senden, Verlauf sehen, Datei herunterladen). Philipp meldete „Ja, habe ich"; ein konkretes Ergebnis des Durchlaufs liegt nicht vor und ist hier nicht eingetragen. Er schließt die „teilweise"-Zeilen zu Portal, Rückgabe und Download.
- Nicht behauptet: Claude führt keine Entwicklungswerkzeuge (Bash, Build) aus. Das tut JARVIS in der Sandbox.

## Benchmark A2 (neue Daten, Seed 7), Nebenbefund

| Aufgabe | `check.py` | JARVIS-Abnahme | Aufrufe | neue Token |
|---|---|---|---|---|
| T04 | 16/16 | 5/5 | 1 | 26 607 |
| T06 | 15/15 | 6/6 | 1 | 16 737 |
| T07 | 19/19 | 5/5 | 1 | 17 901 |
| T09 | 14/15 | 5/5 | 2 | 32 167 |
| T11 | 21/21 | 6/7, Status `partial` | 3 | 39 929 |

Alle n=1. Bei T09 meldet JARVIS 5/5, `check.py` aber nur 14/15; bei T11 ist es umgekehrt (`check.py` 21/21, JARVIS `partial` 6/7). JARVIS-Abnahme und unabhängiges Prüfskript weichen ab, Ursache nicht untersucht.
