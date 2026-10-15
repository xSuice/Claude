# MA Home – Änderungshistorie

Alle Zeiten: Europe/Berlin. Diese Historie beginnt am 2026-10-05. Sie ist keine vollständige Rekonstruktion früherer Servereingriffe.

## 2026-10-15 – JARVIS Integrationsprüfung vor dem Mobile-Test (Server)

- Auftrag: Integrationsübersicht mit echten Abläufen, Teil des Prüfpakets.
- Betroffene Dateien: `docs/jarvis/INTEGRATIONSPRUEFUNG-V16.md` (neu). Keine Änderung an Code oder Konfiguration.
- Prüfung: Testauftrag `j20261015-6a27fc` über den Brücken-Socket, 3/3 abgenommen, eigener Testlauf 7/7 grün.
- Offen: Brücken-Update, Browser-Durchlauf (Portal, Verlauf, Download), Router-Wirkung.

## 2026-10-15 – JARVIS Phase E: Verbesserungsauftrag mit Probelauf-Gate (Server)

- Auftrag: B39 Phase E, Kette JARVIS -> Claude Code ohne Rechteausweitung.
- Betroffene Dateien: `server/jarvis/core/brain-runtime/taskengine.py` (neue Schritt-Art `improve`, `_run_improve_step`, `_improver`), `tests/test_v16_improve.py` (neu), `tests/v16_fakes.py` (`cfg_extra`), `server/jarvis/PHASE-E-ENTWURF.md`, `BACKLOG.md` (B39).
- Änderung: Claude schreibt nur einen Patch (`patch.diff`) in den Arbeitsordner; `improve.py trial` prüft ihn gegen die unveränderten Tests. Erlaubt nur in Aufträgen mit Option `improve=true` und nur wenn `improve.enabled` in der Konfiguration steht (Standard: aus). Prüfungen kommen aus der Konfiguration (`improve.checks`), nie aus dem Plan. `allow_promote` bleibt aus; das Repo wird nicht verändert. Tagesgrenze und fehlende Konfiguration beenden den Schritt ohne Korrekturrunde.
- Prüfung: neue Tests (10) und gesamte Suite im Quellbaum: 320 Tests grün, 4 übersprungen.
- Rückweg: `rollback-v16.sh`; die Funktion ist ohne `improve.enabled` wirkungslos.
- Offen: Freigabe-Schritt für Philipp (`human`) als Planvorlage, Einspielen in den aktiven Release, echter Lauf mit kleiner Änderung, `Claude:`-Kennzeichnung im Claude-Chat.

## 2026-10-15 – JARVIS Phase E: Nachtrag, echter Lauf und zwei Korrekturen (Server)

- Eingespielt: Release `20261015-032153-25df9d6` (322 Tests grün, 4 übersprungen, `doctor` ok). Commits `a9407b2` (Planer-Hinweis für Verbesserungsaufträge) und `25df9d6` (Korrektur).
- Fehler 1 (behoben): Ein abgelehnter Probelauf hinterließ `improve-trial.json`; die Abnahme (`contains verdict`) wertete den Auftrag als Erfolg. Auftrag `j20261015-075335` meldete deshalb fälschlich `done` (alle drei Probeläufe waren `rejected`). Jetzt: Datei nur bei `improved`/`neutral`, Abnahme per `regex` auf dieses Urteil, Regressionstest ergänzt. Der Ergebnisordner `/srv/ma-home/library/JARVIS/j20261015-075335` ist noch vorhanden und irreführend (Löschen wartet auf Freigabe).
- Fehler 2 (behoben): Die Prüf-Aktion `unit-attribution` hatte ein falsches `cwd`; die Basis schlug schon vor dem Patch fehl. Neu: `cwd` = `server/jarvis/core/brain-runtime`. Beleg: derselbe Patch ergibt jetzt `neutral` mit bestandenen Prüfungen auf Basis und Kandidat.
- Folgefehler (bereinigt): Aus dem fälschlichen `done` wurde die gelernte Vorlage #6; sie wurde mit `jarvis_cli forget template 6` zurückgenommen.
- Echter Lauf: `j20261015-465d49` (Haiku, ein Claude-Schritt): Patch erzeugt, Probelauf #4 `neutral`, Repo unverändert, kein `promote`. Hinweis: Dieser Lauf nutzte noch die Vorlage #6 mit der schwachen Abnahme (`contains verdict`); das Urteil `neutral` stammt aus `improve-trial.json` selbst. Ein Lauf mit der neuen regex-Abnahme steht noch aus.
- Konfiguration: `improve.enabled` ist AN (`max_trials_per_day` 3, `allow_neutral` aus). Prüfungen: `unit-attribution`, `compile` (`~/.config/ma-jarvis/improve-actions.json`). Sicherung der Konfiguration davor: `~/.local/share/ma-jarvis/backups/jarvis.json.vor-improve-20261015`.
- Offen: Freigabe-Schritt (`human`) als Planvorlage, Brücke reicht `options` nicht durch (`improve` nur über die CLI), `Claude:`-Kennzeichnung im Claude-Chat, Rollback-Test mit aktiver Phase E, Phase F bis I.

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

## 2026-10-13 – vault-q: verbesserte Suche (Server-Kopie)

- `scripts/vault-q.py` ersetzt durch den Stand von `vault-q-test.py`: Stoppwörter (de/en, auch Verbformen wie "hatten"), Suche erst mit UND, dann aufgefüllt mit ODER, Gewichtung nach Bereich (Archiv 0,35; Import und `_Claude-Memory/Archiv` 0,5; Romanordner `Projekt Schmejd`, `Crimson Zone` und `30 Technik/Arduino` 0,4; `_Claude-Memory` und `30 Technik` 1,3), Treffer mit gleichem Dateinamen und Titel nur einmal, Datum als zusätzliche Spalte in der Ausgabe.
- Geprüft: 4 echte Fragen aus dem Chat-Archiv gegen alte und neue Suche (3 von 4 klar besser, 1 mit Restrauschen); danach `vault-q.py search` einmal gelaufen, Datei identisch mit `vault-q-test.py`. Nicht geprüft: Goldstandard mit 20 Fragen, Treffer@5, Skripte, die die Ausgabe zeilenweise auswerten (neue Spalte Datum).
- Parität: PC-Kopie noch nicht angepasst, geht über `ClaudeAbgleich`.
- Rückweg: alte Version in `/srv/ma-home/library/vault-snapshots/wissen-vor-umbau-20261013-0921/` (altes `vault-q.py`).

