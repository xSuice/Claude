Im Arbeitsordner liegt `messdaten.csv` (Trennzeichen `;`, Dezimalpunkt, Kopfzeile `zeit;temperatur;feuchte`, Werte als Zahlen, einzelne Zeilen können in einer Spalte leer sein).

Schreibe ein Programm `auswertung.py` (Python 3, `python-docx` ist installiert), aufrufbar als

    python3 auswertung.py messdaten.csv --json statistik.json --docx bericht.docx

1. `statistik.json`: `{"temperatur": {"anzahl": n, "min": ..., "max": ..., "mittel": ...}, "feuchte": {...}}`. Leere Zellen zählen nicht mit. `min`, `max` und `mittel` auf 2 Nachkommastellen gerundet (Zahlen). Mittelwert = Summe geteilt durch Anzahl.
2. `bericht.docx`: eine Überschrift der Ebene 1 `Messbericht`, danach ein Absatz je Spalte der Form `Temperatur: Anzahl 96, Minimum 18,25, Maximum 24,10, Mittelwert 21,05` (Spalte mit großem Anfangsbuchstaben `Temperatur` bzw. `Feuchte`; Zahlen mit Dezimalkomma und 2 Nachkommastellen, Anzahl ohne). Die Zahlen im Bericht müssen genau denen in `statistik.json` entsprechen.

Liefere außerdem `test_auswertung.py` (unittest) und `README.md` mit Aufrufbeispiel. Wende das Programm auf `messdaten.csv` an, sodass `statistik.json` und `bericht.docx` im Ergebnis liegen.
