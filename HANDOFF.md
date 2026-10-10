# MA Home – aktuelle Übergabe

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
