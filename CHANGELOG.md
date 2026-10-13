# MA Home – Änderungshistorie

Alle Zeiten: Europe/Berlin. Diese Historie beginnt am 2026-10-05. Sie ist keine vollständige Rekonstruktion früherer Servereingriffe.

## 2026-10-05 – Projektdokumentation eingerichtet

- Auftrag: Änderungen und Erkenntnisse dauerhaft festhalten und bekannte Fehler künftig berücksichtigen.
- Betroffene Dateien: `AGENTS.md`, `CHANGELOG.md`, `SERVER-STATUS.md`.
- Änderung: Dokumentationspflicht, Quellen- und Datumsangaben, Regeln zur Übernahme bestätigter Fehlerursachen und zum Abgleich der Dokumentkopien ergänzt. Historie und Status neu angelegt.
- Prüfung: Bestehende Projektregeln gelesen und erhalten; neue Statusangaben nach Beleglage getrennt. Keine Live-Prüfung des Servers vorgenommen.
- Ergebnis: Dokumentationsstruktur erstellt. Keine Änderung an Serverdiensten, Firewall, Containern oder produktiven Dateien durchgeführt.
- Rückweg: Ergänzung „Verbindliche Projektdokumentation und Fehlerlernen“ bei Bedarf zurücknehmen; die vorherige AGENTS-Version bleibt über die Dateiversionierung verfügbar. Neue Dokumente können archiviert werden; Server-Rollback nicht erforderlich.
- Offen: Aktuelle Diagnoseausgabe erhalten; Dateien in den lokalen MA-Home-Projektordner übertragen; Abgleich mit eventuell vorhandener Serverdokumentation.

## 2026-10-05 – Frühere Schritte aus diesem Chat eingeordnet

- Diagnose: `ma-home-diagnose.sh` bereitgestellt. Bash-Syntax lokal geprüft; Ausführung und Ergebnisse auf Andrews Server nicht bestätigt. Keine Serverreparatur daraus ableiten.
- Codex: Installationsanleitung bereitgestellt. Andrew wählte zuletzt die Installation auf dem Windows-PC. Erfolgreiche Installation, Anmeldung und SSH-Anbindung nicht bestätigt.
- Historische Serverangaben: Aus `AGENTS.md`, Version 2026-10-04, übernommen. Frühere Reparaturen sind damit keine aktuell bestätigten Live-Ergebnisse. Frühere Eingriffe nicht nachträglich als ausgeführt dokumentiert.

## 2026-10-05 – Dokumentationspaket erweitert

- Auftrag: Alle für wirksame MA-Home-Arbeit benötigten Markdown-Unterlagen zusammenstellen.
- Ausführungsort: ChatGPT-Arbeitsbereich; neue zusammengeführte Dokumentausgabe.
- Betroffen: neun Markdown-Dateien im Paket MA-Home-Dokumentation. Bestehende Regeln und Historie übernommen, Status aus vorhandener Dokumentkopie gelesen; sechs zusätzliche Dateien bzw. Leitfäden einschließlich README erstellt.
- Änderung: Architektur, Diagnoseabläufe, belegorientierte Erkenntnisse, Aufgaben und Übergabe getrennt dokumentiert; gezieltes Lesen und eine führende Stelle pro Information geregelt.
- Prüfung: Lokale Vollständigkeits- und Verweisprüfung; keine Live-Server- oder Browserprüfung.
- Ergebnis: Dokumentationspaket bereitgestellt. Keine Änderungen an Server, Firewall, Containern oder produktiven Dateien.
- Rückweg: Vorherige Dokumentausgabe behalten bzw. neue Ausgabe archivieren; kein Server-Rollback nötig.
- Offen: Diagnosebericht und aktueller Code; Übertragung sowie Abgleich der Dokumentkopien.

## 2026-10-05 16:54 Europe/Berlin – TASK-POLICY ergänzt

- Auftrag: Vermeidbaren Tokenaufwand reduzieren, wirksame Bearbeitung erhalten.
- Ausführungsort: ChatGPT-Arbeitsbereich; keine Serveränderung.
- Dateien: TASK-POLICY.md erstellt; AGENTS-Verweis und HANDOFF ergänzt.
- Regeln: Kontext gezielt lesen, Aufträge im Zusammenhang verstehen, passende Prüfungen erhalten, Routing nur bei verfügbarer und autorisierter Funktion.
- Prüfung: Inhalt mit geltenden Projektregeln abgeglichen; kein Modellrouting oder Verbrauchstest durchgeführt.
- Ergebnis: Dokumentationsregeln bereitgestellt; keine gemessene Tokenersparnis behauptet.
- Rückweg: TASK-POLICY archivieren und zugehörigen AGENTS-Verweis entfernen; kein Server-Rollback erforderlich.
- Offen: Dateien auf PC/Server übernehmen; Diagnoseausgabe erhalten.

## 2026-10-05 17:01 Europe/Berlin – Zehn-Dateien-Paket vereinheitlicht

- Auftrag: Alle zehn Dokumente aktualisieren und mit Diagnosecode als Download bereitstellen.
- Ausführungsort: ChatGPT-Arbeitsbereich; keine Serveränderung.
- Änderung: Kanonische Dateinamen, README auf zehn Dateien einschließlich TASK-POLICY gebracht; Übergabe konsolidiert; Eintragsvorlage ans Ende verschoben. Übrige Fachunterlagen erhalten.
- Prüfung: Zehn Markdown-Dateien und interne Dateiverweise geprüft; Bash-Syntax des erweiterten Diagnoseskripts geprüft. Keine Live- oder Browserprüfung.
- Ergebnis: Downloadpaket mit zehn Markdown-Dateien und separatem Diagnoseskript erstellt.
- Rückweg: Vorherige Dokumentversionen verwenden; kein Server-Rollback nötig.
- Offen: Diagnose ausführen; aktuellen Code erhalten; Dokumente auf PC/Server abgleichen.

## Vorlage für den nächsten Eintrag

### YYYY-MM-DD HH:MM Europe/Berlin – konkrete Änderung

- Auftrag/Ziel:
- Ausführungsort und Bearbeiter:
- Betroffene Dateien/Dienste:
- Änderung und tatsächlich ausgeführte Schritte:
- Sicherung/Rückweg (ohne Geheimnisse):
- Prüfung: Syntax / Simulation / Server / Browser, jeweils mit Ergebnis und Quelle:
- Ergebnis: durchgeführt / fehlgeschlagen / zurückgenommen / nur bereitgestellt:
- Erkenntnis und Vermeidungsregel, sofern Ursache belegt:
- Offene Punkte:


### 2026-10-09 Europe/Berlin – Claude Code übernimmt: Bestandsaufnahme, Reparaturskript vorbereitet

- Auftrag: Server prüfen, JSON-404 und Verbindungsabbruch eingrenzen, Web-Dateirechte gezielt reparieren.
- Ausführungsort: Windows-PC → `ssh ma-server` (andrew, ohne root).
- Betroffen: nur lesende Prüfungen auf dem Server. Neu lokal: `scripts/ma-fix-web-perms.sh`. Kopie nach `/home/andrew/ma-fix-web-perms.sh` (nur Ablage, nicht ausgeführt). Projektdoku aus Vault-Archiv (`MA-Server-Uebergabe/projektunterlagen`) als führende Kopie nach `C:\Users\andre\Documents\MA-Server` übernommen.
- Entscheidung: Kein NOPASSWD. Vorgeschlagene 8-h-Freigabe verworfen, weil das transiente systemd-Timer-Unit einen Reboot nicht überlebt und die sudoers-Datei dann dauerhaft bliebe. Root-Arbeit nur per Skript, das Andrew mit eigenem Passwort startet.
- Prüfung: Bash-Syntax lokal und auf dem Server OK. Skript noch **nicht ausgeführt**, also Reparatur **nicht** erfolgt.
- Rückweg des Skripts: sichert Eigentümer/Modi/ACL nach `/root/ma-backups/web-perms-<UTC>/`, dort `rollback.sh`.
- Serveränderungen: keine.
- Offen: Skript ausführen; Dashboard nach Login im Browser prüfen; Client-DNS-Test an einem Gerät; Backup-Ziel; Drucker.

