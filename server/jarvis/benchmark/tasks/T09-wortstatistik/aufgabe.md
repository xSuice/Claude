Im Arbeitsordner liegt `text.txt`. Erstelle mit dem vorhandenen Werkzeug `tool.wortstatistik` (über die Fähigkeiten-Schnittstelle, nicht neu programmiert) die Datei `statistik.json` mit den **5** häufigsten Wörtern.

Schreibe dazu `bericht.py` (nur Standardbibliothek), aufrufbar als

    python3 bericht.py statistik.json --out statistik.md

Es macht aus der JSON-Datei eine Markdown-Datei: Zeile 1 `# Wortstatistik`, Zeile 2 leer, Zeile 3 `Wörter gesamt: N`, Zeile 4 `Verschiedene Wörter: M`, Zeile 5 leer, danach eine Tabelle `| Rang | Wort | Anzahl |` mit Trennzeile `|---|---|---|` und je Eintrag der Häufigkeitsliste (Rang ab 1, in der Reihenfolge der JSON-Datei).

Liefere `statistik.json`, `statistik.md`, `README.md` und `test_bericht.py` (unittest). Die Zahlen in `statistik.json` müssen zum Text passen: Als Wort zählt jede Folge von mindestens 2 Buchstaben, ohne Beachtung der Groß- und Kleinschreibung.
