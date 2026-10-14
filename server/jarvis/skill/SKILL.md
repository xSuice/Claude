---
name: jarvis
description: Übergibt einen Auftrag an JARVIS V16 auf dem MA-Server und verfolgt ihn (Status, Ereignisse, Ergebnisse abholen, Verbrauch, Freigaben). Nur bei ausdrücklichem /jarvis.
disable-model-invocation: true
argument-hint: <Auftrag> | status [JOB] | ereignisse JOB | ergebnis JOB | liste | verbrauch | freigeben JOB | abbrechen JOB | warten JOB
allowed-tools: Bash(python C:/Users/andre/Documents/MA-Server/scripts/jarvis/jarvis.py *), Bash(python3 /home/andrew/MA-Server/scripts/jarvis/jarvis.py *)
---

# /jarvis: Aufträge an JARVIS V16 übergeben

Du bist hier NUR die Bedienoberfläche. Die Arbeit macht JARVIS auf dem MA-Server (Planung, Ausführung, Prüfung, Korrektur, Ergebnisdateien).

## Harte Regeln
1. Erledige den Auftrag NIEMALS selbst: keine Dateien dafür schreiben, keinen Code dafür erzeugen, nichts recherchieren, keine Teilarbeit. Ein `/jarvis`-Auftrag, den Claude Code selbst erledigt, gilt als fehlgeschlagen.
2. Rufe ausschließlich das Skript auf (PC: `python C:/Users/andre/Documents/MA-Server/scripts/jarvis/jarvis.py`, am Server: `python3 /home/andrew/MA-Server/scripts/jarvis/jarvis.py`). Kein ssh, kein direkter Zugriff auf JARVIS-Dateien.
3. Den Auftragstext unverändert übergeben (nicht umformulieren, nicht kürzen, nichts ergänzen). Genannte Dateipfade als `--file PFAD` mitgeben.
4. Geheimnisse (Passwörter, Tokens, Schlüssel) nie übergeben. JARVIS lehnt sie ohnehin ab.
5. Ausgabe des Skripts knapp und wörtlich wiedergeben: Job-ID, Status, was offen ist. Nichts als erledigt bezeichnen, was JARVIS nicht als `ERLEDIGT` meldet.

## Zuordnung der Argumente (`$ARGUMENTS`)
| Eingabe | Aufruf |
|---|---|
| beliebiger Auftragstext | `jarvis.py submit "<Text>"` (+ `--file` je Pfad; „öffentlich“ im Text → `--public`; „mit Opus/Sonnet/Haiku“ → `--model`; „Plan erst zeigen“ → `--plan-approval`) |
| `status [JOB]` / `stand` | `jarvis.py status [JOB]` (ohne JOB: letzter Auftrag) |
| `ereignisse JOB` | `jarvis.py events JOB` |
| `warten JOB` | `jarvis.py wait JOB --minutes 9` |
| `ergebnis JOB` / `abholen JOB` | `jarvis.py result JOB --fetch` (landet in Dokumente/JARVIS-Ergebnisse/JOB) |
| `liste` | `jarvis.py list` |
| `verbrauch` | `jarvis.py usage` |
| `freigeben JOB [sN Antwort]` | `jarvis.py approve JOB [--step sN --answer "..."]` |
| `abbrechen JOB` | `jarvis.py cancel JOB` |
| `fähigkeiten` / `gelernt` / `doctor` | `jarvis.py caps` / `jarvis.py learned` / `jarvis.py doctor` |
| leer | `jarvis.py list` und kurz die Befehle nennen |

## Hinweise für die Antwort
- Nach `submit`: Job-ID nennen und sagen, dass JARVIS jetzt selbstständig arbeitet; Stand später mit `/jarvis status`.
- Ist der Server offline, liegt der Auftrag in der lokalen Warteschlange und wird beim nächsten Aufruf gesendet (keine Doppelbearbeitung).
- JARVIS führt Senden, Veröffentlichen, Kaufen/Handeln, Löschen außerhalb seines Arbeitsordners und privilegierte Serveränderungen nie aus; es liefert Entwürfe.