## 2026-10-13 – vault-q: Anfrageprotokoll und `report` (Server-Kopie)

- `scripts/vault-q.py`: neue Tabelle `qlog` (Zeit, Frage, Zone, Trefferzahl, erste fünf Treffer, Dauer) in der Index-Datei `/srv/ma-home/library/.jarvis/vault-index.db`; `search` schreibt jede Anfrage dorthin (`log_query`, Fehler beim Schreiben stören die Suche nicht, aus mit `MA_VQ_NOLOG=1`). Neuer Befehl `vault-q report [-n 15]`: Anfragen ohne oder mit einem Treffer, häufige Wörter als Stoppwort-Kandidaten. Nur Vorschläge, Stoppwörter und Gewichte ändert weiter nur ein Mensch im Code.
- Datenklasse B: Fragen bleiben lokal in der Index-Datei auf dem Server.
- Geprüft: `py_compile`, ein Suchlauf und `report` gegen eine Kopie der Datenbank (`/tmp/vq-test.db`, 1 Anfrage erfasst); danach `vault-q.py report` gegen die Live-Datei. Nicht geprüft: längerer Betrieb, parallele Zugriffe, Verhalten nach `ClaudeAbgleich` am PC.
- Parität: PC-Kopie noch nicht angepasst, geht über `ClaudeAbgleich`.
- Rückweg: `vault-q.py` aus der Sicherung `/srv/ma-home/library/vault-snapshots/wissen-vor-umbau-20261013-0921/` zurückkopieren; die Tabelle `qlog` kann bleiben oder mit `DROP TABLE qlog` entfernt werden.

## 2026-10-13 – vault-q: Filter --art und --status (Server-Kopie, live)
- `vault-q search ... --art fakt|entscheidung|aufgabe|annahme --status gueltig|veraltet|offen|erledigt`. Liest `art` und `status` aus dem Frontmatter (nur Vault), Spalten in `notes`; beim ersten Lauf wird der Index einmal komplett neu eingelesen.
- Geprüft auf Indexkopie und live: `search "Physik" --status aktiv` findet genau die Fachnotiz. Bisher setzt nur `status` in Altnotizen (Freitext: aktiv, aktuell, im aufbau ...), `art` ist noch in keiner Notiz gesetzt.
- Sicherung der alten Fassung: `vault-snapshots/wissen-vor-umbau-20261013-0921/vault-q.py.vor-filter`. PC-Kopie und `paritaet-check.py` noch offen (kommt über ClaudeAbgleich).

## 2026-10-13 – vault-q-gold.py: Goldstandard der Suche (Server-Kopie)
- Neues Skript `scripts/vault-q-gold.py`: 20 Fragen, Treffer@5 und MRR, alt (Sicherung) gegen neu (Live-Index). Ergebnis: alt 4/20 (MRR 0,20), neu 18/20 (MRR 0,67). Auswertung und Schwächen: Vault-Notiz `30 Technik/MA-Server/Goldstandard-Suche.md`.
- Neu in `FILES` von `paritaet-check.py` eintragen, PC-Kopie folgt über ClaudeAbgleich.
- Nachtrag: Test, Hub-Notizen (Crimson Zone, Projekt Schmejd, Arduino) in `RANK` von der Ordner-Abwertung auszunehmen, brachte keine Besserung (17 statt 18 von 20) und wurde zurückgenommen; `vault-q.py` ist wieder der Stand vor dem Test. Erwartung "Eternal Bonds" im Goldstandard um `Projekt Schmejd.md` ergänzt.

## 2026-10-13 – Portal-Reiter „Verbindungen“ (installiert, Ansicht im Browser noch ungeprüft)

- Auftrag: Philipp will den Portal-Chat näher an Claude Desktop bringen (Plan: `Plan-Portal-Chat-wie-Desktop`, Schritt 1).
- Betroffene Dateien: `server/claude-bridge/ma-claude-bridge.py` (Op `connectors`), `portal-ui/web/app.js` und `sw.js` (Reiter, Version 2026-10-13-1), neu `portal-ui/patch-portal-connectors.py`, `portal-ui/entwurf-verbindungen/installieren.sh`; angepasst `server/claude-bridge/patch-portal-images.py` und `patch-portal-attach.py` (erkennen spätere Staende von `portal.py`; der erste Installationsversuch brach bei `patch-portal-images.py` mit „Stelle nicht gefunden“ ab).
- Prüfung: Python-Dateien kompiliert, Skript mit `bash -n`; Patches gegen eine Kopie der echten `portal.py` getestet (idempotent, Op-Liste bleibt vollständig). `claude mcp list` liefert 40 Verbindungen, Parser liest alle. `app.js` ist ungeprüft (kein node auf dem Server), Aufruf von `claude mcp list` aus der Brücke ungeprüft.
- Ergebnis: Philipp hat `installieren.sh` per Sudo ausgeführt; Brücke und Portal neu gestartet, beide Dienste „active“. Test der Op am Brückensocket: 40 Verbindungen, 29 verbunden, 11 Anmeldung nötig. `'connectors'` steht laut Übergabe in der Op-Liste von `portal.py` (Zeile 362). Ansicht `verbindungen()` in `app.js` im Browser noch nicht bestätigt.
- Rückweg: Kopf von `installieren.sh`; Quellsicherungen `portal-ui/entwurf-verbindungen/*.vor-verbindungen`.
- Parität: `paritaet-check.py` prüft jetzt den Marker `'connectors'` in `portal.py` (`MARKERS`; `patch-portal-connectors.py` ist ein Einmal-Patch ohne Serverpfad und gehört nicht in `FILES`). PC zieht über `ClaudeAbgleich` nach.

## 2026-10-13 – Portal: Slash-Menü für Befehle und Skills (Server-Kopie, noch nicht eingespielt)

- Auftrag: Plan `Plan-Portal-Chat-wie-Desktop`, Schritt 2 (Philipp: „Ja“).
- Betroffene Dateien: `portal-ui/web/app.js` (`SLASH_CMDS`, `SLASH_SKILLS`, `slashMenu()`, Skill-Zweig in `slashRun()`, `/hilfe`), `style.css` (`.cslash`), `app.js`/`sw.js` Version `2026-10-13-2`. Brücke und `portal.py` unverändert.
- Verhalten: Tippen von `/` öffnet ein Menü mit Befehlen und Skills, Klick setzt `/name `. `/<skill> Text` sendet „Nutze den Skill …“ mit den Auto-Rechten wie bei `/plan`. Skill-Liste von Hand gepflegt (uebergabe, bild, docx, pdf, pptx, xlsx, video, netz, ma-server-ops, obsidian-librarian); ob alle im Portal-Chat verfügbar sind, ist ungeprüft.
- Prüfung: keine JS-Laufzeit auf dem Server (kein node), Syntax und Darstellung ungeprüft. Einspielen: `sudo bash ~/MA-Server/portal-ui/deploy-ui.sh`.
- Parität: PC zieht über `ClaudeAbgleich` nach.

