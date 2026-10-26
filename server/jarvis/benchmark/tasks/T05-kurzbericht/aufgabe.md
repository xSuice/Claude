Im Arbeitsordner liegt `abschnitte.json` mit `titel` (Text) und `abschnitte` (Liste von Objekten mit `ueberschrift` und `text`).

Schreibe ein Programm `kurzbericht.py` (Python 3, `reportlab` ist installiert), aufrufbar als

    python3 kurzbericht.py abschnitte.json --out kurzbericht.pdf

Das PDF hat folgenden Aufbau:
1. Seite 1 ist eine Titelseite mit dem `titel` und sonst nichts außer dem Text `Kurzbericht`.
2. Danach genau eine Seite je Abschnitt, in der Reihenfolge der Datei: oben die Überschrift, darunter der Text. Jeder Abschnitt steht auf einer eigenen Seite, auch wenn er kurz ist. Die Texte sind so kurz, dass jeder Abschnitt auf eine Seite passt.
3. Jede Seite ab Seite 2 trägt unten den Text `Seite N von M` (N = laufende Seite, M = Gesamtzahl der Seiten).
4. Der Text im PDF muss maschinell lesbar sein (kein Bild).

Liefere außerdem `test_kurzbericht.py` (unittest) und `README.md` mit Aufrufbeispiel. Wende das Programm auf `abschnitte.json` an, sodass `kurzbericht.pdf` im Ergebnis liegt.