### 2026-10-09 Europe/Berlin – Reparaturskript gehärtet, DNS-Test und Backup vorbereitet

- Auftrag: Skript-Review (Sicherung vor Änderung, keine fremden Dateien/Symlinks, Abbruch+Wiederherstellung, proxy_key-Schutz, Statuscodes); DNS-Test am PC vorbereiten; Backup/Restore vorbereiten ohne Ziel.
- `scripts/ma-fix-web-perms.sh` überarbeitet: Abbruch vor jeder Änderung bei Unterordnern/Symlinks/Spezialdateien/Hardlinks/ungewöhnlichen Namen; Sicherung (owners.bin NUL-getrennt, getfacl, sha256) wird auf Vollständigkeit geprüft, bevor geändert wird; ERR-Trap mit automatischem Rollback während der Änderungsphase; rollback.sh stellt Eigentümer, Modus und ACLs wieder her und verifiziert; proxy_key gelangt nur per stdin an curl (`-K -`), nie in argv/Ausgabe; erwartete Codes aus portal.py abgeleitet (`/`,`/assets/*`,`/api/me` mit Key 200; `/` ohne Key 401; `/healthz` 200).
- Prüfung (Server, als andrew, Testordner unter /tmp, MA_TEST=1): Normallauf + Rollback OK inkl. ACL; Symlink → Abbruch Exit 2 ohne Änderung; Hardlink → Abbruch ohne Änderung; erzwungener Fehler nach chmod → Auto-Rollback OK, Zustand identisch. Produktivpfad nicht berührt.
- `server-snapshot/pc-dns-backup.json`: PC-DNS gesichert. **Korrektur** zur früheren Annahme: DNS am Adapter "Ethernet" ist **manuell** gesetzt (192.168.0.104, 192.168.0.1); DHCP liefert nur 192.168.0.1.
- `scripts/pc-dns-test.ps1`: prüft Blocky vorab, setzt DNS 192.168.0.111, testet Systemresolver + HTTPS mit Zertifikatsprüfung, stellt bei Fehler automatisch den manuellen Ursprungszustand her (`-Restore` manuell). Syntax OK; ohne Admin verweigert (geprüft). **Nicht ausgeführt** – PC-Benutzer hat keine Admin-Rechte in dieser Sitzung.
- `scripts/ma-backup.sh` + `BACKUP-RESTORE.md`: restic-Verfahren ohne eingebautes Ziel; lehnt Ziel auf derselben Platte ab. Syntax lokal/Server OK, **nicht ausgeführt**.
- Serveränderungen: keine (nur Ablage von Skripten in /home/andrew).

### 2026-10-09 Europe/Berlin – ma-fix-web-perms.sh: ACL-Korrektur (vor Ausführung)

- Anlass: Review-Punkte. (1) Platzhalter im Heredoc war nur eine Auslassung in meiner Chat-Anzeige, nicht in der Datei; Datei vollständig gezeigt, lokal und Server byte-identisch (sha256 d62a970e420936b93c16a979748338587c51c5ffe9105e3941852b691c95dde4). (2) Benannter ACL-Eintrag `user:ma-web` hat Vorrang vor Gruppenrechten und überlebt chown/chmod: Skript listet erweiterte ACLs, setzt nur bei vorhandenem Eintrag `ma-web` auf r-x (Verzeichnis) bzw. r-- (Dateien) mit `setfacl -n` (Mask unverändert) und prüft Durchsuchbarkeit + Lesen als Dienstkonto per `runuser`/`head -c1`. (3) Rollback vergleicht vollständige, sortierte ACL-Ausgabe (inkl. Mask/Default) per diff gegen die Sicherung. (4) Aussage "404 = Ursache bestätigt" entfernt; Vorher-Wert wird nur gemessen, Ursache gilt erst nach Vorher/Nachher-Vergleich und erfolgreichem Browserablauf.
- Tests (Server, als andrew, Testordner, MA_TEST=1): benannter Eintrag `ma-web:---` am Verzeichnis → nach Fix r-x/r--, Rollback stellt `---` samt Mask wieder her, ACL-Diff leer; Fehler nach ACL-Fix → Auto-Rollback OK; sabotierter Rollback (ohne setfacl) → Abweichung erkannt, Exit 1; Symlink → Abbruch Exit 2.
- Grenze: Zugriff "als echter ma-web" konnte ohne root nicht getestet werden (Testmodus läuft als andrew, der Dateieigentümer ist). Der echte Test per `runuser -u ma-web` erfolgt erst im Produktivlauf. Serveränderung: keine.

### 2026-10-09 Europe/Berlin – Web-Dateirechte repariert (live bestätigt)

- Ausführung: Andrew, `sudo bash ~/ma-fix-web-perms.sh` (sha256 d62a970e…dde4) im interaktiven SSH-Terminal. Claude hatte keinen root-Zugriff.
- Ergebnis laut Ausgabe von Andrew: ma-web liest Verzeichnis + index.html/app.js/style.css; Portal `/` mit Schlüssel 404 → 200; `/assets/*` und `/api/me` 200; `/` ohne Schlüssel 401.
- Gegenprüfung durch Claude (nur lesend, danach): `/opt/ma-home/web` = root:ma-web 750; ma-home-web active; lokal `/healthz` 200, `/` ohne Schlüssel 401; Domain (erzwungen auf LAN-IP) ohne Login 302 → Authelia.
- Ursache: Vorher/Nachher-Vergleich (404 → 200 nach gezielter Rechteänderung) stützt `root:root 700` als Ursache des JSON-404 im Portal. Browserablauf mit Anmeldung steht noch aus.
- Rückweg: `sudo bash /root/ma-backups/web-perms-20261009T031712Z/rollback.sh`.
- Offen: Domainzugriff vom Client (DNS), Browser-Anmeldung, Dashboard nach Login.

### 2026-10-09 Europe/Berlin – Webcode-Analyse, Zugriffs-Einrichtung und Root-Diagnose vorbereitet

- Werkzeuglage: SSH als andrew ohne root (live), Browser-Pane ohne Anmeldung, kein Computer-Use, Claude in Chrome nicht verbunden.
- Installer-Kopie der Web-Dateien (Base64 in ma-home-ubuntu-installer.sh) nach `server-snapshot/web-from-installer/` dekodiert (nur Daten). Übereinstimmung mit Serverstand **offen** (Hashvergleich per Diagnoseskript).
- Vorläufig (nur Code, kein Laufzeittest): app.js bettet per iframe `/files/`, `/terminal/`, Home Assistant und ntfy (URLs aus `me.modules`) ein. Funktion hängt an Caddy-Routen/Frame-Headern und Authelia-Cookies; Caddyfile root-only.
- Vorbereitet, nicht ausgeführt: `scripts/ma-claude-access.sh` (kein NOPASSWD; benutzerweites sudo-Ticket 8 h, reboot-fest selbstablaufend, Entfernen: `sudo rm /etc/sudoers.d/zz-ma-claude`) und `scripts/ma-diag-root.sh` (rein lesend, bereinigter Bericht).
- Hinweis: Ein Passwort-ähnlicher String wurde im Chat genannt; nicht verwendet, nicht gespeichert.

### 2026-10-09 Europe/Berlin – sudo-Konfiguration und Root-Diagnose ausgeführt (durch Andrew)

- Versuch 1 des Einrichtungsskripts scheiterte an `tty_tickets` (sudo-rs kennt die Option); visudo lehnte ab, **nichts geändert**. Lehre: Ubuntu 26.04 nutzt sudo-rs; keine sudo-Optionen aus Handbuch von sudo 1.9 blind übernehmen, vorher `visudo -cf` prüfen.
- Versuch 2: `/etc/sudoers.d/zz-ma-claude` mit `Defaults:andrew timestamp_timeout=480` gesetzt (syntaxgeprüft, Gesamtkonfiguration gültig). Danach lief die lesende Diagnose. Rückweg: `sudo rm /etc/sudoers.d/zz-ma-claude`.
- tmux-Freischaltung (`ma-root`) scheiterte beim Passwort (sudo-Log 16:18:43); Sitzung beendet. Offen: erneuter Versuch.
- Befunde siehe SERVER-STATUS.md "Diagnosebericht".