## 2026-10-13 – Admin-Schalter „Auto-Einspielung erlauben“ (Server-Kopie, noch nicht installiert)

- Auftrag: Philipp will die Auto-Einspielung (Root-Dienst `ma-deploy`) nur für Admins und als Checkbox schaltbar.
- Dateien: `server/auto-deploy/patch-portal-deployswitch.py` (neu, Route `/api/deploy/switch`, nur `g.admin`), `server/auto-deploy/schalter-einrichten.sh` (neu, Sudo-Skript), `server/auto-deploy/ma-deploy.sh` (spielt nur ein, wenn der Schalter an ist), `portal-ui/web/app.js` (Checkbox `#cdep` im Chat, Version `2026-10-13-3`), `sw.js`, `style.css`.
- Sicherheit: Der Schalter ist die Datei `/srv/ma-home/deploy-schalter/erlaubt` in einem Ordner `root:ma-web` (0775). `andrew` ist nicht in `ma-web` und kann die Datei nicht anlegen; nur das Portal (Admin-Route) und root. Voreinstellung nach der Installation: AUS. Bei AUS meldet `ma-deploy.sh` „AUS …“ in `status.txt` und tut nichts. Manuelles Einspielen mit `sudo bash portal-ui/deploy-ui.sh` bleibt unberührt.
- Prüfung: `bash -n` und `py_compile` für die neuen Skripte; Portal-Patch gegen das echte `portal.py` und `app.js` im Browser nicht getestet (kein node). Annahmen ungeprüft: Dienstname `ma-home-web`, `os`/`jsonify`/`g` in `portal.py` importiert (Importzeilen gelesen, passt).
- Einspielen: `sudo bash ~/MA-Server/server/auto-deploy/schalter-einrichten.sh`, danach `deploy-anfordern.sh` oder `sudo bash ~/MA-Server/portal-ui/deploy-ui.sh` für die Oberfläche.
- Offen: `deploy-anfordern.sh` scheitert im Chat weiter an `/srv/ma-home/deploy/request` (Fund 2, braucht `SUDO-ALLES.sh`). `paritaet-check.py` meldet `ma-deploy.sh` als abweichend, bis das Skript installiert ist.
- Parität: PC zieht über `ClaudeAbgleich` nach.

## 2026-10-13 – PostgreSQL + pgvector: Einrichtungsskript (Vorbereitung)

- Auftrag: Philipp will den Vault-Index von SQLite/FTS5 auf PostgreSQL + pgvector umstellen (Entscheidung 2026-10-13; Claude hatte SQLite + Vektorsuche empfohlen).
- Betroffene Dateien: `server/postgres/postgres-einrichten.sh` (neu).
- Änderung: Sudo-Skript installiert `postgresql`, `postgresql-18-pgvector`, `python3-psycopg`, legt DB `vault`, Benutzer `vaultq` und die Erweiterungen `vector`, `unaccent` an. Passwort nur in `/etc/ma-home/vaultq.pgpass`.
- Prüfung: `bash -n` fehlerfrei. Paketkandidaten per `apt-cache` belegt (postgresql 18+290ubuntu1, postgresql-18-pgvector, python3-psycopg 3.3.2). Skript NICHT ausgeführt, nichts installiert.
- Ergebnis: `vault-q` (SQLite) unverändert. Nächste Schritte: Skript durch Philipp, dann `vault-pg.py` und Embedding-Modell (Ollama fehlt noch).
- Rückweg: Skript löschen; nach Ausführung `sudo -u postgres dropdb vault; dropuser vaultq` und Pakete entfernen.

## 2026-10-13 – Sudo-Freigabe: pauschaler Admin-Haken (Entwurf, nicht eingespielt)

- Auftrag: Philipp will einen pauschalen Haken, mit dem Claude Sudo-Skripte selbst ausführen kann (Entscheidung Philipp; Claude hatte Freigabe pro Skript empfohlen).
- Betroffene Dateien: `server/auto-deploy/ma-sudo-run.sh`, `sudo-anfordern.sh`, `sudo-einrichten.sh`, `patch-portal-sudoswitch.py` (alle neu); `portal-ui/web/app.js` (zweiter Haken `#csudo` mit Bestätigungsdialog), `sw.js` (Version 2026-10-13-4); `scripts/server-sync/paritaet-check.py` (neue Zeile).
- Änderung: Schalterdatei `/srv/ma-home/deploy-schalter/sudo-erlaubt` (Route `/api/deploy/sudo-switch`, nur Admin). Mit Schalter führt der Root-Dienst `ma-sudo` das von andrew in `/srv/ma-home/deploy-sudo/` abgelegte `*.sh` aus: erst Kopie in root-eigenes Temp, Syntaxprüfung, Archiv mit SHA-256 in `/var/log/ma-sudo/`, Ergebnis in `ergebnis.txt`. Ohne Schalter: Status „AUS“.
- Prüfung: `bash -n` für alle drei Skripte fehlerfrei. `py_compile` des Patches und die JS-Syntax von `app.js` NICHT geprüft (Bash-Befehl verweigert, kein `node` auf dem Server). Nichts installiert oder ausgeführt.
- Sicherheit: Mit gesetztem Haken laufen Skripte von andrew als root. Haken weg oder `sudo systemctl disable --now ma-sudo.path`.
- Offen: `sudo bash ~/MA-Server/server/auto-deploy/sudo-einrichten.sh`, dann `deploy-ui.sh`; Drop-in für die Claude-Brücke gilt erst nach deren Neustart.
- Rückweg: siehe Kopfzeilen von `sudo-einrichten.sh`; Haken in `app.js` per Dateiversionierung zurücknehmen.

## 2026-10-13 – Sudo-Brücke in Betrieb, PostgreSQL läuft, Portal-Oberfläche eingespielt (Server-Kopie, live)

