## Persistent Knowledge

Mein kompletter Obsidian-Vault ist meine dauerhafte Wissensbasis und Teil des Projektwissens:

C:\Users\andre\Documents\Obsidian Vault

Der gesamte Vault darf als Wissensquelle genutzt werden. Informationen aus dem Vault gelten als vorhandenes Wissen, nicht als externe Zufallsquelle.

Suchen und Lesen:

- Bei jeder neuen Aufgabe zuerst prüfen, ob relevantes Wissen im Vault existiert.
- Gezielt nach passenden Dateien, Begriffen, Projekten, Entscheidungen und früheren Notizen suchen.
- Niemals den kompletten Vault pauschal laden.
- Erst suchen, dann nur relevante Dateien bzw. Abschnitte lesen. Aufhören, sobald genug Evidenz vorliegt.
- Bestehende Notizen, Dokumentation, frühere Entscheidungen und historische Informationen aktiv berücksichtigen.
- Widersprechen sich mehrere Notizen, die aktuellste bzw. klarste Quelle priorisieren und den Widerspruch markieren.
- Persönliche Notizen dürfen als Kontext genutzt werden, wenn sie für die aktuelle Aufgabe relevant sind.
- Obsidian-Suche und Memory-Nutzung möglichst token-effizient durchführen.

Speichern:

- Das native Claude Auto-Memory befindet sich über eine Junction physisch unter:
  C:\Users\andre\Documents\Obsidian Vault\_Claude-Memory\Auto-Memory
- Auto-Memory weiterhin normal verwenden.
- Wenn neues dauerhaft nützliches Wissen entsteht, im Auto-Memory oder einer passenden bestehenden Obsidian-Notiz dokumentieren.
- Bei größeren Aufgaben nach Abschluss prüfen, ob neues Wissen, Fixes, Entscheidungen oder Lessons Learned gespeichert werden sollten.
- Bestehende passende Notizen bevorzugt aktualisieren, statt Duplikate anzulegen.
- Fehlgeschlagene Lösungswege speichern, wenn sie künftig Wiederholungen verhindern.
- Wichtige Entscheidungen inklusive Grund speichern.
- Keine belanglosen Zwischenschritte oder riesigen Roh-Logs dauerhaft speichern.
- Niemals Passwörter, API-Keys, Tokens, Cookies, private Schlüssel oder andere Secrets speichern.
- Persönliche bestehende Notizen nur ändern, wenn es für die Aufgabe sinnvoll ist oder ich es ausdrücklich verlange.

## Parität PC ↔ Server

PC und Server sollen gleich gepflegt sein (Entscheidung Philipp, 2026-10-12). Das PC-Repo ist die Hauptkopie, aber nicht zwingend: Änderungen auf dem Server (z. B. durch Claude im Portal) gehen nicht verloren.

- Jede neue Funktion oder Verbesserung wird auf beiden Seiten umgesetzt oder zeitnah nachgezogen. Ist etwas bewusst nur auf einer Seite (Sicherheit, Hardware, Windows), steht der Grund in `docs/paritaet-bestandsaufnahme.md`.
- Nach Änderungen auf dem Server: Eintrag in `CHANGELOG.md`. Den Abgleich in beide Richtungen (Projekt, Skills, Agenten, Regeln, Hooks) macht die geplante Aufgabe `ClaudeAbgleich` am PC (`scripts/server-sync/claude-abgleich.py`); Konflikte werden nie still überschrieben, geholte Änderungen werden committet und nach GitHub gepusht. `server-nach-pc.py` ist nur eine Notlösung für den manuellen Abgleich.
- `scripts/server-sync/paritaet-check.py` meldet Abweichungen; neue Betriebsdateien dort in die Liste `FILES` eintragen.
- Fehlt etwas auf der anderen Seite noch, steht es in `BACKLOG.md` mit Verweis auf die Änderung.