### 2026-10-09 Europe/Berlin – Reparaturen: Filebrowser, Home Assistant, Dokumentvorschau (live bestätigt)

Ausführung: Claude per SSH (andrew) + sudo-Ticket in tmux-Terminal `ma-root` (von Andrew freigeschaltet). Sicherungen unter `/root/ma-backups/` (root, 700).

| Funktion | Ursache (belegt) | Änderung | Test (live) | Rückweg |
|---|---|---|---|---|
| Dateien (`/files/`, Filebrowser) | Image `:latest` (v2.63.23) liest Server-Einstellungen aus `/config/settings.json`; die enthielt Image-Standard (`port 80`, `baseURL ""`). Compose mappt 18081→8080 und Caddy erwartet `/files`. Ergebnis: Connection reset, Caddy 502 | `settings.json`: `port 8080`, `baseURL /files`; Container neu gestartet | Container healthy; `GET /files/` 200; Proxy-Login (`Remote-User: andrew`) liefert Token; `resources` mit Token 200 (Scope /andrew), ohne Token 401 | `cp -p /root/ma-backups/filebrowser-settings-20261009T162831Z.json /srv/ma-home/filebrowser/settings.json` + `docker restart ma-home-filebrowser-1` |
| Dateien – Härtung | Proxy-Login legt unbekannte Benutzer automatisch mit Scope `/` und Schreibrechten an (Testkonto `nobody` entstand durch meinen Test, entfernt) | Standardwerte für neue Benutzer: Scope `/.noaccess` (leerer Ordner), alle Rechte aus; Testkonten `nobody`, `zz-test` gelöscht; `andrew` unverändert | Unbekannter Benutzer: leere Liste, Schreiben 403 | DB-Sicherung `filebrowser-db-20261009T163028Z.db` (Container stoppen, Datei zurückkopieren, starten) |
| Home Assistant (Proxy) | HA 2026.9.4 verwaltet HTTP-Einstellungen in `.storage/http` (stable/pending); Proxy-Einstellung stand als `pending` (`not_promoted`), wurde am 03.10. mangels Bestätigung (5 min, UI über Proxy unerreichbar) verworfen → 400 bei Proxy-Anfragen | `pending` als `stable` übernommen (server_host 127.0.0.1, use_x_forwarded_for, trusted_proxies 127.0.0.1/32), HA gestoppt/gestartet | GET mit `X-Forwarded-For` 400 → 200; Listener nur `127.0.0.1:8123`; Einstellung nach Neustart erhalten | `cp -p /root/ma-backups/ha-storage-http-20261009T163254Z /srv/ma-home/ha/.storage/http` bei gestopptem HA |
| Dokumentvorschau (Konverter) | `agent.py` Zeile 202: `mkdir(mode=0o755)` wird durch `UMask=0077` zu 0700; Container-Benutzer (uid 999) konnte `/input` nicht lesen → `StopIteration` | eine Zeile ergänzt: `os.chmod(job/'input', 0o755)`; `ma-home-agent` neu gestartet (web hängt per Requires dran) | Vorschau-Job (eigene .txt-Datei, danach gelöscht): `done`, 1 Seite, JPEG 200 | `cp -p /root/ma-backups/agent.py.20261009T163517Z /opt/ma-home/agent.py` + `systemctl restart ma-home-agent` |
| systemd | alle ma-home-Units zeigten NeedDaemonReload | `systemctl daemon-reload` (keine Neustarts) | alle Units active, reload=no | – |

Portal-API serverseitig getestet (echter Code, Schlüssel nie ausgegeben): `/api/me`, `/api/status`, Aufgaben/Notizen/Finanzen/Training (POST/PUT/DELETE mit Testdaten, sofort gelöscht), `/api/files`, `/api/export` alle 200/201; CSRF ohne Origin 403; ohne Schlüssel 401; fremder Benutzer 403.

Nicht geändert/entschieden: Blocky (72 Fehler nur in einer Sekunde um 15:06 UTC, DoT jetzt erreichbar); HA-Bluetooth-Capabilities (kein Bedarf); Filebrowser-Image ist laut Meldung archiviert (kein Sicherheitsupdate mehr) → Backlog.
Offen: Browser-Test (Navigation, iframes, Konsole) wartet auf angemeldete Browser-Sitzung; DNS-Client-Test am PC braucht Administrator-PowerShell; Backup-Ziel; Drucker/Scanner nicht erreichbar.

### 2026-10-09 Europe/Berlin – Paketupdates (ohne Docker) eingespielt

- Ausführung: `apt-get install --only-upgrade` für 25 Pakete (u. a. openssh-server/-client, libaudit, netplan, mdadm, ubuntu-server-Metapakete); ausgenommen `docker-*`/`containerd.io` (würden alle Container neu starten, separat planen). Vorher Paketversionen gesichert: `/root/ma-backups/dpkg-versions-<UTC>.txt` (Rückweg: gezielter Downgrade einzelner Pakete aus dieser Liste).
- Prüfung: `dpkg --audit` sauber; neue SSH-Sitzung nach dem openssh-Update erfolgreich; verbleibend upgradable: 5 (Docker-Gruppe). Kernel/Reboot: nicht angefasst.
- Beobachtung: Der `apt-get`-Prozess blieb nach Abschluss angehalten (Zustand T+, vermutlich Tastatureingabe im angehängten tmux-Terminal) und blockiert die Befehlsschlange des Terminals `ma-root`; Fortsetzung per `sudo kill -CONT <pid>` durch Andrew nötig (Stand: ausstehend).
- Lehre: Lange Befehle nicht über das interaktive tmux-Terminal ausführen, in dem Andrew sudo freigeschaltet hat, sondern als `systemd-run`/Hintergrundjob mit Logdatei starten; so blockiert ein hängender Prozess den Zugang nicht.

### 2026-10-09 Europe/Berlin (abends) – Browser-Funktionstest im angemeldeten Chrome (live bestätigt)

Ausführung: Claude über die verbundene Chrome-Erweiterung im Chrome von Andrew (bestehende Authelia-Sitzung); keine Zugangsdaten eingegeben, keine Änderung an Server oder Daten außer Testeinträgen (sofort gelöscht).

| Bereich | Ergebnis |
|---|---|
| Startseite/Navigation | Dashboard lädt ohne Konsolenfehler; angemeldet als andrew · Administrator; Status "Verbunden"; 13 Bereiche in der Navigation |
| Zuhause, Druck & Scan, Aufgaben, Notizen, Haushaltsbuch, Training, System & Docker, Backup & Sync, Einstellungen | rendern ohne Fehlermeldung; System zeigt CPU/RAM/Disk und Docker-Dienste; Backup-Seite meldet korrekt "Kein externer Backup-Datenträger" |
| Dateien (iframe `/files/`) | Filebrowser eingebettet, Ordner `andrew` mit `Scans` sichtbar |
| Smart Home (iframe HA) | HA lädt eingebettet (Frame-Header korrekt), zeigt HA-eigene Anmeldung; alle Ressourcen 200 (ein einzelner 503 auf einer Übersetzungsdatei, beim Nachladen 200; Ursache offen, Caddy-Log nicht prüfbar solange root-Terminal blockiert) |
| Mitteilungen (iframe ntfy) | ntfy lädt eingebettet, Oberfläche sichtbar (ntfy-eigene Anmeldung/Abonnements separat) |
| Terminal (iframe ttyd) | WebSocket verbunden, SSH-Anmeldeprompt `andrew@127.0.0.1` sichtbar (Passwort nicht eingegeben) |
| API über Browserweg (Caddy+Authelia+CSRF-Header) | `me`, `status`, `files` 200; Aufgabe anlegen 201, ändern 200, löschen 200 (Testeintrag entfernt); Filebrowser-Login 200 |

Nicht getestet / offen: Handy-Ansicht (Chrome-Fenster ließ sich nicht verkleinern; CSS enthält Breakpoints 1100/760 px und viewport-Meta, kein Laufzeitnachweis); Anmeldung in HA und ntfy (eigene Konten); Druck (kein Drucker erreichbar, `printer_ready=False`); Scan (Gerät nicht gefunden; Auslösen würde physischen Scan starten); Dokumentvorschau von PDF/Office über die Oberfläche (nur Textdatei serverseitig geprüft).

