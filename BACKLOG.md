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
| B14 | Hoch | Portal-Änderungen vom 2026-10-12 einspielen und am Handy testen | `sudo bash ~/MA-Server/server/auto-deploy/install.sh` und `alles-einspielen.sh` gelaufen, Claude-Tab, Anhänge, Stopp, Terminal am Handy geprüft | offen (CHANGELOG 2026-10-12; app.js nie im Browser ausgeführt) |
| B15 | Hoch | App neu bauen (Druckbrücke `MaApp.print`) | `app/android/build.ps1` am PC, APK installiert, Druckansicht in der App geprüft | offen (Java nicht kompiliert) |
| B16 | Mittel | Abgleich der Konfiguration um Verbindungen (MCP) erweitern | `claude-abgleich.py` gleicht auch die MCP-Definitionen ohne Geheimnisse ab; Zugangsdaten (z. B. GMX) einmalig direkt auf dem Server eingerichtet, nie über Git | offen (Entscheidung Philipp 2026-10-12: auch Verbindungen gleich) |
| B17 | Mittel | Browser-Test der Oberfläche in Handy-Größe | Playwright-Lauf gegen das Portal ohne Konsolenfehler | **erledigt 2026-10-12** (Server-Kopie, Platzhalter-API): `tests/portal_smoke.py`, 21 von 21 bestanden. Start: `LD_LIBRARY_PATH=~/.ma-browsertest/libs/usr/lib/x86_64-linux-gnu ~/.ma-browsertest/bin/python tests/portal_smoke.py`. Offen: Test gegen das echte Backend und am echten Handy. |
| B18 | Mittel | Terminal-Befehle protokollieren | jeder Befehl mit Zeit und Benutzer in einem Log | offen |
| B19 | Niedrig | HEIC-Fotos auf dem Server in JPEG wandeln | iPhone-Foto im Chat lesbar | offen, nur falls HEIC genutzt wird |
| B20 | Niedrig | Konnektoren im Server-Chat (Mail, Kalender …) | Entscheidung Philipp, welche; mit `ma-guard` abgesichert | offen |
| B21 | Hoch | Akku des Server-Laptops prüfen | BAT1 meldet 0 % und "Not charging" bei Netzteil an; klären, ob der Akku fehlt/defekt ist (aufgeblähte Akkus sind eine Brandgefahr im Dauerbetrieb); ggf. ausbauen; Stromausfall = harter Neustart, kein Puffer | offen (Fund 2026-10-12, nur per /sys gelesen) |
| B22 | Mittel | Notfall-Seite für das Handy (Dienststatus ohne Portal) | statische Seite über Caddy, zeigt Portal, Brücke, Backup | offen |
| B23 | Mittel | MCP-Verbindungen (GMX u. a.) auf dem Server einrichten | `paritaet-check.py` meldet keine Abweichung bei "Verbindungen (MCP)"; Zugangsdaten einmalig direkt am Server | offen (B16) |
| B24 | Niedrig | Vaultwarden, Radicale, Paperless, CrowdSec, Filebrowser-Ersatz | gemeinsam entwerfen, sobald Musik-Server und Caddy-Eintrag stehen | offen |
| B25 | Hoch | Server ist Hauptkopie des Vaults | **entschieden 2026-10-12 (Philipp)**. Code fertig: Flag `/srv/ma-home/library/.jarvis/server-master` (setzt `alles-installieren.sh`, abschaltbar mit `--ohne-master`); PC-Skripte beachten es: `server-to-vault.py` zieht Löschungen/Umbenennungen nach (nur in `.server-geloescht`), `vault-to-server.py` überschreibt vom Server geänderte Notizen nie (Kopie in 00 Inbox/Review). Logik mit Testdaten geprüft | offen: Sudo-Installation, Probelauf am PC (`--dry`), Beobachten der ersten Läufe |
| B26 | Mittel | `vault-q` am PC einrichten | `scripts` im PATH, Regel "Vault zuerst mit vault-q abfragen" in die globale CLAUDE.md (3 Zeilen aus `server/claude-config/server-abschnitt.md`), Probe: `vault-q stats` | offen (nur auf dem Server getestet) |
| B27 | Niedrig | Neo4j am PC ausprobieren | `vault-q export-neo4j` -> CSV in den import-Ordner, `import.cypher` ausführen | offen (Export geprüft, Import nicht; auf dem Server bewusst nicht: zu wenig Arbeitsspeicher) |
| B28 | Hoch | Root-Teil in einem Schritt vollständig machen | `ma-deploy` (root-eigen) um die festen portal.py-Freischaltungen erweitern oder `alles-installieren.sh` einmal laufen lassen; danach liefert der PC-Deploy alles ohne Sudo | offen (Fund 2026-10-12: PC-Deploy existiert, deckt portal.py nicht ab) |
| B29 | Mittel | Automatisierungen zentral führen | `server/automations.json` pflegen, `automations.py validate` im Test, PC-Aufgaben dort eintragen | Liste und Server-Zeitplan fertig; PC-Aufgaben nur als Prüf-Erwartung erfasst |
| B30 | Mittel | Statusbericht/„Neu“/Posteingang-Aufgabe in Betrieb nehmen | nach Einspielung: Reiter Neu am Handy geprüft, Aufgabe „Posteingang und Kalender“ angelegt und ein Lauf gelesen, `sync_mcp` mit Freigabe am PC einmal laufen lassen (Bericht prüfen); GMX-Windows-Programm braucht Linux-Ersatz | offen (Code fertig und mit Testdaten geprüft, 2026-10-12) |
| B31 | Mittel | Musik in Betrieb nehmen | `sudo bash ~/MA-Server/SUDO-ALLES.sh` gelaufen, Musikdateien in `/srv/ma-home/library/media/musik`, Reiter Musik am Handy: Wiedergabe, Spulen, Sperrbildschirm; optional Navidrome + Caddy-Eintrag fuer Handy-Apps | offen (Code und Tests fertig, 2026-10-12) |

Neue Aufgabe: ID, Ziel, Priorität, Belege, Abnahmekriterium, Status. Keine Aufgabe ohne Nachweis als erledigt markieren.