- Auftrag: Rechte-Probleme des Chat-Prozesses lösen und die offenen Schritte aus der Übergabe ausführen.
- Befund: Der Chat-Prozess läuft als `andrew` mit Hauptgruppe `ma-web`, nicht `andrew`. `/srv/ma-home/deploy-sudo` (`root:andrew`, `1775`) war deshalb nicht beschreibbar (`Permission denied`), ebenso `/etc/ma-home/vaultq.pgpass`. Nicht behoben: `/srv/ma-home/deploy-schalter` ist `root:ma-web` `0775`, der Chat könnte die Admin-Haken selbst anlegen (nicht genutzt). Vorschlag: root-only, sobald klar ist, welcher Dienst die Haken schreibt.
- Neue Dateien: `server/auto-deploy/rechte-fix.sh` (Gruppe `ma-web` für `deploy-sudo`; von Philipp ausgeführt, Wirkung indirekt belegt), `server/auto-deploy/deploy-ui-bruecke.sh` (Wrapper, weil die Sudo-Brücke nur ein einzelnes Skript kopiert und `deploy-ui.sh` den Ordner `web/` braucht), `server/postgres/pgpass-gruppe.sh` (Passwortdatei für `ma-web` lesbar), `server/claude-bridge/bridge-nur.sh` (nur die Brücke installieren, Neustart verzögert), `scripts/vault-pg.py` (siehe unten).
- Belegt: PostgreSQL 18.6, pgvector 0.8.1, `listen_addresses=localhost` (Ausgabe von `postgres-einrichten.sh`, über die Sudo-Brücke gelaufen). Portal-Oberfläche 2026-10-13-4: Prüfsummen `app.js` und `sw.js` in `/opt/ma-home/web` gleich dem Projekt, Portal intern HTTP 200, Sicherung `/opt/ma-home/web.bak-20261013-150438` (ein erster Lauf scheiterte vor dem Installieren und ließ eine weitere unbenutzte Sicherung zurück).
- `scripts/vault-pg.py`: Index in PostgreSQL (`tsvector`/GIN deutsch, Spalte `emb vector(768)` angelegt, leer). Befehle `sync [--voll]`, `search`, `show`, `links`, `stats`; nutzt Parser und Zonen von `vault-q.py`. Geprüft: Vollabgleich 655 Dateien in rund 53 s (501 Vault, 152 Projekt, 2 Bibliothek; 3629 Links, 621 Tags), inkrementeller Lauf 0,4 s, zweiter gleichzeitiger `sync` wird per Advisory-Lock übersprungen, Suche läuft währenddessen. Nicht umgesetzt: Ordnergewichte und `qlog` von `vault-q`, Embeddings (Ollama fehlt), Timer für `sync`. Die Rangfolge unterscheidet sich von `vault-q`.
- Verbindungen-Reiter (502): Ursache laut Code: `portal.py` wartet auf die Brücke nur 15 s (`sock.settimeout(15)`), `connectors_status()` rief `claude mcp list` mit bis zu 60 s Wartezeit auf. Änderung in `ma-claude-bridge.py`: Antwort aus Zwischenspeicher, Auffrischen im Hintergrund, ohne Daten höchstens 10 s warten (Meldung „Verbindungen werden noch geprüft“). Die Dauer von `claude mcp list` wurde NICHT gemessen (Aufruf nicht freigegeben). Brücke installiert (Prüfsumme gleich) und um 15:20:02 neu gestartet, danach „bereit“. Ob der Reiter jetzt lädt: NICHT geprüft.
- Offen: Handy-Test des Bilder-Knopfs (App neu öffnen), sonst App neu bauen (B15); Timer für `vault-pg sync`; Embedding-Modell; `deploy-schalter` absichern; Sudo-Haken wieder aus (`sudo systemctl disable --now ma-sudo.path`).
- Rückweg: Brücke `sudo cp /usr/local/lib/ma-claude-bridge.py.bak /usr/local/lib/ma-claude-bridge.py && sudo systemctl restart ma-claude-bridge`; Oberfläche: Anleitung in der Kopfzeile von `deploy-ui.sh`; PostgreSQL siehe Eintrag oben.

## 2026-10-13 – vault-pg: Ordnergewichte, Anfrageprotokoll, Timer (Server-Kopie, live)

- Auftrag: offene Punkte aus der Übergabe (Gewichte, `qlog`, Timer für `sync`).
- `scripts/vault-pg.py`: Gewichte wie `RANK` in `vault-q.py` (Archiv 0,35, Chat-Importe 0,5, Schmejd/Crimson Zone/Arduino 0,4, `_Claude-Memory` und Technik 1,3), angewandt nach der Abfrage auf die ersten `3·n` Treffer. Tabelle `qlog` und Befehl `report` (aus mit `MA_VQ_NOLOG=1`). Geprüft: Suche mit Treffern, ohne Treffer, `report` zeigt die Anfragen. Die Rangfolge wurde NICHT gegen `vault-q` verglichen, und der Gewichtungseffekt wurde nicht gemessen.
- Neu: `server/postgres/vault-pg-timer.sh` (`ma-vault-pg-sync.timer`, alle 10 Min, Benutzer `andrew`, Gruppe `ma-web`). Über die Sudo-Brücke ausgeführt; erster Lauf Status 0/SUCCESS, nächster Lauf 15:44 UTC angezeigt.
- Rückweg: `sudo systemctl disable --now ma-vault-pg-sync.timer; sudo rm /etc/systemd/system/ma-vault-pg-sync.{service,timer}`. Kopfzeile des Skripts enthält dasselbe.
- Offen: Embeddings (Ollama fehlt), Parität auf dem PC (`vault-pg` dort nicht vorhanden), `report` ohne Wortauswertung.

## 2026-10-13 – vault-pg am PC (Paritaet) (PC-Kopie)

- Auftrag (Philipp): `vault-pg` muss am PC gleich verfuegbar sein.
- Entscheidung: kein zweites PostgreSQL am PC. `scripts/vault-pg.cmd` ruft per SSH dasselbe `vault-pg.py` auf dem Server auf; PC und Server liefern damit dieselben Treffer, und das Datenbankpasswort (`/etc/ma-home/vaultq.pgpass`) bleibt auf dem Server. Der Index wird weiter nur dort aktualisiert (Timer, Server ist Hauptkopie des Vaults).
- `paritaet-check.py`: `vault-pg.py` in `FILES` aufgenommen.
- Geprueft 2026-10-13: nach `sudo usermod -aG ma-web andrew` liefert `vault-pg search` und `stats` vom PC dieselben Treffer wie auf dem Server. Die Weitergabe der Argumente macht `scripts/vault-pg-pc.py` (shlex-Quoting, sonst zerfallen Suchbegriffe mit Leerzeichen).
- Rueckweg: `scripts/vault-pg.cmd` loeschen; Gruppe mit `sudo gpasswd -d andrew ma-web` entfernen.