## 2026-10-12 – Portal mobil, Weiterlaufen im Hintergrund, Terminal, Auto-Einspielung (Server-Kopie, noch nicht live)

- Auftrag: Verbesserungen aus der Handy-Nutzung (Zurück-Geste, Wischen, Druckansicht, PDF, "Neuer Chat" im Verlauf), Token-Anzeige, Terminal-Tab, Versionsnummer, Weiterlaufen bei Verbindungsverlust mit Live-Anzeige, alle Anhänge, automatischer Council, Chat-Funktionen wie in der Claude-App, Abgleich PC <-> Server.
- Betroffene Dateien: `portal-ui/web/{app.js,style.css,sw.js}` (Version 2026-10-12-5), `server/claude-bridge/ma-claude-bridge.py` (Auftraege laufen im Hintergrund weiter, attach, Meldung bei Fertig, Uploads bis 25 MB), `server/claude-bridge/patch-portal-attach.py`, `server/term-bridge/*` (neu), `server/auto-deploy/*` (neu), `server/alles-einspielen.sh` (neu), `app/android/src/.../MainActivity.java` (Druckbruecke MaApp.print), `scripts/server-sync/server-nach-pc.py` (neu), `scripts/server-sync/paritaet-check.py`.
- Pruefung: Bruecke mit Fake-Claude getestet (Auftrag laeuft nach Trennung weiter, attach liefert den Rest, unbekannter Auftrag, Meldungsdatei). Portal-Patches an Kopie von portal.py getestet (idempotent). server-nach-pc.py mit Testordnern getestet (gleich, neu, geaendert, Konflikt, ignorierte Dateien). Klammer-Check der app.js ausgeglichen (grober Test, kein Parser). NICHT geprueft: app.js im Browser/am Handy (kein node auf dem Server), Java nicht kompiliert, SSH-Weg von server-nach-pc.py, PDF-Vorschau ueber den Server-Job.
- Ergebnis: Dateien liegen in ~/MA-Server auf dem Server. Eingespielt wird mit `sudo bash ~/MA-Server/server/auto-deploy/install.sh` und `sudo bash ~/MA-Server/server/alles-einspielen.sh`; danach spielt Claude Oberflaeche und Bruecken selbst per `server/auto-deploy/deploy-anfordern.sh` ein.
- Rueckweg: Sicherungen `/opt/ma-home/web.bak-<Zeit>`, `/opt/ma-home/portal.py.bak-<Zeit>`, `/usr/local/lib/*.bak`; Auto-Einspielung abschalten mit `sudo systemctl disable --now ma-deploy.path ma-job-notify.path`.
- Offen: Einspielen (Sudo) und Test am Handy; App am PC neu bauen; server-nach-pc.py am PC als geplante Aufgabe `ServerNachPC` eintragen; Entscheidung: Konnektoren im Server-Chat; Projekte/Ordner fuer Chats nur als Filter nach Ordner umgesetzt.

## 2026-10-12 – Musik-Server (Navidrome) vorbereitet (noch nicht installiert)

- Auftrag: Eigener Musik-Streamingdienst als Ersatz fuer ein bezahltes Abo. Neu: `server/musik/install.sh` (Docker-Compose, nur 127.0.0.1:4533, Image per Digest festgenagelt, geringe Rechte) und `server/musik/caddy-beispiel.txt`.
- Pruefung: nur Bash-Syntax. Caddy/Authelia-Konfiguration konnte nicht eingesehen werden, der Caddy-Eintrag ist ein ungeprueftes Beispiel. Docker auf dem Server fuer andrew nicht nutzbar, daher nichts gestartet.
- Offen: `sudo bash ~/MA-Server/server/musik/install.sh`, Musik ablegen, Caddy-Block mit Authelia, Administrator anlegen, Apps testen. Nur eigene/legale Musik.

## 2026-10-12 – Web-Terminal-Reparatur vorbereitet (noch nicht ausgefuehrt)

- Befund: Das Web-Terminal (`ma-home-terminal`, ttyd -> ssh andrew@127.0.0.1) scheitert mit "Permission denied (publickey)": sshd erlaubt seit der Haertung nur Schluessel (`10-ma-haertung.conf`), der Dienst laeuft als ma-web ohne Schluessel. Aus Konfiguration und Fehlermeldung abgeleitet, nicht mit Root geprueft.
- Neu: `server/tools/terminal-reparieren.sh` (Passwort-Anmeldung nur fuer 127.0.0.1/::1 per `Match Address`, Pruefung der wirksamen Einstellung vor dem Neuladen, Rueckbau bei Abweichung). Nicht getestet (braucht Root).
- Ausserdem: SSH (Port 22) war von einem Mobilfunknetz aus nicht erreichbar (Zeitueberschreitung); Ursache Router oder Anbieter offen.

## 2026-10-12 – Jarvis: Lern-Impuls, Zeitplan, Startseiten-Karte (Server-Kopie, noch nicht live)

- Neu: `scripts/server-sync/lern-impuls.py` (waehlt eine eigene Notiz aus 30 Technik/40 Wissen, Haiku ohne Werkzeuge macht drei Lernfragen, schreibt `_Claude-Memory/Dienste/Lern-Impuls.md`, optional ntfy-Push), `server/jarvis/install.sh` (/etc/cron.d/ma-jarvis: Lern-Impuls 18:30; Morgenbrief 06:55 und Fristen 07:30/17:30 nur, wenn nicht schon in der Crontab von andrew), Jarvis-Karte "Jarvis heute" auf der Portal-Startseite (Version 2026-10-12-6), Terminal-Protokoll `~/.ma-term.log`.
- Pruefung: Lern-Impuls einmal echt gelaufen (Haiku, Datei geschrieben, Fragen sinnvoll); Trockenlauf; Cron-Installer nur Syntax. Die Karte in app.js nicht im Browser getestet; Dateipfad `Bibliothek/vault-notizen/...` ueber /api/file aus der Struktur abgeleitet, nicht belegt.
- Befund: Morgenbrief und Fristen-Erinnerung existierten bereits; ob sie in der Crontab von andrew stehen, ist nicht lesbar (crontab unter NoNewPrivileges gesperrt). ~/.ntfy-token existiert nicht, daher kein Push. Mail-Berichte im Vault zuletzt 2026-10-10.

## 2026-10-12 – Volltextsuche und geplante Claude-Aufgaben (Server-Kopie, noch nicht live)

- Neu in `server/claude-bridge/ma-claude-bridge.py`: Op `search` (grep, feste Zeichenkette, ohne Shell; Notizen und Dokumente der Bibliothek, Roharchiv der Chats ausgenommen, bis 40 Treffer) und geplante Aufgaben (`sched_list/sched_set/sched_del`, Zeitplan in `~/.ma-schedule.json` 0600, Scheduler-Thread alle 30 s, je Tag einmal, nur Modus lesen oder Notizen, nie Voll, hoechstens 10, Ergebnis nach `_Claude-Memory/Dienste/Geplant/<Titel>.md`, Meldung ueber den Root-Dienst ma-job-notify). `patch-portal-attach.py` schaltet die neuen Ops in portal.py frei (idempotent).
- Oberflaeche (Version 2026-10-12-7): Suchfeld im Reiter Dateien, Knopf "Aufgaben" im Claude-Tab (Liste, Pausieren, Loeschen, Neu).
- Pruefung: Suche und Zeitplan mit Fake-Claude und Testdaten getestet (Validierung, einmal pro Tag, Ausgabedatei, Meldung, Rechte 0600); Portal-Patch an Kopie. Neu: `tests/portal_smoke.py` (Playwright-Rauchtest in Handy-Groesse mit Platzhalter-API); Playwright/Chromium unter `~/.ma-browsertest` ohne Root installiert.

## 2026-10-12 – Ereignis-Ausloeser, Vorlagen, Paritaet um Verbindungen und neue Dienste erweitert (Server-Kopie, noch nicht live)

