Im Arbeitsordner liegt `zaehler.csv`: stündliche Zählerstände eines Stromzählers als deutsche CSV-Datei (Trennzeichen `;`, Dezimalkomma). Die Spalte `zeit` ist ISO 8601 mit UTC-Versatz (z. B. `2026-03-29T03:00+02:00`), die Spalte `stand_kwh` der Zählerstand. Die Datei ist unordentlich: Zeilen können doppelt vorkommen, nicht zeitlich sortiert sein, Stunden fehlen, und einzelne Zählerstände sind unplausibel.

Schreibe ein Python-Kommandozeilenprogramm `verbrauch.py` (nur Standardbibliothek), aufrufbar als

    python3 verbrauch.py EINGABE.csv --out tage.csv --anomalien anomalien.txt

Regeln:
1. Exakt doppelte Zeilen zählen einmal. Die Reihenfolge ergibt sich aus der Zeit, nicht aus der Datei.
2. Ein Zählerstand ist unplausibel, wenn er kleiner ist als der letzte plausible Zählerstand davor. Unplausible Zeilen werden ignoriert und mit ihrem `zeit`-Wert (genau wie in der Eingabe) je Zeile in `anomalien.txt` geschrieben, zeitlich sortiert.
3. Kalendertage gelten in der Zeitzone Europe/Berlin (Sommerzeitwechsel beachten).
4. Tagesverbrauch = letzter plausibler Zählerstand des Tages minus letzter plausibler Zählerstand des vorherigen in der Datei vorkommenden Tages. Für den ersten Tag: letzter minus erster plausibler Zählerstand dieses Tages.
5. `tage.csv`: Kopfzeile `datum;kwh`, danach je Tag `JJJJ-MM-TT;Wert` mit genau 3 Nachkommastellen und Dezimalpunkt, nach Datum sortiert.

Liefere außerdem `test_verbrauch.py` (unittest, deckt Duplikate, Sommerzeit und unplausible Werte ab) und eine kurze `README.md` mit Aufrufbeispiel. Wende das Programm auch auf `zaehler.csv` an, sodass `tage.csv` und `anomalien.txt` im Ergebnis liegen.