## 2026-10-13 – git-sync aktiv: Server pusht auf GitHub-Zweig server-live (Server-Kopie, live)

- Belegt: Login mit dem Deploy-Key an `xSuice/Claude` ("successfully authenticated"), `git-sync.py init` (Fetch `main` ok), erster `run`: Commit und Push auf `server-live` ok (53 Dateien). Timer `ma-git-sync.timer` alle 15 Min über die Sudo-Brücke eingerichtet, erster Lauf Status 0/SUCCESS.
- Befund: Viele Dateien unterscheiden sich zu `main` nur im Zeilenende (PC CRLF, Server LF) oder im Dateimodus. Fix in `git-sync.py`: nur echte Inhaltsänderungen committen (`--ignore-cr-at-eol`); im Server-Repo `core.fileMode=false`. Der erste Commit enthält trotzdem rund 50 Dateien mit 0 Zeilenänderung (nur Modus), harmlos.
- Nicht geprüft: Ob der Timerlauf ohne Terminal auch pusht (Status 0, aber keine Ausgabe gelesen); Zusammenführung `server-live` → `main` am PC; Umstellung von `claude-abgleich.py` und `paritaet-check.py` auf Commit-Stände.
- Offen: PC holt `server-live` per `git fetch` und führt bewusst zusammen; `claude-abgleich.py` am PC danach anpassen, damit beide Wege sich nicht überschneiden.
- Rückweg: `sudo systemctl disable --now ma-git-sync.timer; sudo rm /etc/systemd/system/ma-git-sync.{service,timer}`; Deploy-Key in GitHub löschen, `rm -r ~/.config/ma-github`.

## 2026-10-13 – Abgleich-Bericht kürzer, spart Tokens (Server-Kopie)

- Auftrag: Philipp will weniger Tokenverbrauch; `Dienste/Server-Abgleich.md` war rund 600 Zeilen lang und wird bei jedem Lesen komplett geladen.
- Datei: `scripts/server-sync/claude-abgleich.py`, Funktion `write_report`. Läuft am PC, die Änderung wirkt erst nach dem nächsten Abgleich (bei Änderung auf beiden Seiten entsteht `.server-konflikt`).
- Änderung: nur die letzten 12 statt 48 Einträge; geholte und gesendete Dateien als eine Zeile mit höchstens 5 Namen und "(+N weitere)"; höchstens 3 verschiedene Claude-Sitzungen, Startsatz auf 60 Zeichen gekürzt.
- Geprüft: Testlauf mit `/tmp/ma-test/test_report.py` (Skript wird geladen, `write_report` 15-mal mit Testdaten): genau 12 Einträge, 115 Zeilen, Dateiliste "(9): a0..a4 (+4 weitere)", doppelter Sitzungsstart nur einmal. Nicht geprüft: Lauf am PC mit echten Daten.
- Rückweg: Die drei Änderungen in `write_report` zurücknehmen (`git diff` zeigt sie), `blocks[:12]` wieder auf `blocks[:48]`.

## 2026-10-13 – Portal-Chat: Kontextfenster-Balken, Authelia-Diagnose geschwärzt (Server-Kopie, noch nicht eingespielt)

- Auftrag: Philipp will im Portal-Chat eine Anzeige wie in Claude Desktop (Kontextfenster mit Balken, Sitzungs- und Wochenlimit).
- Änderung: `portal-ui/web/app.js` (`tokRender`) zeigt "Kontextfenster 204k / 200k (100 %)" mit Balken, darunter Sitzungsverbrauch; Fenster 200k, bei Modellnamen mit `1m` 1 Mio. `style.css`: Klassen `.ctokh`, `.ctokbar`. Version in `app.js` und `sw.js` auf 2026-10-13-5.
- Nicht gebaut: Sitzungs- und Wochenlimit in Prozent. Im Stream des Servers (`claude -p`) ist dafür kein Ereignis belegt (Suche in den Protokollen ohne Treffer); ohne Datenquelle würde die Anzeige erfunden. Fenstergröße des Server-Modells ist nicht belegt (200k angenommen).
- Nicht geprüft: Syntax und Darstellung. `node` fehlt auf dem Server, kein Browsertest. Einspielen mit `deploy-ui.sh` (Sudo).
- Fund: `ma-authelia-diag2.sh` hat Geheimnisse NICHT geschwärzt (Konfig liegt als JSON, das Muster erwartete keine Anführungszeichen). `/home/andrew/ma-authelia-diag2.txt` (0600) enthält jwt_secret, session secret, storage encryption_key und Passwort-Hashes im Klartext. Muster im Skript korrigiert und an Testwerten geprüft; die Datei selbst und die Geheimnisse sind nicht angefasst.
- Rückweg: `git diff` zeigt die Änderungen an `app.js`, `style.css`, `sw.js`; Versionen zurücksetzen.

## 2026-10-13 – Authelia: Skript für Passkey und Schlüsseltausch (Server-Kopie, nicht gelaufen)

- Neu: `scripts/ma-authelia-haerten.sh` (`sudo bash ... passkey` schaltet WebAuthn und Passkey-Login ein; `... rotate` tauscht Session- und Reset-Schlüssel und fragt optional nach neuen Passwörtern). Beide sichern die Konfiguration, prüfen mit `authelia validate-config` und stellen bei Fehler die Sicherung zurück. `storage.encryption_key` bleibt unverändert (Wechsel braucht eine Datenbank-Migration).
- Geprüft: nur `bash -n`. Nicht geprüft: Lauf; die Schlüssel `enable_passkey_login` und `selection_criteria` unter webauthn stammen aus dem Gedächtnis für v4.39, die Prüfung vor dem Neustart fängt Fehler ab.
- Erledigt: `/home/andrew/ma-authelia-diag2.txt` (enthielt Geheimnisse im Klartext) gelöscht, Löschung belegt (`ls` meldet "No such file"). Die Werte stehen weiter im Chatprotokoll; daher `rotate` empfohlen.
- Rückweg: Sicherungen `configuration.yml.bak-<Zeit>` und `users.yml.bak-<Zeit>` zurückkopieren, `docker restart ma-home-authelia-1`.
- Gelaufen 2026-10-13 16:07 und 16:08 über die Sudo-Brücke: `passkey` (Prüfung "parsed and loaded successfully", Neustart, `/auth/api/health` = OK) und `rotate ohne-passwort` (Session- und Reset-Schlüssel neu, Sicherungen `*.bak-20261013-160808`, Health OK). Passwörter wurden nicht geändert (Modus ohne Passwort), Passkey noch nicht angelegt, Anmeldung mit Passkey nicht getestet.