- Brücke: geplante Aufgaben haben jetzt den Ausloeser `inbox` (neue Datei in /srv/ma-home/library/inbox, Abkuehlzeit 5 Min, vorhandene Dateien gelten als bekannt, Namen bereinigt, Modus und Ordner serverseitig erzwungen: nur lesen, Bibliothek). Oberflaeche (Version 2026-10-12-8): Auswahl "Ausloeser", Vorlagen Abend-Rueckblick, Wochenrueckblick, Eingang pruefen. Stil-Fehler behoben ([hidden] wurde von CSS ueberstimmt; der Browser-Test hat ihn gefunden).
- Paritaet: `paritaet-check.py` prueft zusaetzlich die Namen der lokalen MCP-Verbindungen (PC `~/.claude.json` und `.mcp.json` gegen Server; `PC_ONLY_MCP` fuer bewusste Ausnahmen), die Dienste ma-term-bridge, ma-deploy.path, ma-job-notify.path, den Cron lern-impuls.py und die neuen Portal-Marker (attach, Suche/Zeitplan, Terminal).
- Pruefung: Ereignis-Ausloeser mit Fake-Claude und Testordner (keine Ausloesung ohne neue Datei, Ausloesung bei neuer Datei, Dateinamen bereinigt, Abkuehlzeit, Ausgabe, Meldung); Browser-Rauchtest 24 von 24; Server-Skript der Paritaetspruefung lokal ausgefuehrt (Syntax und Ausgabe). Nicht geprueft: Lauf der Paritaetspruefung am PC (SSH, PowerShell), echtes Backend, echtes Handy.

## 2026-10-12 – Verbrauch/Limits, Lernrueckmeldung, Fristen-Kalender, Vorab-Test beim Einspielen u. a. (Server-Kopie, noch nicht live)

- Bruecke: Tageslimit je Art (chat 300, council 25, geplant 40; aenderbar ueber `limits.json`), Verbrauch je Tag (Auftraege, Tokens) in `usage.json` mit Op `usage`, Op `lern_feedback`; Zustand (Zeitplan, Verbrauch, Lernstand, Terminal-Protokoll) liegt jetzt unter `/srv/ma-home/library/.jarvis` (im Restic-Backup, Dateien-API sperrt Punkt-Ordner), alte Dateien aus /home/andrew werden einmal kopiert. `patch-portal-attach.py` schaltet die Ops frei und zieht auch den Zwischenstand nach.
- Oberflaeche (2026-10-12-9): laufende Auftraege ueber "Ansehen" auf jedem Geraet live anhaengen, Verbrauch im Aufgaben-Panel, Vorlage Pruefungstraining, `/notiz <Begriff>`, Rueckfrage bei riskanten Terminal-Befehlen (zweites Absenden), Vorlesen-Knopf, Teilen-Menue (share_target, GET, nur Text/Link), Lern-Rueckmeldung "Wusste ich"/"Nochmal" und Link zur Kalenderdatei auf der Jarvis-Karte.
- Skripte: `fristen-ics.py` (Fristen -> Bibliothek/fristen.ics, 06:50 per Jarvis-Cron), `lern-impuls.py` beachtet die Rueckmeldung. `ma-deploy.sh`: geaenderte Oberflaeche wird nur eingespielt, wenn `tests/portal_smoke.py` (als andrew via runuser) besteht.
- Pruefung: Brueckentest (Limits, Verbrauch, Feedback-Validierung, Portal-Patch Zwischenstand), ICS-Datei lokal erzeugt (CRLF, Zeilenlaenge 75), Browser-Test 33 von 33. Nicht geprueft: echtes Backend/Handy, runuser-Aufruf in ma-deploy.sh (braucht Root), Teilen-Menue in der installierten App.
- Fund: BAT1 (COMPAL, Li-ion) meldet 0 % und "Not charging", ACAD online=1, keine Energiewerte; zram (1,6 GB) und Swapdatei (3,9 GB) sind schon aktiv.

## 2026-10-12 – Vault-Reiter (Obsidian-Ersatz) und vault-q (Server-Kopie, noch nicht live)

- Brücke: Op `note` (Aktionen index, read, write, create, rename, delete, backlinks, tags, versions, restore, daily, templates). Nur .md, keine versteckten Ordner, keine Symlinks, `_Claude-Memory` und `Auto Router` nur lesen, 60.000 Zeichen je Notiz, Schreiben mit etag (Konflikt -> Serverfassung wird angeboten), Versionsverlauf (30 Stueck unter `.jarvis/versions`), Loeschen = Papierkorb `.jarvis/trash`, Umbenennen passt `[[Links]]` an (nicht in geschuetzten Ordnern). Tagesnotiz: `10 Leben/Tagesnotizen/JJJJ-MM-TT.md`. Portal-Patch schaltet Op `note` frei.
- Oberflaeche (2026-10-12-12): Reiter "Vault": Ordner und Notizen, Schnellwechsler, Volltext, Zuletzt, Tags, Lesen/Bearbeiten mit Autospeichern, Werkzeugleiste, `[[`-Vorschlaege, anklickbare Wikilinks und Tags, Callouts, Rueckverweise, lokale Graph-Ansicht (SVG), Versionen, Umbenennen/Loeschen, Tagesnotiz, Vorlagen (leer, projekt, lernnotiz, meeting, tagesnotiz), Bilder/PDFs aus dem Vault (`![[bild.png]]`).
- PC: `vault-to-server.py` spiegelt jetzt auch Anhaenge (png, jpg, jpeg, gif, webp, svg, pdf bis 8 MB) auf den Server (wirkt, sobald der PC die neue Fassung hat).
- `scripts/vault-q.py` (+ `vault-q.cmd`): SQLite-FTS5-Index ueber den Vault (selbstaktualisierend), Befehle search, links, near, tags, show, recent, stats, export-neo4j. Messung: dieselbe Suche kostet ca. 300 statt ca. 9.600 Tokens (Faktor 32, eine Stichprobe). Installiert als `~/.local/bin/vault-q`, in den Lese-Modi der Bruecke erlaubt, Hinweis im Server-Abschnitt der CLAUDE.md.
- Pruefung: Bruecken-Backend mit Testvault (Rueckverweise, Tags ohne Code, Konflikt, Versionen, Rename mit Linkanpassung und unveraenderter geschuetzter Notiz, Papierkorb, Pfadangriffe, Groessenlimit); vault-q gegen den echten Vault (487 Notizen, 3.559 Links, 0,2 s je Abfrage nach 7 s Erstaufbau); Browser-Test 47 von 47. Nicht geprueft: echtes Backend und Handy, Neo4j-Import, Anhang-Spiegelung am PC, Schreiben im laufenden Dienst.
- Offen: Entscheidung Philipp, ob der Server die Hauptkopie des Vaults wird (dann PC-Skripte umstellen: Server -> PC als vollstaendiger Spiegel inkl. Loeschen, PC -> Server nicht mehr ueberschreiben).

## 2026-10-12 – Server als Hauptkopie, Chat-Scrollen, Obsidian-/Claude-Funktionen (Server-Kopie, noch nicht live)

- Entscheidung Philipp: Der Server ist die Hauptkopie des Vaults. Flag `/srv/ma-home/library/.jarvis/server-master` (von `alles-installieren.sh` gesetzt, `--ohne-master` verhindert es). `server-to-vault.py`: im Flag-Modus werden auf dem Server entfernte/umbenannte Textnotizen am PC nach `.server-geloescht/<Datum>/` verschoben (nie hart geloescht; Sicherheitsstopp bei auffaellig kleiner Serverliste). `vault-to-server.py`: im Flag-Modus wird eine vom Server seit dem letzten Abgleich geaenderte Notiz nie ueberschrieben, die PC-Fassung landet als "<Name> (PC-Änderung)" in `00 Inbox/Review` auf dem Server. Server-Abschnitt der CLAUDE.md angepasst.
- Chat (2026-10-12-14): Hochscrollen waehrend einer Antwort moeglich (Mitscrollen nur, wenn man unten ist), Knopf "↓ Neueste"; HTML/SVG-Codebloecke mit Vorschau im abgeschotteten iframe (sandbox allow-scripts, ohne allow-same-origin).
- Vault: Gliederung, Lesezeichen (Server-Datei `.jarvis/bookmarks.json`), eingebettete Notizen `![[Notiz]]`, Suchoperatoren `tag:` und `path:`, lokale Graph-Ansicht (Trefferflaeche vergroessert).
- Pruefung: Logik der Hauptkopie-Umstellung mit Testdaten (divert, vanished, Sicherheitsstopp), Bruecke (Notiz-API, Lesezeichen, Verbrauch, Zeitplan, Eingang), Browser-Test 58 von 58 (inkl. Scrollen, Einbettung, Gliederung, Lesezeichen, Vorschau). Nicht geprueft: Lauf der PC-Skripte am echten PC, Backend/Handy, Neo4j-Import.

