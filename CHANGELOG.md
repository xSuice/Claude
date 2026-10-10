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
