Schreibe ein Python-Kommandozeilenprogramm `toc.py` (nur Standardbibliothek), das in einer Markdown-Datei ein Inhaltsverzeichnis erzeugt:

    python3 toc.py dokument.md --out dokument_mit_toc.md

Regeln:
1. Überschriften sind Zeilen der Form `#` bis `####` (1 bis 4 Zeichen), gefolgt von einem Leerzeichen und dem Text. Zeilen innerhalb von Codeblöcken (``` ... ```) sind keine Überschriften.
2. Die Zeile `<!-- toc -->` wird durch das Inhaltsverzeichnis ersetzt. Fehlt sie, wird das Verzeichnis nicht eingefügt, die Datei bleibt unverändert und das Programm endet mit Exit-Code 3.
3. Je Überschrift eine Zeile `- [Text](#anker)`, eingerückt mit 2 Leerzeichen je Ebene unterhalb von Ebene 1 (Ebene 1: keine Einrückung, Ebene 2: 2 Leerzeichen, usw.). Die Reihenfolge ist die der Datei. Die Überschrift, die selbst `Inhalt` heißt, kommt nicht ins Verzeichnis.
4. Anker wie bei GitHub: Text in Kleinbuchstaben, Leerzeichen zu `-`, alle Zeichen außer Buchstaben (inklusive Umlaute), Ziffern, `-` und `_` entfernt. Kommt derselbe Anker mehrfach vor, erhalten die weiteren `-1`, `-2`, ... angehängt.
5. Alles andere bleibt unverändert, auch die Zeilenenden am Dateiende.

Liefere außerdem `test_toc.py` (unittest) und `README.md` mit Aufrufbeispiel. Wende das Programm auf `dokument.md` an, sodass `dokument_mit_toc.md` im Ergebnis liegt.
