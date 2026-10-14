# JARVIS V16 – Benchmark-Gerüst (noch nicht ausgeführt)

Zweck: belegen, ob JARVIS gegenüber „Claude direkt am PC“ Token spart und gleich gute Ergebnisse liefert. Bisher gibt es **eine** Wiederholungsmessung (Primzahlen, −61 % Token, n=1). Das ist kein Benchmark.

## Methode

- Je Aufgabe zwei Läufe: **A** JARVIS (`jarvis.py submit`), **B** Claude direkt (gleiches Modell, gleicher Prompt, ohne JARVIS-Vorlage). Reihenfolge abwechseln, jeweils frischer Kontext.
- Zusätzlich je Aufgabe Lauf **A2**: dieselbe Aufgabe nochmals durch JARVIS (Lerneffekt).
- Gemessen (aus `status`/Ledger): neue Token, Cache-Token, Claude-Aufrufe, Korrekturrunden, Wartephasen, Wanduhrzeit, Listenpreis-Äquivalent.
- Qualität: Abnahmeprüfung von JARVIS **und** eigene, vorab festgelegte Prüfliste je Aufgabe (läuft das, Tests grün, Anforderungen erfüllt, ja/nein). Ergebnisdateien erst nach der Wertung ansehen, nicht vorher anpassen.
- Mindestens 3 Wiederholungen je Aufgabe, dann Median und Streuung. Bei n<3 nur als Einzelwert angeben.
- Held-out: 4 der 12 Aufgaben werden festgelegt und **nicht** vor der Messung durch JARVIS gelaufen (keine Vorlage, kein Tuning). Nur diese zählen für die Aussage „JARVIS spart“. Die übrigen 8 dienen zum Lernen und Debuggen.
- Last: pro Lauf Messung mit `measure_v16_load.py` (Leerlauf-Baseline: `messungen/2026-10-14-1-…`, Leerlauf mit Cron: `…-2-…`). Home Assistant (:8123) darf nicht auffällig langsamer werden.

## Aufgaben (Vorschlag, Philipp bestätigt)

| # | Typ | Aufgabe | Held-out | Prüfliste (Kern) |
|---|---|---|---|---|
| 1 | coding.python_cli | Primzahlen bis N mit Tests und README | nein (schon gelaufen) | Ausgabe korrekt, Tests grün, README |
| 2 | coding.python_cli | CSV-Summen je Spalte als CLI mit Tests | nein | Beispiel-CSV, Randfälle (leer, Text) |
| 3 | coding.python_cli | Markdown-Inhaltsverzeichnis-Generator | ja | Überschriftenebenen, Anker |
| 4 | doc | Markdown → DOCX mit Tabelle (pandoc) | nein | Datei öffnet, Tabelle da |
| 5 | doc | Kurzbericht als PDF (reportlab) | ja | Seitenzahl, Text prüfbar |
| 6 | data | JSON filtern/umformen (jq) mit Prüfung | nein | Ausgabe = Erwartung |
| 7 | media | WAV → MP3, Länge prüfen | nein | Dauer ±0,1 s |
| 8 | image | 5 Bilder skalieren, Kontaktbogen | ja | Maße, Anzahl |
| 9 | analysis | Textdatei: Wortstatistik als JSON (Drop-in `tool.wortstatistik`) | nein | Zahlen = Referenz |
| 10 | coding.python_lib | Kleine Bibliothek (Ringpuffer) mit Tests | ja | Tests, Kantenfälle |
| 11 | mixed | Skript + Bericht (DOCX) aus Messdaten | nein | beides vorhanden, konsistent |
| 12 | java.build (PC) | Minimal-Gradle-Projekt bauen | nein | Build grün; braucht `jarvis-pc.json` |

## Auswertung (Vorlage)

| # | A Token | B Token | A2 Token | Korrekturrunden A | Qualität A/B | Anmerkung |
|---|---|---|---|---|---|---|
| 1 | 30 442 | – | 11 779 | 0 | ja / – | n=1, B fehlt |

## Grenzen, die in den Bericht müssen

Gleiches Modell nur, wenn der Router nicht umschaltet (festlegen). Cache verzerrt Token-Vergleiche (neue und Cache-Token getrennt zeigen). Listenpreis-Äquivalent ist keine Rechnung (Abo). Server ist langsam (Celeron, HDD), Wanduhrzeit vergleicht Maschinen, nicht nur Methoden.