## 2026-10-12 – Verbrauch pro Nachricht, Datenbank-Zonen, zentrale Automatisierungsliste, MCP-Abgleich (Server-Kopie)

- Chat (2026-10-12-15): unter jeder Antwort eine Zeile mit Modell, Tokens rein/raus, Dauer und Kosten (aus dem result-Ereignis; wird mit dem Chat gespeichert).
- `vault-q` hat Zonen: vault (Standard), projekt (MA-Server: Doku, Skripte, Code), bib (Texte/PDF der Bibliothek, PDF ueber pdftotext). `search --zone ...|--alles`, `show "projekt::Pfad"`. Aeltere Indexdateien werden automatisch erweitert. Erstaufbau 16 s (614 Dateien), danach inkrementell.
- `server/automations.json` + `scripts/automations.py` (list, validate, cron, skripte): eine Quelle fuer alle Automatisierungen (Server-Cron und PC-Aufgaben). `server/jarvis/install.sh` erzeugt die Cron-Zeilen daraus (ohne schon vorhandene Crontab-Eintraege zu verdoppeln); `paritaet-check.py` leitet seine Erwartungen daraus ab.
- `claude-abgleich.py`: neuer Schritt `sync_mcp` (kapselt Fehler): lokale MCP-Verbindungen ohne Zugangsdaten und ohne Windows-Programme gehen automatisch auf den Server (nur Ergaenzen, nie Ueberschreiben, Sicherung `~/.claude.json.ma-bak`); der Rest wird gemeldet; Ausnahmen in `server/claude-config/mcp-nur-pc.txt`.
- `tests/test_sync_logic.py` (17 Pruefungen: Hauptkopie-Modus, MCP-Abgleich inkl. Zusammenfuehren, Automatisierungsliste) und `tests/portal_smoke.py` (59 Pruefungen) bestanden.
- FUND: Ein PC-gesteuerter Auto-Deploy existiert schon und ist installiert: `scripts/server-sync/deploy.py` (laeuft am Ende von claude-abgleich.py) legt COMMITTETE Staende nach ~/deploy-staging und ruft `sudo -n /usr/local/sbin/ma-deploy` (root-eigen, Sudo-Regel fuer andrew, seit 2026-10-11 18:15). Er liefert Weboberflaeche und Bruecke ohne Sudo von Philipp aus; vorher prueft er JS mit `node --check`. Nicht abgedeckt (bleibt Sudo): portal.py-Freischaltungen (attach, Ops, Terminal-Route), Terminal-Bruecke, Meldungs- und Einspiel-Dienste, Zeitplan, Navidrome, SSH-Reparatur, Hauptkopie-Flag. Die von mir gebaute Server-seitige Auto-Einspielung (server/auto-deploy) ist eine zweite, unabhaengige Moeglichkeit, die auch ohne PC funktioniert.
- Folge: Sobald der PC den Server-Stand abgeglichen, committet und deployed hat, laufen die neue Oberflaeche und Bruecke, auch ohne alles-installieren.sh; Funktionen, die neue Ops brauchen (Vault, Suche, Aufgaben, Verbrauch), melden bis zum portal.py-Patch einen Fehler 400.

## 2026-10-12 – GitHub-Veroeffentlichung im Abgleich robust gemacht (Server-Kopie)

- `claude-abgleich.py`: neue Funktion `git_publish` ersetzt das bisherige `git add -A` + Commit + stilles Push. Es werden nur die vom Server geholten Dateien committet (per Pathspec aus Datei, mit NUL-getrennter Liste, damit keine Befehlszeilen-Grenze greift), vorher Pruefung auf Geheimnisse (Dateiname: .env, *.key, *.pem, token/credential/passwort/secret im Namen; Inhalt: private Schluessel, ghp_/github_pat_/sk-/xox-/AKIA-Muster) -> solche Dateien werden NICHT committet und gemeldet. Unfertige PC-Arbeit bleibt ausserhalb des Commits (der Auto-Deploy liefert nur Committetes). Push erfolgt, sobald das lokale Repo dem Remote voraus ist (auch fuer eigene Commits und nach frueheren Fehlschlaegen); Fehlschlaege erscheinen im Bericht und im Log. Remote laut setup-status.md: github.com/xSuice/Claude (main).
- Test: `tests/test_git_publish.py` (6 Pruefungen mit lokalem Bare-Remote: Commit+Push, Geheimnisse, fremde Arbeit, nachtraeglicher Push, Push-Fehler) bestanden. Nicht geprueft: Lauf am echten PC mit dem echten GitHub-Remote und dessen Anmeldung.

## 2026-10-12 – Statusbericht, Reiter „Neu“, Mail-/Kalender-Aufgabe, Zugangs-Freigabe fuer Verbindungen (Server-Kopie)

- `scripts/server-sync/status-bericht.py` (ohne Modell, ohne Root): sammelt Laufzeit, RAM, Platte, Wachhund, Dienste, `apt`-Updates (nur lesen, Neustart noetig?), Portal-/Bruecken-Version laufend gegen Projekt, letzte CHANGELOG-Eintraege, offene Hoch-Aufgaben aus BACKLOG, Fristen, Mail-Tagesbericht, Ergebnisse geplanter Aufgaben, Eingang, Verbrauch. Schreibt `/srv/ma-home/library/status.json` (Portal) und `_Claude-Memory/Dienste/Status.md` (Vault). Eingetragen in `server/automations.json` (07:00, 13:00, 19:00); `server/jarvis/install.sh` erzeugt die Cron-Zeilen.
- Echter Lauf auf dem Server: meldet korrekt "Portal laeuft 2026-10-11-4, Projekt 2026-10-12-16" und "Bruecke nicht aktuell" (Einspielung steht aus), 5 Pakete aktualisierbar, kein Neustart noetig.
- Portal (2026-10-12-16): neuer Reiter „Neu“ (Hinweise, Fristen, Mails, Ergebnisse geplanter Aufgaben, Updates, Neues am System, Offenes, Server). Zeigt "noch kein Bericht", solange status.json fehlt.
- Bruecke: neuer Modus `konnektoren` fuer geplante Aufgaben (Vorlage „Posteingang und Kalender pruefen“ in den Aufgaben). Erlaubt nur lesende Werkzeuge von Gmail, Google Kalender und Multi Mail (`CONNECTOR_READ`), kein Write/Edit/Bash (die Bruecke schreibt das Ergebnis selbst), damit Mailtext nichts aendern kann; Senden/Loeschen/Beschriften ist nie freigeschaltet, `ma-guard` bleibt aktiv. Nur dieser Modus laedt Verbindungen (sonst `--strict-mcp-config`). Gilt nach Einspielung der Bruecke.
- Verbindungen: Konto-Verbindungen (claude.ai Gmail, Kalender, Drive u. a.) sind in der Server-Sitzung schon da (gleiches Konto). Fuer lokale MCP-Server mit Zugangsdaten: `claude-abgleich.py` uebertraegt sie nach ausdruecklicher Freigabe von Philipp (Datei `server/claude-config/mcp-zugang.ok` oder `--mcp-zugang`) direkt per ssh-Stdin in `~/.claude.json` des Servers (0600, Sicherung `.ma-bak`), nie ueber Git/Log/Bericht. Windows-Programme (z. B. GMX-exe) und unbekannte Programme bleiben ausgenommen (Meldung). `settings.json` sperrt Lesen von `~/.claude.json` fuer den Server-Chat.
- Tests: `portal_smoke.py` 63/63, `test_sync_logic.py` 21/21, `test_git_publish.py` 6/6. Nicht geprueft: Lauf von `sync_mcp` mit Zugangsdaten am echten PC, `konnektoren`-Lauf mit echten Mails, Reiter „Neu“ am Handy.

