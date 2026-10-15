Im Arbeitsordner liegt `verkauf.csv` (Trennzeichen `;`, Dezimalkomma, Kopfzeile `artikel;menge;preis`). `menge` ist eine ganze Zahl, `preis` der Einzelpreis in Euro.

Schreibe ein Programm `bericht.py` (Python 3, `python-docx` ist installiert; alternativ pandoc), aufrufbar als

    python3 bericht.py verkauf.csv --out umsatz.docx

Das Word-Dokument enthält:
1. Eine Überschrift der Ebene 1 (Stil Überschrift 1) mit dem Text `Umsatzbericht`.
2. Eine Tabelle mit der Kopfzeile `Artikel | Menge | Einzelpreis (EUR) | Summe (EUR)` und je CSV-Zeile einer Zeile (Reihenfolge wie in der Datei). Einzelpreis und Summe mit genau 2 Nachkommastellen und Dezimalkomma; Summe = Menge mal Einzelpreis. Tausenderpunkte gibt es nicht.
3. Als letzte Tabellenzeile `Gesamt | <Summe der Mengen> | | <Gesamtsumme>` (Einzelpreis-Zelle leer).

Liefere außerdem `test_bericht.py` (unittest) und `README.md` mit Aufrufbeispiel. Wende das Programm auf `verkauf.csv` an, sodass `umsatz.docx` im Ergebnis liegt.
