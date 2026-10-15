Im Arbeitsordner liegt `bestellungen.json`: eine Liste von Bestellungen mit `id`, `kunde`, `status` (`offen`, `bezahlt` oder `storniert`) und `positionen` (Liste von Objekten mit `menge` und `preis`).

Schreibe ein jq-Programm `auswertung.jq` (jq ist installiert), aufrufbar als

    jq -f auswertung.jq bestellungen.json

Ausgabe: ein JSON-Array mit je einem Objekt `{"kunde": ..., "bestellungen": ..., "umsatz": ...}` für jeden Kunden mit mindestens einer **bezahlten** Bestellung.
1. Nur Bestellungen mit Status `bezahlt` zählen. `bestellungen` ist ihre Anzahl, `umsatz` die Summe über alle Positionen (`menge` mal `preis`), auf 2 Nachkommastellen gerundet (Zahl, kein Text).
2. Sortierung: `umsatz` absteigend, bei Gleichstand `kunde` aufsteigend.
3. Die Schlüssel stehen in der Reihenfolge `kunde`, `bestellungen`, `umsatz`.

Liefere außerdem `pruefen.sh`, das `auswertung.jq` auf `bestellungen.json` anwendet und die Ausgabe in `ergebnis.json` schreibt, sowie `README.md` mit Aufrufbeispiel. `ergebnis.json` soll im Ergebnis liegen.