## 2026-10-12 – Reiter „Musik“ (Spotify-Ersatz ohne Abo) (Server-Kopie)

- Portal (2026-10-12-17): neuer Reiter Musik. Ordner durchsuchen, Volltextsuche über Titel und Ordner, Ordner abspielen oder mischen (mit Unterordnern), Warteschlange (Einzeltitel anhängen, entfernen, Reihenfolge merken), Zufall, Wiederholen (aus/alle/ein Titel), Spulen, gespeicherte Wiedergabelisten (im Browser). Der Player lebt ausserhalb der Ansicht: die Musik laeuft beim Wechsel der Reiter weiter; Steuerung auf dem Sperrbildschirm ueber MediaSession. Quelle: `/srv/ma-home/library/media/musik` (mp3, m4a, aac, ogg, opus, flac, wav).
- Neue Portal-Route `/api/audio` (`server/musik/patch-portal-audio.py`, idempotent, wird von `update-bridge.sh` eingespielt): richtiger Inhaltstyp, inline, Range (Spulen; das iPhone verlangt das), gleiche Pfadpruefung wie `/api/file`, nur Audio-Endungen. Mit einer Test-App geprueft: 200, 206 (Anfang, Mitte, Ende, Suffix), 416, 415 bei Nicht-Audio, 403 bei `..`.
- Navidrome (`server/musik/install.sh`, Docker) bleibt die Erweiterung fuer Handy-Apps (Subsonic: Symfonium, Substreamer) mit Cover, Kuenstlern und Alben; das braucht Sudo und einen Caddy-Eintrag (`caddy-beispiel.txt`). Der Portal-Player braucht beides nicht.
- `SUDO-ALLES.sh` im Projektstamm: ein Aufruf fuer alle Sudo-Schritte (Terminal-Reparatur, alles installieren, Statusbericht).
- Test: `portal_smoke.py` 68/68 (Chromium, Platzhalter-API, echte WAV-Wiedergabe: Start, Weiter, Reiterwechsel, Unterordner). Nicht geprueft: Wiedergabe am echten Handy (iPhone/Android), grosse Bibliotheken (Suche laedt bis 3000 Titel einmalig), Sperrbildschirm-Tasten, `/api/audio` im echten Portal (erst nach Einspielung).

## 2026-10-13 – Terminal wählt den Ordner automatisch (Server-Kopie)

- Portal (2026-10-12-18): Im Reiter Terminal ist "Automatisch" jetzt die Standardwahl beim Ordner. `termAutoDir` waehlt nach dem Befehl: Notizen (vault, vault-q, .md, notiz), Bibliothek (/srv/ma-home, library, inbox, media, Mediendateien), MA-Server (git, tests/, scripts/, .py, .sh, .js, CHANGELOG, npm, node), sonst Server-Home. Der gewaehlte Ordner steht vor dem Befehl in der Ausgabe. Eine manuelle Wahl bleibt bestehen (auch beim Reiterwechsel). Die Terminal-Bruecke bleibt unveraendert (bekommt weiter den Ordnernamen).
- Test: `portal_smoke.py` 73/73 (Standard, drei Zuordnungen, manuelle Wahl). Nicht geprueft: Zuordnung bei ungewoehnlichen Befehlen; die Heuristik ist einfach gehalten.

## 2026-10-13 – Auto-Rechte: Voll ohne zweiten Druck, bessere Erkennung (Server-Kopie)

- Ursache der wiederholten Schreibsperren: `router_core.suggest_access` waehlte nur bei Befehlswoertern UND Projektwoertern "Voll"; Saetze wie "mach weiter" oder "im Terminal soll ..." landeten bei "Nur lesen" im Ordner Notizen. Zusaetzlich verlangte das Portal bei "Voll" immer einen zweiten Druck auf Senden.
- `scripts/router/router_core.py`: mehr Projektwoerter (Reiter, Terminal, Player, Musik, Tests, Version, CHANGELOG, GitHub, Cron, Abgleich, MCP, .py/.sh ...) und neue Umsetzungswoerter (_BUILD_WORDS: baue, ergaenze, erweitere, teste, "mach weiter", einspielen ...). Im Ordner MA-Server fuehren sie zu "Voll". `voll_senden` wird weiterhin nie vorgeschlagen.
- Portal (2026-10-12-19): Was Auto als Rechte waehlt, wird sofort gesendet (Hinweis "Auto: Voll · Ordner"); der zweite Druck entfaellt. Manuell gewaehltes "Voll" fragt weiter einmal pro Sitzung, "Voll + Senden/Loeschen" jedes Mal. Begruendung: Auto entscheidet nur aus dem eigenen Text, nie aus Mails oder Webseiten. Weiter gesperrt: ma-guard (Senden/Loeschen ueber Verbindungen), deny-Liste in settings.json.
- Tests: `test_router_core.py` 39/39 (5 neue Faelle), `portal_smoke.py` 74/74. Die Bruecke nutzt `router_core.py` aus /usr/local/lib erst nach der Einspielung (SUDO-ALLES.sh / update-bridge.sh).

## 2026-10-13 – Rechte-Eskalation, Terminal-Sudo (Server-Kopie)

- Portal (2026-10-12-20): Rechte-Eskalation. Hat Auto Ordner oder Rechte gewaehlt und der Lauf meldet verweigerte Werkzeuge (`permission_denials` im result-Ereignis), setzt das Portal die Aufgabe mit der naechsthoeheren Stufe fort (lesen → notizen → voll; bei Bash gleich voll; der Ordner folgt dem verweigerten Pfad: Vault, Bibliothek, MA-Server, Home), hoechstens zweimal, nie mit Senden/Loeschen. Die Fortsetzung laeuft in derselben Sitzung mit kurzem Text ("Die Rechte wurden automatisch erhoeht … mach zu Ende"), damit keine Tokens fuer die Wiederholung der ganzen Aufgabe anfallen. Manuell gewaehlte Rechte und Ordner werden nie eskaliert.
- Terminal-Sudo: `server/term-bridge/sudo-erlauben.sh` (Sudo, einmal): Gruppe `ma-sudo` + `/etc/sudoers.d/ma-term-sudo` (`%ma-sudo ALL=(root) NOPASSWD: ALL`, mit visudo geprueft); `install.sh` erzeugt die Unit von ma-term-bridge dann mit `NoNewPrivileges=no`, `SupplementaryGroups=ma-sudo`, `ProtectSystem=no`. NUR dieser Dienst hat Sudo; der Claude-Chat (NoNewPrivileges), SSH-Sitzungen und andere Dienste nicht. Das Skript prueft danach, dass die Gruppe wirkt und andrew ohne Gruppe kein Passwort-Sudo hat; sonst Rueckbau (Schalter `--user-regel` fuer die breitere Benutzerregel). Im Portal fragen sudo-Befehle erst beim zweiten Absenden. `SUDO-ALLES.sh` fuehrt den Schritt mit aus (auslassen mit `OHNE_TERMINAL_SUDO=1`).
- Tests: `portal_smoke.py` 78/78 (Eskalation lesen → notizen → voll mit Ordnerwechsel, Sudo-Bestaetigung); Unit-Erzeugung in beiden Varianten geprueft. NICHT geprueft: `sudo-erlauben.sh` selbst (braucht Root), `permission_denials` im echten Stream (Format der CLI laut Doku, im Test nachgebaut), ob die installierte sudo-Version die Gruppe auswertet (das Skript prueft es beim Lauf).

## 2026-10-13 – Auto-Einspielung: zwei Fehler gefunden und im Projekt behoben (Server-Kopie)