## 2026-10-14 – Portal: Reiter "Einstellungen", Stufe 1 (Server-Kopie, noch nicht eingespielt)

- Auftrag: Philipp will Passkey und weitere Einstellungen in einem eigenen Reiter im Portal.
- Dateien: `portal-ui/web/app.js` (TABS, ICONS, Funktion `einstellungen()`, ROUTES), Version in `app.js` und `sw.js` auf 2026-10-14-1.
- Inhalt: Anmeldung (Hinweis auf Passwort, Code, Passkey, Knopf zu `/auth/settings`, dort legt Authelia Passkeys und Codes selbst an), Claude-Chat (Grenze für "neuer Chat", fest 200 000), Portalversion und Rolle. Keine neue API-Route, kein neuer Root-Weg.
- Bewusst nicht gemacht: Admin-Schalter verschieben (der Code im Reiter Claude greift per ID `#cdep`/`#csudo` zu, ein Verschieben ohne Umbau würde ihn zum Absturz bringen); Knöpfe mit Root-Wirkung (Stufe 2, braucht eine Prüfung durch Philipp).
- Nicht geprüft: Syntax und Darstellung (`node` und Browser fehlen auf dem Server). Die Aussage "Passwort und Code (TOTP) sind eingerichtet" stammt aus der Konfiguration, nicht aus einem Test der Anmeldung.
- Einspielen: `deploy-ui.sh` (Sudo). Danach im Browser Reiter "Einstellungen" und "Claude" öffnen.
- Rückweg: `git diff` zeigt die Änderungen; Version zurücksetzen.

## 2026-10-14 – Portal: Limit-Ereignis im Chat, Text im Reiter Einstellungen korrigiert (Version 2026-10-14-3)

- Auftrag: Sitzungs-/Wochenlimit im Claude-Reiter anzeigen; Screenshot der Einstellungen geklärt.
- Betroffene Dateien: `portal-ui/web/app.js`, `portal-ui/web/sw.js`.
- Änderung: `rate_limit_event` aus dem Datenstrom wird gelesen und unter dem Kontextbalken angezeigt (`rlRender`); Text im Reiter Einstellungen korrigiert (TOTP-Behauptung war ungeprüft, Hinweis auf Menü Sicherheit ergänzt).
- Prüfung: Syntax mit esprima geprüft (Kopie mit ES2020-Operatoren ersetzt). Verhalten im Browser nicht geprüft. Die Limit-Anzeige liefert laut Philipp keine Werte; belegt sind in den Protokollen nur rejected-Ereignisse mit status, resetsAt, rateLimitType.
- Rückweg: `/opt/ma-home/web.bak-*` (letzte Sicherung vor diesem Stand: 20261014-043154).
- Offen: Quelle für Prozentwerte (wie die Claude-App) unbekannt; Weg über Anmelde-Token nur mit Freigabe von Philipp.

## 2026-10-14 – Portal: Sitzungs- und Wochenlimit automatisch im Claude-Reiter (Version 2026-10-14-4)

- Auftrag: Anzeige wie in der Claude-App (Sitzung 5 Std., Woche) immer automatisch.
- Betroffene Dateien: `server/claude-bridge/ma-claude-bridge.py` (plan_usage, Antwort von `jobs` um `plan` ergaenzt), `portal-ui/web/app.js` (planRender, ersetzt den Weg ueber rate_limit_event), `portal-ui/web/sw.js`.
- Aenderung: Die Bruecke fragt alle 120 s `https://api.anthropic.com/api/oauth/usage` mit dem Token von andrew ab (undokumentierte Schnittstelle, nur Prozent und Reset werden gespeichert, das Token nie ausgegeben). Das Portal liest `plan` aus der `jobs`-Abfrage (alle 4 s, solange der Reiter Claude offen ist).
- Pruefung: Syntax von app.js (esprima, Kopie) und Bruecke (py_compile) ok. Probe `usage-probe.py` am 2026-10-14 06:49: five_hour 22 %, seven_day 25 %, Woche stimmt mit der Claude-App ueberein. Anzeige im Browser noch nicht geprueft.
- Rueckweg: Bruecke `sudo cp /usr/local/lib/ma-claude-bridge.py.bak /usr/local/lib/ma-claude-bridge.py && sudo systemctl restart ma-claude-bridge`; Portal `/opt/ma-home/web.bak-*`.
- Risiko/Offen: Schnittstelle kann sich aendern; Token laeuft ab (wird beim naechsten Chat erneuert), dann zeigt die Anzeige einen Hinweis. Paritaet: noch nicht am PC, Abgleich ueber ClaudeAbgleich.

## 2026-10-14 – Portal: Label der Sitzungsanzeige gekürzt (noch nicht eingespielt)

- Auftrag: Im Handy-Screenshot brach „Sitzung (5 Std.)“ auf drei Zeilen um.
- Aenderung: `portal-ui/web/app.js` (planRender), Label „Sitzung (5 Std.)“ zu „Sitzung 5h“.
- Pruefung: nur Textaenderung, nicht im Browser geprueft. Einspielen mit `deploy-ui.sh` (Sudo-Bruecke) steht aus.
- Rueckweg: Label zurueckaendern. Paritaet: Abgleich ueber ClaudeAbgleich (BACKLOG B33).

## 2026-10-14 – Kontext-Wächter-Hook für den Server (nur im Projekt, noch nicht aktiv)

- Auftrag: Server-Chat meldet große Sitzungen wie der PC (Übergabe-Schritt 4).
- Dateien: neu `server/claude-config/hooks/kontext-waechter.py`; `server/claude-config/settings.json` (zweiter UserPromptSubmit-Hook neben council-auto.py).
- Verhalten: liest Token der letzten Antwort aus `transcript_path`; ab 250 000 Hinweis, ab 300 000 Auftrag `/uebergabe`; Abschalten mit „ohne waechter“; bei Fehlern still (Exit 0).
- Pruefung: Testlauf mit künstlichen Transcripts (100k: keine Ausgabe, 260k: Warnung, 310k: Übergabe, „ohne waechter“ und fehlende Datei: still); settings.json ist gültiges JSON. Nicht in einer echten Sitzung getestet.
- Offen: Einspielen nach `~/.claude/hooks/` und `~/.claude/settings.json` (Abgleich oder Installer); ob die Brücke `transcript_path` an Hooks liefert, ist ungeprüft.
- Rueckweg: Eintrag in settings.json entfernen, Datei löschen. Paritaet: PC hat eigenen Wächter.

