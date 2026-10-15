Im Unterordner `bilder/` liegen mehrere PNG-Bilder unterschiedlicher Größe. Schreibe ein Programm `kontakt.py` (Python 3, Pillow ist installiert), aufrufbar als

    python3 kontakt.py bilder --out kontaktbogen.png --thumbs thumbs

1. Je Bild entsteht `thumbs/<name>.png` mit genau 200 Pixeln Breite; die Höhe folgt dem Seitenverhältnis (gerundet auf ganze Pixel, mindestens 1). Es wird nie hochskaliert-verzerrt: Breite 200, Höhe `round(h * 200 / w)`.
2. Der Kontaktbogen `kontaktbogen.png` zeigt alle Vorschaubilder in einem Raster mit 3 Spalten, Reihenfolge nach Dateiname aufsteigend, zeilenweise. Jede Zelle ist 200 x 200 Pixel, zwischen und um die Zellen liegt ein Rand von 10 Pixeln (Breite also `3*200 + 4*10 = 640`, Höhe `Zeilen*200 + (Zeilen+1)*10`). Der Hintergrund ist weiß (255, 255, 255). Das Vorschaubild steht links oben in seiner Zelle.
3. Kein Bild ist höher als breit, die Vorschau passt also immer in die Zelle.
4. Nicht-PNG-Dateien im Ordner werden ignoriert. Gibt es keine PNG-Bilder, endet das Programm mit Exit-Code 4 und legt nichts an.

Liefere außerdem `test_kontakt.py` (unittest) und `README.md` mit Aufrufbeispiel. Wende das Programm auf `bilder/` an, sodass `kontaktbogen.png` und `thumbs/` im Ergebnis liegen.
