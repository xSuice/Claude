Im Arbeitsordner liegt `ton.wav` (Mono, PCM). Schreibe ein Programm `wav2mp3.py` (Python 3; `ffmpeg` und `ffprobe` sind installiert), aufrufbar als

    python3 wav2mp3.py ton.wav --out ton.mp3

Das Programm wandelt die Datei in eine MP3 mit 128 kbit/s um, ermittelt die Dauer der **entstandenen MP3** in Sekunden (mit `ffprobe`) und gibt als letzte Zeile der Standardausgabe genau `Dauer: S.S` aus (eine Nachkommastelle, Dezimalpunkt, z. B. `Dauer: 3.2`). Bei fehlender Eingabedatei endet das Programm mit Exit-Code 2 und gibt nichts nach `--out` aus.

Liefere außerdem `test_wav2mp3.py` (unittest) und `README.md` mit Aufrufbeispiel. Wende das Programm auf `ton.wav` an, sodass `ton.mp3` im Ergebnis liegt.
