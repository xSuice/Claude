# Claude Code: lokales Attention Gate – Minimalprototyp

**Zweck:** Einen kleinen, verifizierbaren Teil einer kognitiven Architektur als normales Python-Programm realisieren. Es wählt aus *bereits berechtigt abgerufenen* Fakten eine kompakte Teilmenge für Claude. Es ruft **kein Sprachmodell** auf und verwendet nur Python-Standardbibliothek.

## Testen (Windows PowerShell / Linux)

```powershell
python -m unittest -v test_brain_gate.py
python brain_gate.py --input example_input.json --user person-a --project ma-home --max-chars 3000
```

Der Aufruf erzeugt eine kurze JSON-Antwort, ohne einen Claude-Aufruf auszulösen. **Wenn Claude die Antwort anschließend liest, kosten diese übertragenen Zeichen wieder Kontext-Tokens.** Die Entscheidung, ob eine Aufgabe Claude benötigt, liegt außerhalb dieses Prototyps.

## Integration in die bestehende Architektur

1. Bestandsaufnahme: reale Datenbank und Abrufweg ermitteln. Keinesfalls parallel einen zweiten führenden Speicher anlegen.
2. Bestehende Suchfunktion liefert `query` und `candidates` im JSON-Schema wie in `example_input.json`; der Datenbankadapter setzt **serverseitig** authentifizierte Nutzerkennung, Projekteinschränkungen, ACL und widerrufene Inhalte durch.
3. `brain_gate.py` als **zusätzlichen** lokalen Filter auf die bereits berechtigten Treffer anwenden. Nicht automatisch ungeprüfte Gedächtnisinhalte auf jedem `UserPromptSubmit` in den Modellkontext injizieren. Besser: auf Bedarf via CLI oder MCP.
4. Nur `items` samt Quellen/Version an Claude übergeben, wenn für die jeweilige Aufgabe erforderlich. Bei `warning` Primärquelle suchen, statt etwas zu erfinden.
5. Bestehende Hooks beibehalten und reparieren. Neue Hooks nur auf bestimmte Ereignisse beschränken; `stdout` möglichst leer, wenn Claude kein Ergebnis braucht.
6. Nach zwei Nutzerkontexten, Widerruf und unabhängigen Qualitätstests evaluieren, bevor produktiv freigegeben wird.

## Wichtige Grenzen

- **Proof of Concept, nicht produktionsreif.** Keine DB-Verbindung, Authentifizierung, produktive RLS-Prüfung, Graphsuche, semantische Embeddings, Cache-Invalidierung oder Claude-Code-Hook-Konfiguration enthalten.
- `--user` allein ist keine Authentifizierung. Ein Angreifer könnte einen anderen Wert übergeben. Technischer Schutz muss im vorhandenen Backend (z. B. PostgreSQL-RLS) sowie in der Tool-Zugriffsschicht erfolgen.
- Die Wortüberschneidung ist nur ein einfacher Relevanzfilter. Sie kann wichtige semantische Treffer übersehen. Die vollständigen Quellen müssen abrufbar bleiben; messen, bevor ein semantischer Index hinzugefügt wird.
- Für dynamische Fakten ist eine als „confirmed“ markierte Zeile **nicht automatisch aktuell**. Die Quellversion und live verfügbare Statusabfragen sind maßgeblich.
- Falls die Anwendung dieselben Treffer mehrfach in den Modellkontext gibt, wird nichts eingespart. Sparpotenzial entsteht erst durch kürzere, ausreichend relevante Eingaben und weniger Modellaufrufe.

## Nächste Funktion (nach erfolgreichem Test)

Bestehenden DB-Adapter anbinden; Fehlversuche lokal protokollieren; Quellenversionen für Cache-Invalidierung speichern; einen kleinen Messdatensatz (Coding, Recherche, Dokumente, Kreativität, zwei Nutzer) vor und nach dem Filter mit unveränderten Erfolgskriterien vergleichen. Nur nach nachgewiesener Qualität und geringerer Gesamtbelastung freigeben.
