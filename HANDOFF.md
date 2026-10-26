# MA Home – aktuelle Übergabe

## 2026-10-18 12:00 Europe/Berlin – Hermes, M1a vor Freeze

- Führend für diese Entwicklung: Worktree `jarvis-m1a-live`, Branch `dev/hermes-m1a-live-20261018`, Basis `server-live` / `70a6fd0242c349bb798c4545ff58e5c4f2843ce3`. Alter main-basierter M1a-Worktree bleibt erhalten.
- SSH ist jetzt tatsächlich verifiziert. Das aktive Release stimmt in allen 104 verglichenen Codedateien mit dieser Basis überein; die main-Basis wich in 8 Dateien ab. Server-Arbeitskopie mit 7 bestehenden Änderungen nicht angefasst.
- Lokale M1a-Schrittvalidierung per RED/GREEN gehärtet. Abschließend 5 Adapter-, 31 Referenz- und 20 isolierte bestehende V16-Tests grün; öffentlicher Minimal-Sandbox-Probe 13/13. Keine vollständige Runtime-/Modellqualifikation daraus ableiten.
- Different-Family-Review, faire tatsächliche D-Baseline, integrierte Laufzeit/Recovery und vollständige M1a-Abnahme bleiben offen. Kein Freeze/M1b/Deployment. Produktivdienste und Daten nicht geändert.
- Details: `docs/jarvis-omega/M1A-LIVE-INTEGRATION.md`; externe Laufbelege im Workspace `Hermes-Engineering-2026-10-17/reports/`, Gesamtbericht `JARVIS-INTEGRATION-2026-10-18.md`.
- Nächster Schritt: faire D-Baseline und D-Recheck-/V16-M1a-Laufzeitkette vervollständigen; unabhängigen anderen Modellfamilien-Review qualifizieren, bevor Gates geschlossen werden. Der frische statische Review des kleinen öffentlichen Adapter-Diffs ist ohne blockierende Befunde abgeschlossen, ersetzt aber keine Different-Family-Abnahme. Zusatzbudget EUR 0; keine erschöpften Kontingente umgehen.

## Historische Übergabe (nicht als aktueller Prüfbeleg verwenden)

Stand: 2026-10-09 (Abend), Europe/Berlin. Historie in CHANGELOG.md, Zustand in SERVER-STATUS.md, Aufgaben in BACKLOG.md.

## Stand (live bestätigt)
- Web-Dateirechte, Filebrowser (`/files`), HA-Proxy-Einstellung und Dokumentvorschau repariert; Portal-API serverseitig vollständig getestet (Details CHANGELOG 2026-10-09).
- Zugriff: `ssh ma-server` (andrew). Root über sudo-Ticket im tmux-Terminal `ma-root` (von Andrew mit Passwort freigeschaltet, läuft nach 8 h oder Reboot ab); Claude nutzt `~/rr "sudo …"` auf dem Server. Beenden: `ssh ma-server "tmux kill-session -t ma-root; sudo -k"`.
- Sicherungen aller Änderungen: `/root/ma-backups/` auf dem Server (Rückwege im CHANGELOG je Eintrag).
- Führende Doku: dieser Ordner. Werkzeugskripte: `scripts/`.

## Offen / Blockaden
1. **Browser-Funktionstest** (B04): braucht angemeldete Sitzung. Andrew meldet sich im Browser-Bereich der App an (Tab `ma-server.duckdns.org`, Authelia + 2FA); danach prüft Claude Navigation, iframes, Konsole, Netzwerk, Handy-Ansicht. Claude gibt keine Passwörter ein. Kein Computer-Use/Chrome in der Sitzung verfügbar.
2. **PC-DNS-Test** (B08): Administrator-PowerShell nötig: `powershell -ExecutionPolicy Bypass -File C:\Users\andre\Documents\MA-Server\scripts\pc-dns-test.ps1` (Rückweg `-Restore`; Sicherung `server-snapshot/pc-dns-backup.json`: DNS am PC manuell 192.168.0.104 (tot) + 192.168.0.1).
3. **Backup** (B03): externes Ziel fehlt – Entscheidung Andrew (USB-Platte, NAS, anderer Rechner). Verfahren: BACKUP-RESTORE.md, scripts/ma-backup.sh. Bis dahin kein ausfallsicheres Backup.
4. **Drucker/Scanner** (B09): 192.168.0.198 nicht erreichbar, keine CUPS-Queue. Gerät prüfen/einschalten; Testmaterial vorher klären.
5. Updates (B11): nicht-Docker-Pakete werden eingespielt (siehe CHANGELOG); Docker/containerd (Container-Neustart) und Kernel-Reboot separat planen.
6. Filebrowser-Image ist archiviert (B10) – Nachfolge/Absicherung bewerten.

## Nächste Schritte Claude (ohne Rückfrage)
Update-Ergebnis prüfen und dokumentieren; nach Browser-Login Funktionstest und Fixes; Backup-Skript nach Zielwahl in Betrieb nehmen und Restore testen.
