# MA Home – Diagnose und Reparatur

Stand: 2026-10-05. Diagnoseleitfaden; keine abgeschlossenen Serverreparaturen behauptet. Konkrete Befehle erst nach Bestätigung des Systems, Dienstes und Fehlers erstellen.

## Vor jedem Eingriff

1. Ursprünglichen Fehler, Zeitpunkt und Zugriffsweg festhalten.
2. Relevante Belege lesen; wenige lesende Prüfungen wählen, die Ursachen unterscheiden.
3. Betroffene Datei/Dienst, Sicherung und konkreten Rückweg bestimmen.
4. Autorisierte kleine Änderung durchführen; nur notwendige Dienste neu laden.
5. Ursprünglichen Fehlerfall und betroffene Sicherheitsgrenze prüfen.
6. Status, Historie und Übergabe aktualisieren; bestätigte Ursachen in LESSONS-LEARNED.md übernehmen.

## Diagnosepfade

| Fehler | Gezielte Prüfreihenfolge | Erfolgskriterium |
|---|---|---|
| Startseite liefert 404 | Tatsächlichen Respondenten/Route feststellen; Webdienst und Startdatei prüfen; gesamten Pfad unter Dienstrechten prüfen; statische Dateien und Proxy prüfen | Startseite und benötigte Assets im ursprünglichen Browserzugang geladen; Zugriffsschutz korrekt |
| Mobilfunk funktioniert, WLAN nicht | Client-DNS und ggf. IPv6; TCP; TLS; Proxy; Browser-DNS; erst danach Routerpfad | Gleiche Domain funktioniert im betroffenen LAN und weiter über Mobilfunk |
| Container läuft, App nicht | Status/Health, begrenzte bereinigte Logs, Entrypoint, Bind-Mount-Rechte, tatsächlicher App-Endpunkt | Benutzeraktion funktioniert; laufender Container allein genügt nicht |
| Anmeldung fehlerhaft | Redirects, Cookie-Origin, Uhrzeit, tatsächliche Auth-Route und Rollen | Autorisierter Zugriff erfolgreich; unberechtigter Zugriff blockiert |
| Server langsam | Vergleichbare RAM/CPU/I/O-Messung; betroffenen Prozess und HDD-Last eingrenzen | Messbare Verbesserung derselben Last ohne Funktionsverlust |
| Drucker/Scanner erkannt | Angebotene Protokolle und Integration prüfen; Funktionstest nur mit Auftrag | Angeforderte Testseite oder Scan tatsächlich erfolgreich |
| Backup unklar | Ziel, letzte Sicherung, Umfang und isolierten Restore prüfen | Daten wiederherstellbar, produktive Daten nicht überschrieben |

## Rückwegvorlage

- Was wird geändert, welche frühere Fassung ist gesichert?
- Wo liegt die Sicherung, welche Eigentümer/Rechte gelten?
- Welcher konkrete Wiederherstellungsbefehl passt zu dieser Änderung?
- Ist Reload/Restart nötig, und wie bleibt SSH erreichbar?
- Wie wird der ursprüngliche Zustand geprüft?

Keine universellen Rollback-Befehle: Rechteänderungen, Firewallregeln und Datenbankmigrationen benötigen unterschiedliche Rückwege. Zugangsdaten nicht in Beispielen speichern.
