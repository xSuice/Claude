# Lokale Prüfung der Server Edition

Ausgeführt am 14.10.2026 in einer isolierten Linux-Arbeitsumgebung.

- Bestehende V5-Runtime-Tests: **33/33 bestanden**.
- Neue Server-Edition-Tests: **4/4 bestanden**.
- Separater Dry-Run des serverseitigen Installers: erfolgreich, ohne Änderungen.
- Separater Dry-Run des systemd-Unit-Generators nach Testinstallation: erfolgreich.
- Tatsächlicher MCP-Subprozess-Test über `initialize`, `tools/list` und `tools/call`: erfolgreich.
- Offline-Nutzerisolationsprobe mit Testidentitäten: bestätigt, dass private Erinnerung des Nutzers A nicht beim Nutzer B erscheint und explizit freigegebene Erinnerung bei B erscheint.
- SQLite-Backup-Probe: Backup erstellt und mit `integrity_check=ok` geprüft.
- Installationsupdate-Probe: Programmcode-Backup erzeugt; bestätigte Testinformation blieb in der gesonderten Zustandsdatenbank erhalten.

Nicht geprüft:

- Installation auf dem produktiven MA-Home-Server / Windows-SSH-Client / Claude-Pro-Konto.
- End-to-End-SSH-`authorized_keys`-Zwangsbefehl auf echter Hardware.
- Sicherheit zweier Benutzer gegen Prozesskompromittierung (App-Filterung ist keine vollständige Isolation).
- Anbindung an bereits vorhandene externe Datenbank, Docker, ZimaOS, Router und Serverdienste.
- Wirkliche Steigerung von Qualität / Tokenersparnis / Verfügbarkeit.
- Wiederherstellung einer echten Produktionsdatenbank nach Verlust (nur Backup-Integrität getestet).

Achtung: Erfolgreiche Softwaretests belegen nicht die Optimierung des Cloud-Modellkontingents oder biologisch menschenähnliche Intelligenz.