- FUND 1: `/var/log/ma-deploy.log` zeigt zwei Rueckfaelle heute (04:26, 06:07): "Browser-Test bestanden", dann "Portal antwortet nach dem Einspielen nicht richtig; Oberflaeche zurueckgesetzt". Ursache: Die Nachpruefung las die Version per HTTP aus `/assets/sw.js`; das verlangt eine Anmeldung (401, geprueft mit curl), also fehlte die Version und das Skript setzte immer zurueck. Fix in `server/auto-deploy/ma-deploy.sh`: healthz muss 200 sein, die Oberflaeche 200/401/403 (nicht 5xx/000) und die eingespielte Datei die erwartete Version haben.
- FUND 2: `deploy-anfordern.sh` scheitert fuer den Chat mit "Read-only file system": die Bruecke (ProtectSystem=strict) durfte nur in `/srv/ma-home/deploy/notify` schreiben, nicht die Datei `request` anlegen. Fix in `server/auto-deploy/install.sh`: Drop-in `ReadWritePaths=-/srv/ma-home/deploy` (der Ordner ist sticky und root-eigen; status.txt bleibt fuer andrew unersetzbar).
- Wirkung erst nach `sudo bash ~/MA-Server/SUDO-ALLES.sh` (Schritt 2 installiert die Auto-Einspielung neu; das Drop-in gilt nach dem Neustart der Bruecke). Danach kann ich nach Aenderungen selbst einspielen. Nicht geprueft: der Lauf von ma-deploy.sh als Root.

## 2026-10-13 – sudo-erlauben.sh diagnostizierbar gemacht (Server-Kopie)

- Befund nach Philipps Lauf im Web-Terminal: Portal 2026-10-12-20 live, Auto-Einspielung funktioniert (06:39 OK), Gruppe `ma-sudo` (GID 975) existiert, aber `/etc/sudoers.d/ma-term-sudo` fehlt und die Unit der Terminal-Bruecke ist die eingeschraenkte Variante: Schritt 3 hat sich entweder nach der Selbstpruefung zurueckgebaut oder ist vorher abgebrochen; die alte Fassung verwarf die Fehlermeldung. Laut sudo.conf(5) gilt auf Linux `group_source=adaptive` (Gruppenliste des Prozesses), die Gruppenregel sollte also grundsaetzlich greifen.
- `sudo-erlauben.sh`: schreibt jetzt `/var/log/ma-sudo-erlauben.log` (644), zeigt die visudo-Meldung und den echten sudo-Fehler samt Gruppenliste des Pruefprozesses, und prueft mit `setpriv` (andrew mit genau den Gruppen der Bruecke) statt mit `runuser`. Syntax geprueft; nicht als Root gelaufen.
- Ergebnis des Laufs (06:51): Gruppenregel greift nicht, Rueckbau. Ursache sehr wahrscheinlich `sudo-rs 0.2.13` (Ubuntu 26.04), das die Zusatzgruppen des Prozesses nicht auswertet; nicht belegt. Entscheidung: im Terminal beim Passwort bleiben, `--user-regel` nur nach ausdruecklichem Ja.

## 2026-10-13 – Neuer Chat vollautomatisch ab 300 000 Token (Server-Kopie, noch nicht live)

- `portal-ui/web/app.js` (`claudePump`): Ist der Kontext nach einer fehlerfreien Antwort ueber 300 000, sendet das Portal selbst den Auftrag „Skill uebergabe ausfuehren“ (Rechte mind. Notizen), und beginnt danach einen leeren Chat mit dem Hinweis „Schreib ‚weiter‘“ (Grundregel 13 laedt dann die Uebergabe). Fehler, verweigerte Werkzeuge oder Rechte-Eskalation: Chat bleibt unveraendert. Syntax und Ablauf nicht geprueft (kein `node`/Browser-Test in dieser Sitzung); Einspielen: `sudo bash ~/MA-Server/portal-ui/deploy-ui.sh`.

## 2026-10-13 – Verbrauchs-Datenbank `usage-db` (Server-Kopie, live)

- Befund: Eine Wissensdatenbank gibt es schon (`vault-q`, SQLite/FTS5, 633 Dateien); keine zweite angelegt. Die Bruecke zaehlt nur Jobs und Token je Kategorie und Tag (`usage.json`), ohne Modell, Sitzung oder Projekt. Das war die Luecke fuer "Aufwand pro Aufgabe".
- `server/tools/usage-db.py` (Symlink `~/.local/bin/usage-db`, Datenbank `/srv/ma-home/library/.jarvis/usage.db`): liest die Sitzungsprotokolle der Claude-CLI (`~/.claude/projects/*/*.jsonl`) inkrementell, speichert nur Zaehler (Zeit, Sitzung, Projekt, Modell, Token), nie Text. Befehle `report [--days N] [--by day|model|project|session]`, `top`, `stats`. Keine Preise: es wird nur gezaehlt, nicht in Geld umgerechnet. Standardbibliothek, kein Root, kein Eingriff in die Bruecke.
- Geprueft am echten Bestand (184 Protokolle, 7 Tage): Tagessummen, Aufteilung nach Modell und Projekt, zweiter Lauf liefert identische Zahlen (idempotent), Streaming-Duplikate je Antwort-ID zusammengefuehrt, Platzhalterzeilen `<synthetic>` ausgeschlossen. Nicht geprueft: Abgleich mit der Abrechnung des Anbieters; ob die Protokolle auch Aufgaben der Bruecke vollstaendig enthalten.
- `paritaet-check.py`: `usage-db.py` in die Liste `FILES` aufgenommen.
- Ziel Philipp: ein 5-Stunden-Fenster soll fuer zwei Personen reichen. Neu `usage-db windows` (Verbrauch je 5-h-Fenster, Naeherung). Messung 07.-13.10.: groesstes Fenster 4,1 Mio neu + 527k Ausgabe (494 Antworten, 10.10. ab 06:42 UTC), Opus 13 % der neu+raus-Token, Sitzungen mit bis zu 960k Kontext; Cache-Lesen (882 Mio) ist um ein Vielfaches groesser als neu verarbeitet (21,7 Mio). In den Protokollen steht kein Limit-Treffer (weder Beleg dafuer noch dagegen). Wie der Anbieter Cache-Lesen auf das Limit anrechnet, ist nicht belegt.
- Portal 2026-10-12-22: Kontextgrenze fuer den automatischen neuen Chat als Konstante `CTX_MAX` = 200 000 (vorher 300 000, an drei Stellen verstreut), weil jede Antwort den ganzen Kontext neu liest. Wirkung nicht gemessen; nach dem Einspielen mit `usage-db report --by session` vergleichen. Zwei Personen sind in der Datenbank nicht getrennt (Protokolle tragen kein Benutzerfeld).

## 2026-10-13 – Bilder-Knopf mit Mehrfachauswahl (Server-Kopie)

- Befund: Das Eingabefeld `#cfile` hatte schon `multiple`, `attachAdd` laedt mehrere Dateien, `MainActivity.onShowFileChooser` reicht den Modus korrekt weiter. Vermutung (nicht geprueft): Ohne `accept` oeffnet Android die allgemeine Dateiauswahl, in der Mehrfachauswahl nur per langem Druecken geht; oder die installierte App ist aelter als der Quellcode.
- `portal-ui/web/app.js`: neuer Knopf 🖼 mit eigenem Feld `#cpic` (`accept="image/*" multiple`) oeffnet die Galerie mit Auswahlkreisen; 📎 bleibt fuer allgemeine Dateien. VERSION 2026-10-12-21 (app.js und sw.js). Nicht im Browser getestet.

## 2026-10-13 – Stand-Vergleich PC / GitHub / Server (Server-Kopie)

- `deploy.py`: neue Funktion `write_rev` schreibt nach jedem erfolgreichen Lauf (auch "Nichts zu tun") den PC-HEAD-Hash nach `~/MA-Server/DEPLOYED-REV` auf dem Server.
- `paritaet-check.py`: liest `DEPLOYED-REV` (Zeile `R`) und meldet im Bericht unter "Git" den Dreier-Stand PC-HEAD / GitHub (`git ls-remote origin main`) / Server samt Abstand in Commits.
- Geprueft: nur Syntax (py_compile). Nicht geprueft: Lauf am PC mit echtem SSH und GitHub-Remote. Der Server ist kein Git-Repo; die Aenderung wird per `ClaudeAbgleich` zum PC geholt.
- Neu, noch nicht gelaufen: `scripts/ma-authelia-diag.sh` (rein lesende Authelia-Diagnose fuer den geplanten QR-/Passkey-Login; Start mit sudo durch Philipp). In `FILES` von `paritaet-check.py` bewusst nicht eingetragen (nur Einmal-Diagnose).
