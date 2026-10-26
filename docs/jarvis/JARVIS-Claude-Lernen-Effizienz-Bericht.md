# JARVIS-Claude-Lernen-Effizienz-Bericht (Stand 2026-10-15 10:05, Server)

Teilbericht. Nicht alles aus dem Gesamtauftrag ist umgesetzt oder gemessen; unten steht genau, was fehlt.

## Statuskategorien (am laufenden System geprüft)
| Bereich | Status | Beleg |
|---|---|---|
| Git `~/MA-Server` | vorhanden, 7 unbeteiligte uncommittete Dateien (router.disabled, ops-Skill, READMEs, setup-status) | `git status` |
| JARVIS V16 (Release 20261015-040726-91bb3b8) | nachweislich ausgeführt | `doctor`: ok, bwrap, claude_cli, Kill-Switch aus |
| Auftragsfluss Brücke → JARVIS → Claude → Ergebnis | nachweislich ausgeführt (Job j20261015-6a27fc, 3/3, 7/7) | INTEGRATIONSPRUEFUNG-V16.md |
| HTTP-Weg Browser → Authelia → Portal, Download im Browser | unbekannt (nicht geprüft) | |
| Idempotenz | vorhanden (`taskengine.submit` mit `client_id`-Regex, Brücke `portal:user:key`); Doppel-Submit live nicht getestet | Quellcode |
| Worker-Identität | vorhanden: `JARVIS_WORKER=1` setzt nur `workers.py` | `workers.py` Z. 66 |
| Laden Worker die User-Hooks? | unbekannt (`claude -p` ohne `--setting-sources`); Schutz deshalb über `JARVIS_WORKER` | |
| Router | konfiguriert (`shadow`), Wirkung nicht belegt | |
| Externe Helfer | bewusst aus (Limit 0) | `doctor` |
| Erzwingende Weiterleitung neuer Aufträge | war nur beschrieben; Hook jetzt **aktiviert** (10:08) | unten |
| Datenquellenregister, Erfahrungsspeicher, Break-Glass-Anleitung | **nicht umgesetzt** | |
| Vorher/Nachher-Messung | **nicht möglich**: A-Läufe T04/T06/T07/T09/T11 ungültig (leere Eingaben); Wiederholung `run_fix.py` wurde vor Ergebnis beendet (keine Ergebnisdatei) | |

## Serverlast (10:00)
RAM verfügbar 1,8 GB von 3,3 GB, Swap 120 MB, PSI mem 0, PSI io 1,9 %, Last/CPU 0,61.

## Blockade
`doctor`: `plan_block: plan 5h window at 79.0% (limit 70%)`. Neue Aufträge mit Claude-Plan werden gerade abgewiesen; `run_fix.py` wurde beendet (10:07); Stand danach 83 % (Fenster läuft ab, kein Sofort-Effekt). 24 h: 70 Aufrufe, 1,22 Mio. Token (Listenpreis-Äquivalent 5,28 USD, keine Rechnung).

## Neu: Weiterleitungs-Hook (Staging im Repo)
`scripts/jarvis-hook/jarvis-submit-hook.py`, Tests `scripts/jarvis-hook/tests/test_hook.py` (7/7 grün, gegen Fake-Brücke).
- Leitet nur Nachrichten weiter, die mit `jarvis:` oder `@jarvis` beginnen; Gespräche und Status bleiben unberührt.
- Übersprungen bei `JARVIS_WORKER=1` und `direkt:` (kein Rückweg Worker → JARVIS).
- `client_id` = Hash aus Sitzung und Text: gleiche Eingabe, derselbe Job.
- Fail-open: Brücke weg → Meldung „Annahme UNBEKANNT", keine stille Claude-Alleinausführung, keine Blockade.
- Protokoll `~/.claude/jarvis-hook.log` nur Zeit, Job-ID, Client-ID.
- Echt getestet (10:08): Auftrag `jarvis: kleiner Test…` → Job `j20261015-c9935f` (queued); identische Eingabe erneut → **dieselbe Job-ID** (Idempotenz belegt). Der Testjob wurde danach per `cancel` abgebrochen (`cancelled`, 0 Aufrufe, 0 Token).

Aktivierung (erfolgt mit `scripts/jarvis-hook/aktivieren.py`, Sicherung `~/.claude/settings.json.vor-jarvis-hook`, Rückbau `aktivieren.py entfernen`; wirkt erst in neu gestarteten Sitzungen, dort noch nicht geprüft). Manuell wäre es: in `~/.claude/settings.json` unter `hooks.UserPromptSubmit` den Befehl `python3 /home/andrew/MA-Server/scripts/jarvis-hook/jarvis-submit-hook.py` (Timeout 25) ergänzen; Rückbau durch Entfernen. Danach in neuer Sitzung prüfen.

## Offen
Datenquellenregister, Erfahrungsspeicher mit Prüfstatus, Break-Glass-Anleitung, Tests B–G, Messvergleich, Portal-Download, einzelne Kennzeichnungen „nur Jarvis"/„nur Claude" nicht ausgelöst.

## Dateien
Test: `python3 -I scripts/jarvis-hook/tests/test_hook.py`
