# MA Home – offene Aufgaben

Stand: 2026-10-09, Europe/Berlin. Priorisiert nach aktuellen Live-Befunden. Ausführungsdetails stehen im CHANGELOG.md.

| ID | Priorität | Aufgabe | Fertig, wenn | Status |
|---|---|---|---|---|
| B01 | Hoch | Aktuelle Diagnose auswerten | Version, Dienste, Pfade, Fehler mit Datum belegt | **erledigt 2026-10-09** (SERVER-STATUS, Diagnosebericht) |
| B02 | Hoch | Dashboard-404 beheben | Ursache belegt, repariert, Browserzugang und Auth geprüft | Ursache und Reparatur live bestätigt (Vorher/Nachher 404→200); **Browser-Ablauf offen** |
| B03 | Hoch | Backup und Restore | Externes Ziel, Verschlüsselung, Restore-Test belegt | **Blockade:** Ziel fehlt (Andrew entscheidet); Verfahren vorbereitet (BACKUP-RESTORE.md, scripts/ma-backup.sh) |
| B04 | Hoch | Browser-Funktionstest mit Login | Navigation, iframes, Konsole/Netzwerk ohne Fehler, Handy-Ansicht | Desktop-Test **live bestätigt 2026-10-09** (alle 13 Bereiche, 4 iframes); Handy-Ansicht offen |
| B05 | Hoch | Dateien (`/files`) reparieren | `/files` im Dashboard nutzbar | **erledigt, live bestätigt 2026-10-09** (Browser) |
| B06 | Hoch | HA-Einbettung reparieren | HA im Dashboard nutzbar | **erledigt, live bestätigt 2026-10-09** (lädt eingebettet; HA-Login ist eigenes Konto) |
| B07 | Mittel | Dokumentvorschau | PDF/Office/Text-Vorschau im Portal | Text-Vorschau live bestätigt; PDF/Office/PPTX offen (Testdateien nötig) |
| B08 | Mittel | Client-DNS (Blocky) | Einzelner Client nutzt 192.168.0.111, dann Entscheidung zu DHCP | scripts/pc-dns-test.ps1 bereit; braucht Administrator-PowerShell |
| B09 | Mittel | Druck und Scan | Testseite/Testscan in Oberfläche | **Blockade:** Drucker 192.168.0.198 nicht erreichbar, keine CUPS-Queue (`printer_ready=False`); Testmaterial vorher klären |
| B10 | Mittel | Filebrowser-Nachfolge | Ersatz oder Absicherung des archivierten Projekts (keine Sicherheitsupdates mehr) | offen; Image per Digest gepinnt, nur localhost + Authelia 2FA |
| B11 | Niedrig | Updates | 25 Pakete prüfen; Kernel-Reboot nur mit Freigabe | offen |
| B12 | Niedrig | Blocky-Resilienz | Zweiter DoT-Anbieter oder UDP-Fallback | optional; DoT aktuell erreichbar |
| B13 | Niedrig | sudo-Ticket beenden | Nach Projektabschluss `ssh ma-server "tmux kill-session -t ma-root; sudo -k"`, ggf. `/etc/sudoers.d/zz-ma-claude` entfernen | offen bis Projektabschluss |

Neue Aufgabe: ID, Ziel, Priorität, Belege, Abnahmekriterium, Status. Keine Aufgabe ohne Nachweis als erledigt markieren.
