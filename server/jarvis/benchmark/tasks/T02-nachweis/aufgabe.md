Im Arbeitsordner liegt `berichtsheft.json`: Einträge eines Ausbildungsnachweises (Berichtsheft). Felder je Eintrag: `nr`, `datum` (ISO), `bereich` (`Betrieb` oder `Berufsschule`), `taetigkeit`, `stunden`. Die Einträge sind nicht sortiert.

Schreibe ein Python-Kommandozeilenprogramm `nachweis.py` (nur Standardbibliothek), aufrufbar als

    python3 nachweis.py berichtsheft.json --out nachweis.md

Regeln:
1. Gruppiere nach ISO-Kalenderwoche, Wochen aufsteigend. Innerhalb einer Woche nach Datum, bei gleichem Datum nach `nr`.
2. Je Woche eine Überschrift `## KW 05/2027` (zweistellige Woche, vierstelliges ISO-Jahr), danach eine Markdown-Tabelle mit der Kopfzeile `| Datum | Bereich | Tätigkeit | Stunden |` und der Trennzeile `|---|---|---|---|`.
3. Je Eintrag eine Zeile `| TT.MM.JJJJ | Bereich | Tätigkeit | 7,5 |`: Datum deutsch, Stunden mit genau einer Nachkommastelle und Dezimalkomma.
4. Unter jeder Tabelle eine Leerzeile und `**Summe: 40,0 Stunden**` (eine Nachkommastelle, Komma).
5. Die Datei beginnt mit `# Ausbildungsnachweis` und einer Leerzeile.

Liefere außerdem `test_nachweis.py` (unittest) und eine kurze `README.md` mit Aufrufbeispiel. Wende das Programm auf `berichtsheft.json` an, sodass `nachweis.md` im Ergebnis liegt.