- Nachtrag 2026-10-14: Hook und settings.json nach ~/.claude eingespielt (settings.json gleich der Projektkopie, Testlauf mit 310k-Transcript ok). Wirkt ab dem nächsten neuen Chat.

## 2026-10-14 – KI-Effizienz V5: Bestandsaufnahme, Wirkungsregister, zwei kleine Änderungen (Server-Kopie, live)

- Auftrag: V5-Recherche auf das bestehende Setup anwenden, nur belegte Wirkung eintragen. Register: Vault `30 Technik/MA-Server/Wirkungsregister-KI-Setup.md`.
- `scripts/vault-q.py`: Notizen mit `status` veraltet/ungueltig/zurueckgezogen werden im Rang auf 0,3 abgewertet (Eintrag 275). Geprüft an einem Testpaar (Plan Port 8080 veraltet, Beobachtung Port 3000): vorher stand die veraltete Notiz vorn, nachher die Beobachtung; `--status gueltig` unverändert. Goldstandard `vault-q-gold.py`: 18/20 Treffer@5 wie vorher. Testnotizen gelöscht. Rückweg: `vault-snapshots/wissen-vor-umbau-20261013-0921/vault-q.py.vor-veraltet`. PC-Kopie über ClaudeAbgleich.
- `kontext-waechter.py` (`~/.claude/hooks` und `server/claude-config/hooks`, gleich): schreibt `~/.claude/waechter.log` (Zeit, Tokenzahl oder „kein transcript_path“, nie Text), damit B34 belegbar wird. Geprüft mit echtem Transcript (130k, keine Warnung) und ohne Pfad. Nicht geprüft: Lieferung durch die Brücke (erst im nächsten Portal-Chat sichtbar).
- Nicht umgesetzt (kein Beleg für Nutzen oder keine Freigabe): Router, Embeddings, neue Regeldatei (Doppelung zu TASK-POLICY), die 12 Vergleichsaufgaben.
- Nachtrag 2026-10-14 (V5 komplett erneut gelesen, alle 1337 Zeilen): `scripts/vault-pg.py` an `vault-q` angeglichen: `--art`, `--status`, Abwertung veraltet/ungueltig/zurueckgezogen auf 0,3 (Eintrag 275/276). Geprüft: Suche mit und ohne `--status` läuft, Wirkung der Abwertung am Testpaar **nicht** geprüft (Index braucht Sync). Rückweg: `vault-snapshots/wissen-vor-umbau-20261013-0921/vault-pg.py.vor-status`. `LESSONS-LEARNED.md`: Feld „Schicht“ in der Vorlage (Eintrag 175/272). `BACKLOG.md` B34: `transcript_path` bestätigt (waechter.log 142k bis 243k).
- Nachtrag 2: `vault-pg` Abwertung am Testpaar **geprüft** (Pgtestdienst: gültig 0,10, veraltet 0,03 = Faktor 0,3); nach Löschen der Testnotizen und Sync „Keine Treffer“ (M6 für vault-pg bestanden). Beobachtung (nicht geändert): Bei UND-Treffern unter 3 fällt die Suche auf ODER zurück und überschreibt die UND-Treffer, daher fehlten die Testnotizen bei Mehrwort-Suchen. `~/.claude/CLAUDE.md` Regeln 12 und 13 gekürzt (Pfad nur noch über `ask.py --help`), Sicherung `vault-snapshots/wissen-vor-umbau-20261013-0921/CLAUDE.md.vor-kuerzen`. Die PC-Kopie dieser Datei ist davon getrennt.
- Nachtrag 3 (2026-10-14): `scripts/vault-pg.py` Mehrwort-Suche: Die UND-Treffer wurden nicht mehr überschrieben (Beobachtung aus Nachtrag 2 war schon behoben), standen aber hinten, weil die Ränge von UND- und ODER-Durchlauf gemeinsam sortiert wurden (UND-Ränge viel kleiner; mit Standard `-n 8` fielen sie heraus). Jetzt wird je Durchlauf sortiert, UND-Treffer bleiben vorn. Geprüft: „Startprompt Hooks Connector“ liefert Übergabe und Wirkungsregister auf Platz 1 und 2 (vorher Platz 22 und 24 bei `-n 30`, bei `-n 8` fehlend); Einwort-Suche „Startprompt“ unverändert. Nicht geprüft: weitere Mehrwort-Fälle, Filter `--art`/`--status`, Zone `alle`. Rückweg: `scripts/vault-pg.py.vor-und-vorrang`. PC-Kopie von `vault-pg.py` noch nicht angeglichen (Parität: in BACKLOG eintragen).

## 2026-10-14 – KI-Setup (Startprompt): Hooks, Connectoren, Gedächtnis-Link, Regeln (Server, live)

- Auftrag: Autonomer Startprompt plus Auftrag Hooks/Skills/Tools.
- Dateien: `server/claude-config/hooks/{council-auto,kontext-waechter,ma-guard}.py`, `server/claude-config/settings.json` (deny für 8 Connectoren), `server/claude-config/CLAUDE.md`, `server/claude-config/server-abschnitt.md` (Server-Ergänzungen zu Regel 4, 6, 11 und Gedächtnis-Link), `CLAUDE.md` (Vault-Suche eingegrenzt); live gleich in `~/.claude`; Agent `docs-lookup` deaktiviert (braucht Context7, nicht vorhanden); Symlink `~/.claude/projects/-home-andrew-MA-Server/memory` auf Vault `_Claude-Memory/Auto-Memory`.
- council-auto: Texte über 1500 Zeichen lösen nur bei dem Wort Council aus; "sinnvoll" nur als "ist/wäre das sinnvoll". Anlass: Die Startprompt-Datei (5958 Zeichen) und "Wie ist das Wetter, sinnvoll, eine Jacke?" lösten fälschlich aus. 5 Testfälle.
- kontext-waechter: Stufe nur einmal je Sitzung (neu nach +50k), nur Transcript-Ende, Sidechain ignoriert, Log begrenzt, Zustand atomar in `~/.claude/state/`. 10 Testfälle.
- ma-guard: unlesbare Eingabe gibt Exit 2 (fail-closed), 5 Testfälle. Restrisiko: Formatänderung von Claude Code sperrt alle MCP-Aufrufe.
- Connectoren Vercel, Figma, Canva, Supabase, Linear, Postman, vidIQ, Jam per `permissions.deny` ausgeblendet (in 237 Sitzungen nie genutzt). Start-Kontext einer leeren Haiku-Sitzung 41 999 -> 37 075 Token (Einzelmessung).
- Gedächtnis: neue Sitzung nannte die Entscheidung Variante 2 aus dem Index (M1).
- **Befund 06:43:** `claude-abgleich.py` (PC) hat `CLAUDE.md`, `settings.json`, `ma-guard.py`, `council-auto.py` und `docs-lookup.md` auf dem Server mit dem alten PC-Stand überschrieben (push_config nimmt PC-Repo-Stand). Am Server aus dem Repo wieder eingespielt, alle fünf Dateien gleich Repo. Solange der PC `server-live` nicht geholt hat, droht erneutes Überschreiben (BACKLOG B35).
- Rückweg: Backups in `~/.claude/backups/2026-10-14-ki-setup/`; deny-Zeilen löschen; Symlink entfernen und Ordner anlegen; `docs-lookup.md.disabled` zurückbenennen.

