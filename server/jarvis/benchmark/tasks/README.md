# Benchmark-Aufgaben V16 (Stand 2026-10-15, gebaut ohne Claude-Aufrufe)

Je Aufgabe: `aufgabe.md` (Text, wie er JARVIS/Claude gegeben wird), `gen.py` (Eingabegenerator mit festem Seed + Referenzauslegung), `check.py` (Prüfung gegen verdeckte Eingaben mit anderem Seed, läuft im Sandbox-Jail, Ausgabe JSON). Aufruf: `python3 tasks/Txx-.../check.py ERGEBNISORDNER`.

| ID | Typ | Held-out |
|---|---|---|
| T01 | coding.python_cli (Zählerstände) | nein |
| T02 | coding.python_cli (Ausbildungsnachweis) | nein |
| T03 | coding.python_cli (Markdown-Inhaltsverzeichnis) | **ja** |
| T04 | doc (CSV -> DOCX-Tabelle) | nein |
| T05 | doc (PDF-Kurzbericht, reportlab) | **ja** |
| T06 | data (jq-Auswertung) | nein |
| T07 | media (WAV -> MP3) | nein |
| T08 | image (Kontaktbogen) | **ja** |
| T09 | analysis (Wortstatistik über Drop-in) | nein |
| T10 | coding.python_lib (Ringpuffer) | **ja** |
| T11 | mixed (Skript + DOCX-Bericht) | nein |
| T12 | java.build (PC) | nein; nur am PC mit freigegebenem Worker ausführbar |

Die Nummern der Benchmark-Tabelle in `docs/jarvis/BENCHMARK-V16.md` gelten (Held-out 3, 5, 8, 10). T01 (Primzahlen laut Dokument) wurde hier durch die vorhandene Zähler-Aufgabe ersetzt; das ist eine Abweichung vom Dokument und muss in der Auswertung genannt werden.

## Selbstprüfung der Prüfungen
`python3 selfcheck.py [ID ...]` baut je Aufgabe aus `refs/<ID>/` eine Referenzlösung, die die Prüfung vollständig bestehen muss, und prüft, dass ein leerer Ordner nie besteht. Die Referenzlösungen liegen unter `refs/` und dürfen **keinem** Lauf als Eingabe dienen (Held-out-Regel); sie beweisen nur, dass die Prüfungen lösbar und streng genug sind. Grenze: Der Leer-Test zeigt nicht, dass jede Prüfung jede falsche Lösung erkennt.

## Was die Prüfungen nicht belegen
Nutzung von Werkzeugen/Delegation (T09: `tool.wortstatistik`), Token, Kosten, Latenz und Korrekturrunden kommen aus dem JARVIS-Protokoll, nicht aus `check.py`. Menschliche Nacharbeit wird getrennt von Hand bewertet.
