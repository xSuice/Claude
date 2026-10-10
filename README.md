# MA Home – Dokumentation

Stand: 2026-10-05, Europe/Berlin. Dieses Paket ist eine zusammengeführte neue Ausgabe. Es installiert nichts und verändert den Server nicht.

## Einstieg

Alle zehn Markdown-Dateien gemeinsam im MA-Home-Projektstamm ablegen und als aktuelle ChatGPT-Projektquellen verwenden. Alte gleichnamige Quellen durch diese Ausgabe ersetzen, damit keine widersprüchlichen Regeln entstehen. Vor dem Ersetzen lokaler Dokumente vorhandene neuere Einträge zusammenführen. Keine produktiven Konfigurationen überschreiben.

Projektanweisung:

```text
Lies AGENTS.md, TASK-POLICY.md, SERVER-STATUS.md und HANDOFF.md.
Lies die relevanten neuesten Einträge in CHANGELOG.md.
Nutze weitere Projektdateien gezielt nach dem Auftrag.
Bearbeite meinen bestehenden MA-Home-Server nach diesen Regeln.
Dokumentiere Änderungen, tatsächliche Prüfungen und neue Erkenntnisse.
```

## Dateien und Zuständigkeit

| Datei | Zweck | Wann aktualisieren |
|---|---|---|
| AGENTS.md | Dauerhafte Arbeitsregeln und Rollen | Bei Änderung der Regeln |
| SERVER-STATUS.md | Zuletzt belegter Zustand mit Quelle und Datum | Bei neuen belastbaren Befunden |
| CHANGELOG.md | Chronologische Änderungen und Ergebnisse | Nach jeder Änderung, auch fehlgeschlagenen |
| ARCHITECTURE.md | Komponenten, Abhängigkeiten und Datenwege | Bei belegten Strukturänderungen |
| RUNBOOK.md | Gezielte Diagnose und Rückwege | Nach bewährten Reparaturabläufen |
| LESSONS-LEARNED.md | Ursachen, Belege und passende Vermeidungsprüfungen | Nach bestätigten Ursachen |
| BACKLOG.md | Offene Aufgaben und Abnahmekriterien | Bei Aufnahme oder Abschluss einer Aufgabe |
| HANDOFF.md | Aktuelles Ziel, letzter Stand und nächster Schritt | Am Ende einer Arbeitssitzung |
| README.md | Einstieg und Dokumentationskarte | Bei Strukturänderung |
| TASK-POLICY.md | Aufgabenverständnis und sparsamer Aufwand | Bei Änderung der Arbeitsweise |

## Einheitliche Beleglage

Verwende: historisch / Hypothese / lokal geprüft / live bestätigt / offen. Jeder Serverbefund braucht Beobachtungszeit, Quelle und Prüfumfang. Dokumenterstellung bestätigt keinen Serverzustand.

Keine Passwörter, Tokens, privaten Schlüssel, vollständigen geheimen Konfigurationen oder privaten Dokumentinhalte aufnehmen. Technische Adressen in diesem Paket sind private Projektinformationen; nicht öffentlich veröffentlichen.

PC, ChatGPT und Server gleichen diese Dateien nicht automatisch ab. Vor jeder Sitzung die führende Kopie festlegen. Das Paket ist bis zur Übertragung die führende Dokumentausgabe; neuere Live-Befunde müssen zusammengeführt werden.

## Diagnose ausführen

Das ZIP enthält zehn Markdown-Dateien im Ordner MA-Home-10-Dokumente und das separate Skript ma-home-bestandsaufnahme.sh. Das Skript erfasst technische Metadaten; es exportiert keine Konfigurationsinhalte oder Quellcode. Dateinamen und Netzwerkadressen können im Bericht erscheinen. Vor dem Teilen prüfen.

In Windows-CMD, wenn das Skript in Downloads liegt:

```cmd
scp "%USERPROFILE%\Downloads\ma-home-bestandsaufnahme.sh" andrew@192.168.0.111:/tmp/ma-home-bestandsaufnahme.sh
ssh -t andrew@192.168.0.111 "sudo bash /tmp/ma-home-bestandsaufnahme.sh"
```

Die IP ist historisch und muss noch stimmen. Ausgabe von MA-HOME-DIAGNOSE_START bis MA-HOME-DIAGNOSE_ENDE als eigene TXT-Datei hochladen. Fehlende Werkzeuge werden nicht installiert. Syntaxprüfung bestätigt keine Serverausführung.