## 2026-10-15 – JARVIS V16 im Portal (Reiter JARVIS, im Repo, noch nicht eingespielt)

- Auftrag: JARVIS als Hauptoberfläche ins vorhandene Portal einbauen, kein zweites Dashboard, gleiche Steuerung wie CLI und PC-Client.
- Dateien: `server/claude-bridge/ma-claude-bridge.py` (Op `jarvis`, Zulassungsliste, Benutzerzuordnung), `portal-ui/patch-portal-jarvis.py` (neu, Route `/api/jarvis`, nur Admin), `portal-ui/deploy-ui.sh` (ruft den Patch auf), `portal-ui/web/app.js` und `sw.js` (Reiter JARVIS, Version 2026-10-14-5), `tests/portal_smoke.py` (vier neue Prüfungen), `docs/jarvis/PORTAL.md` (neu). Server: `~/.config/ma-jarvis/portal-users.json` (andrew -> jarvis.json).
- Änderung: Aufträge starten, Fortschritt, Freigabe, Abbrechen, Ergebnisdateien im vorhandenen Betrachter, Not-Aus, Fähigkeiten und Gelerntes. Abfrage nur bei offenem Reiter und laufendem Auftrag. V16-Kern unverändert.
- Prüfung: `jarvis_api` gegen den echten Kern am Server (list, status, usage, fremder Benutzer, ungültige ID, unbekannter Befehl); Portal-Patch an einer Kopie von `portal.py` (idempotent, kompiliert); Browser-Rauchtest 82/82 mit Platzhalter-Antworten. Nicht geprüft: echter Lauf durch Portal und Brücke, Freigabe eines echten Auftrags, Bridge-Sandbox gegen `submit`.
- Ergebnis: Code fertig im Repo. Einspielen braucht sudo (Schritte in `docs/jarvis/PORTAL.md`).
- Rückweg: `portal.py.bak-<Zeit>`, `web.bak-<Zeit>` und `/usr/local/lib/ma-claude-bridge.py.bak` zurückkopieren; `portal-users.json` löschen.

## 2026-10-15 – JARVIS V16: eingespielt, Herkunftskennzeichnung (Nachtrag)

- Auftrag: Gesamtauftrag `MA-Home-JARVIS-V16-Gesamtauftrag-2026-10-15.md` (Phasen A bis D umgesetzt, E bis I offen).
- Eingespielt (belegt): Brücke mit Op `jarvis` und Portal-Oberfläche per Sudo-Freigabe (`/srv/ma-home/deploy-sudo/ergebnis.txt`: OK, Sicherungen `ma-claude-bridge.py.bak`, `/opt/ma-home/web.bak-20261015-020401` und `-024119`). Kern-Release `20261015-023846-c6e404c` über `install-v16.sh --no-cron` (Status `tests-ok`).
- Neu: `server/jarvis/core/brain-runtime/attribution.py` (reine Funktion: `Jarvis:`, `Claude:`, `Jarvis + Claude:` nur aus Schritten, Modellaufrufen und Ereignissen; sonst `Ausführung nicht verifiziert`), Einbindung in `taskengine.py` (Statusfeld `attribution`, Ereignis `attribution`, Zeile am Ende von `BERICHT.md`), Anzeige in `portal-ui/web/app.js` (Version 2026-10-15-1, kein neuer Tab), `tests/test_v16_attribution.py` (14 Tests), `tests/portal_smoke.py` (1 Prüfung mehr).
- Prüfung: 310 Tests am Server grün (4 übersprungen, brauchen root); Browser-Rauchtest 83/83; echter Auftrag `j20261015-864ffc` (Bridge-Sandbox `submit` ok) und `j20261015-25b832` (Kennzeichnung im Status, Ereignisprotokoll und Bericht).
- Nicht geprüft: Kennzeichnung `Jarvis:` ohne Claude nur mit konstruierten Statusdaten, nicht mit der echten Engine; `Claude:` nur als Funktion, noch nicht im Claude-Chat; neuer Wortlaut und Anzeige im Reiter nicht an einem frischen echten Auftrag im Browser; `approve` live; Cron-Zeile nicht lesbar (Auftrag lief trotzdem im Takt).
- Falle: Staging für die Tests braucht das volle Release-Layout (`brain-runtime` neben `dropin-beispiele`), sonst 30 falsche Fehler. Hintergrundläufe abgekoppelt starten (`setsid nohup`), sonst stirbt der Lauf mit der Sitzung.
- Rückweg: `bash server/jarvis/rollback-v16.sh --to <früherer Release>`; Oberfläche `web.bak-<Zeit>` zurückkopieren.

## 2026-10-15 – JARVIS V16: Rollback auf früheren Release getestet (Nachtrag 2)

- Test am echten Betrieb: `rollback-v16.sh --to 20261014-172944-local` (tests-ok) -> `doctor ok` -> Auftrag `j20261015-325110` auf dem alten Release bis `done`, Statusfeld `attribution` dort nicht vorhanden (belegt den alten Code) -> `--to 20261015-023846-c6e404c` -> `doctor ok`, alle 7 Aufträge erhalten. Protokoll: `~/tmp/rollback-test.log`.
- Befund: Aufträge, die ein Release ohne `job_calls`-Protokoll ausgeführt hat, bekommen nach dem Wiederherstellen `Ausführung nicht verifiziert · Grund: 0 Modellaufrufe, aber 2 Ereignisse`. Das ist gewollt (keine Kennzeichnung ohne Nachweis), gilt aber auch für alle Aufträge vom 14.10. und früher.
- Offen: Rollback bei laufendem Auftrag mitten im Schritt und Rückkehr bei defekter Datenbank nicht getestet.
