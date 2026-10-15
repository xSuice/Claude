# JARVIS V16 Referenz-Audit (2026-10-15)

Quelle: Masterprompt Referenzanalyse. Stand: Fixes A9, A14, E2 am Quellcode, deployt als Release `20261015-140650-f57d32f`.

## Ergebnis in Kürze
- A9 (Geheimnisse in Aufträgen): neues Modul `secretscan.py`. Altes Muster erkannte 2 von 11 Testsätzen, neu 11 von 11, Fehlalarme 0 von 8 (beide Muster). Aufträge werden nur geschwärzt gespeichert.
- A14 (Scheinerfolg): `taskengine.approve` verlangt Urheber (`cli:` oder `portal:`) und bei Rückfrage eine Antwort. Eine unbeantwortete Rückfrage zählt nie als `done`. Aus lokalen oder unbeantworteten Jobs wird nicht gelernt.
- Kostenfragen werden lokal beantwortet (`local:usage`, 0 Claude-Aufrufe).
- E2 (Wiedererkennung): Wortstamm-Normalisierung statt Schwellen-Tuning. Leave-one-out auf echter Historie 21 auf 25 Treffer von 35, Fehltreffer 0. Feste 14 Paare: Recall 4/8 auf 7/8, Fehlalarme 0/6. Gemessen wird nur Wiedererkennung, NICHT Token-Ersparnis.
- Repos: 18 Metadaten erfasst, 10 am Quellcode gelesen (nichts ausgeführt), Rest nur Katalog. Funde: open-interpreter umgezogen und jetzt Rust; LibreChat leitet um; khoj AGPL; suna Lizenz unklar; restate-agent ohne LICENSE.
- Matrix: `JARVIS-REFERENZ-ENTSCHEIDUNGSMATRIX.csv` (213 Zeilen, 19 geprüft, Rest Nachweisstufe KATALOG). Repomap-PoC: 559.664 auf 5.933 Zeichen (nur Größe).

## Grenzen (dokumentiert)
- A9: Ein reines Wort nach „Passwort ist“ ohne Ziffer oder Symbol wird nicht erkannt.
- Urheber-Prüfung basiert auf Prozess-Metadaten. Gleiche uid kann die Umgebung fälschen. Echte Grenze wäre ein eigenes OS-Konto (braucht sudo).
- Portal-`app.js` nicht syntaxgeprüft (kein node).

## Nicht belegt
- Cron-Eintrag nach Installer-Abbruch: `crontab` aus dieser Sitzung nicht lesbar.
- Claude-allein-Vergleich, Last im Job, AMD-Worker (`jarvis-pc.json` fehlt, nur Plan), Mobile/Browser-Test, E2 live.
