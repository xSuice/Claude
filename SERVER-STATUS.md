# MA Home – zuletzt belegter Projektstand

## Aktuell live geprüft: 2026-10-18, Europe/Berlin

Quelle: neue SSH-Inventare und read-only Code-Fingerprints im Workspace `Hermes-Engineering-2026-10-17/reports/`. Kein sudo, kein Produktions-DB-Inhalt, keine Dienständerung.

- SSH als andrew auf ma-server erfolgreich; Ubuntu 26.04.1, Kernel 7.0.0-38, Python 3.14.4, Celeron N2840/2 CPUs, 3,21 GiB RAM.
- Portal-Health HTTP 200, PostgreSQL 18/main online und nur localhost:5432; ma-home-web/-agent/-terminal, Docker und SSH aktiv. Dies ist kein vollständiger Portal-/Job-Funktionstest.
- Aktives JARVIS: `~/.local/share/ma-jarvis/current` -> `releases/20261015-140650-f57d32f`; Cron referenziert current, KILL nicht vorhanden. 104 verglichene Codedateien passen exakt zu GitHub server-live / `70a6fd0`, nicht zu main / `72e1607`.
- Server-Repo `~/MA-Server`: HEAD `70a6fd0`, 7 bestehende getrackte Änderungen; nicht überschrieben. Aktives Release ist keine Git-Arbeitskopie.
- Docker-Containerinventar mangels Socket-Rechten blockiert. Datenbankinhalte, private Holdouts, Live-Modellqualität, vollständige Recovery und Browserablauf nicht neu geprüft.
- 20 ausgewählte bestehende V16-Regressionen mit synthetischen Modellantworten in RAM-/Netzwerk-Isolation grün; kein Ersatz für die gesamte frühere 294/310-Test-Suite. Produktionscode und Dienste unverändert.

Ältere Befunde folgen unverändert; sie gelten nur mit ihrem jeweiligen Beobachtungsdatum. Aktuelle Integrationsgrenzen: `docs/jarvis-omega/M1A-LIVE-INTEGRATION.md`.

Stand: 2026-10-05, Europe/Berlin. Keine aktuelle Live-Diagnose verfügbar. Diese Datei beschreibt die Beleglage und ersetzt keine Serverprüfung.

## Quellen und Belegstatus

- Quelle A: `AGENTS.md`, Version 2026-10-04. Enthält historischen Gesprächskontext; der ursprüngliche Messzeitpunkt der Serverangaben ist nicht angegeben. Am 2026-10-05 gelesen, nicht live bestätigt.
- Quelle B: Nutzerentscheidungen und bereitgestellte Anleitungen in diesem Chat am 2026-10-05. Keine Ausführungsausgaben zur Installation oder Diagnose erhalten.
- „Historisch“: aus früheren Angaben übernommen. „Offen“: noch zu prüfen. „Lokal geprüft“: Prüfung außerhalb des Heimservers. „Live bestätigt“ nur mit tatsächlichem Serverbeleg und Datum verwenden.

## Ziel und aktuelle Entscheidung

- Bestehendes MA Home auf Ubuntu gezielt reparieren und weiterentwickeln. Sicherheit, Datenbestand und geringe Ressourcenlast priorisieren. Kein OS-Wechsel, kein Cloudflare. Quelle A; Projektregel.
- Codex soll auf dem Windows-PC installiert werden. Quelle B; Nutzerentscheidung vom 2026-10-05. Installation und Serververbindung offen.
- Änderungen und Erkenntnisse sollen dokumentiert werden. Quelle B; Auftrag vom 2026-10-05. Dokumente erstellt; Übertragung zum PC/Server offen.

## Historische Systemangaben – vor Eingriffen prüfen

| Bereich | Letzte Angabe | Beleglage |
|---|---|---|
| System | Ubuntu 26.04.1 LTS, x86_64 | Quelle A; historisch, Version offen |
| Hardware | Celeron N2840, 2 logische CPUs, ca. 4 GB RAM, HDD | Quelle A; historisch |
| SSH / LAN | andrew@192.168.0.111; 192.168.0.0/24 | Quelle A; aktuelle Erreichbarkeit offen |
| Domain | ma-server.duckdns.org; ha, ntfy, sync | Quelle A; DNS und HTTPS offen |
| Dienste | Caddy, Authelia, Filebrowser, Home Assistant, ntfy, CouchDB | Quelle A; aktueller Zustand offen |
| Code / Web | /opt/ma-home; /opt/ma-home/web | Quelle A; Existenz, Eigentümer und Rechte offen |
| Konfiguration / Daten | /etc/ma-home; /srv/ma-home | Quelle A; aktueller Zustand offen |
| systemd / Compose | ma-home-web, ma-home-agent; Projekt ma-home | Quelle A; aktive Konfiguration offen |
| DNS-Zusatz | /etc/ma-home-dns; Projekt ma-home-dns | Quelle A; Blocky-Installation offen |
| Drucker | Samsung C480/C48x, 192.168.0.198; IPP zuvor erkannt | Quelle A; Druck und Scan nicht bestätigt |

## Offene Probleme und nächste Prüfungen

| Thema | Befund oder Hypothese | Nächste passende Prüfung |
|---|---|---|
| Oberfläche | Historische JSON-404 über Mobilfunk. Dateirechte unter /opt/ma-home/web sind eine lokal simulierte mögliche Ursache, keine bestätigte Serverursache. Quelle A. | Tatsächlichen Dienstbenutzer, Zugriff auf index.html, Root-Route und Anmeldung prüfen; anschließend ursprünglichen Browserfehler testen. |
| ntfy | Früherer erfolgreicher Reparaturbericht erwähnt. Quelle A; heute nicht geprüft. | Gezielter Dienst-/Anwendungstest, falls für den aktuellen Auftrag nötig. |
| Blocky | Zusatzdatei bereitgestellt; Installation und Nutzung durch Clients nicht bestätigt. Quelle A. | Server-DNS-Antwort und tatsächliches LAN-/WLAN-Client-DNS getrennt prüfen. |
| Backup | Externes Backupziel fehlt laut früherem Bericht. Quelle A; heute nicht geprüft. | Vorhandene Sicherungen, Ziel und Wiederherstellbarkeit ermitteln. |
| Druck/Scan | Geräteerkennung beweist keine Funktion. Quelle A. | Druck oder Scan nur bei entsprechendem Nutzerauftrag testen. |
| Diagnose | Diagnose-Skript bereitgestellt; Syntax lokal geprüft. Quelle B. | Ausgabe vom Server erhalten, dann Tabelle mit Datum und konkretem Beleg aktualisieren. |

## Bekannte Prüfregeln

- HTTP-200 am Healthcheck beweist weder eine funktionierende Startseite noch korrekte Anmeldung.
- Dateirechte unter dem tatsächlichen Dienstkonto prüfen; umask und übergeordnete Verzeichnisse berücksichtigen.
- Mobilfunk und LAN getrennt prüfen; DNS, IPv6, TLS, Proxy und Anwendung unterscheiden.
- Bereitgestellter Code ist keine ausgeführte Änderung. Geräteerkennung ist kein Druck-/Scan-Erfolg.
- Diese Regeln stammen aus Quelle A. Neue Ursachen erst nach Beleg als bestätigte Erkenntnis aufnehmen.

## Dokumentkopien und Übergabe

Führend ist derzeit die hier aktualisierte Projektdokumentation vom 2026-10-05. Dateien gemeinsam in den Windows-Projektordner MA-Home übernehmen. Vor einem späteren Upload nach /opt/ma-home mit vorhandenen Dateien vergleichen und zusammenführen. Automatische Synchronisierung und automatischer Serverzugriff sind nicht eingerichtet.

Für jeden neuen Live-Befund ergänzen: Beobachtungsdatum mit Zeitzone, Quelle/Prüfung, bereinigtes Ergebnis, betroffener Bereich und verbleibende Unsicherheit. Nie Geheimnisse übernehmen.

## Live-Befunde 2026-10-09 (Europe/Berlin), Quelle: SSH `ma-server` als andrew ohne root, PC-Tests

Belegstatus: **live bestätigt** wenn nicht anders vermerkt. Historische Tabelle oben ist damit teilweise überholt.

| Bereich | Befund | Status |
|---|---|---|
| System | Ubuntu 26.04.1 LTS, Kernel 7.0.0-38, Uptime 4 Tage, 2 CPUs, 3,2 GiB RAM (2 GiB available), zram-Swap, Root-LV 98 GB / 15 % belegt, HDD ST500LT012 | live bestätigt |
| Zeit | Server-Zeitzone Etc/UTC, NTP synchron | live bestätigt |
| Dienste | ma-home-web/-agent/-terminal laufen, ma-home-firewall exited (oneshot), ma-home-maintenance.timer alle 5 min OK | live bestätigt |
| Container/Prozesse | Prozessliste zeigt Authelia, Caddy, Filebrowser, ntfy, CouchDB, Home Assistant, Blocky; `docker ps` als andrew nicht erlaubt (kein docker-Gruppenmitglied) | Prozesse live, Container-Details offen (root nötig) |
| sudo | andrew in Gruppe sudo, aber Passwort nötig; kein NOPASSWD (bewusst, Entscheidung 2026-10-09) | live bestätigt |
| Web-Dateien | `/opt/ma-home/web` ist `root:root 700`; Dienst `ma-home-web` läuft als `ma-web` (uid 999, keine Zusatzgruppen); `/opt`, `/opt/ma-home` 755 | live bestätigt. Folgerung "daher JSON-404 auf /" ist **Hypothese** (Code: `send_from_directory` → NotFound → JSON-Handler), Nachweis als ma-web steht aus (Skript scripts/ma-fix-web-perms.sh) |
| Portal lokal | `127.0.0.1:18765/healthz` 200; `/` ohne Key 401 | live bestätigt |
| Domain via LAN-IP erzwungen | `--resolve` auf 192.168.0.111: TLS ok, 302 → Authelia (Hauptdomain und ha) | live bestätigt (nur bis Login; Dashboard nach Login ungeprüft) |
| Client-DNS PC | PC (192.168.0.70, DHCP) nutzt DNS 192.168.0.104 (antwortet nicht, Host nicht im ARP) und 192.168.0.1; Router löst Domain auf öffentliche IP 109.192.162.38; Zugriff darauf aus dem LAN → Timeout | live bestätigt (Auflösung/Timeout); Ursache Timeout = Hairpin-NAT ist **Hypothese** |
| Blocky | 192.168.0.111:53 antwortet: Domain/ha/ntfy/sync → 192.168.0.111, externe Namen werden aufgelöst | live bestätigt (PC-Abfrage); Nutzung durch Clients nicht aktiviert |
| LAN-IP direkt | `https://192.168.0.111/` bricht TLS ab (`alert internal error`, kein Zertifikat ohne SNI); `http://192.168.0.111/` → 308 auf https://192.168.0.111/ | live bestätigt. Das ist der "Verbindungsabbruch"; Caddy hat keine Site für die IP. Deutung "erwartetes Verhalten" = Hypothese |
| Ports | Server lauscht u. a. 22, 80, 443, 8080, 8443, 8123, 18555; vom PC aus 8123/8443/18555 nicht erreichbar (vermutlich UFW) | Server live, Ursache der PC-Sperre Hypothese |
| Zertifikat | Let's Encrypt (YE1), gültig bis 2027-01-02 | live bestätigt |
| Drucker/Scanner | 192.168.0.198: kein Ping, keine offenen Ports 80/443/631/9100/8080; CUPS ohne Drucker, `scanimage -L` ohne Gerät, kein IPP/eSCL per mDNS | live bestätigt; Drucker vermutlich aus oder neue IP = Hypothese |
| Backup | `/srv/ma-home/backups` root-only (Inhalt ungeprüft); keine externe Platte (nur sda + DVD-Laufwerk); `/etc/ma-home/backup.json` nicht lesbar geprüft | externes Ziel fehlt live bestätigt, Rest offen |
| Updates | 25 Pakete upgradable (inkl. Header), kein Reboot nötig | live bestätigt |
| Alt | Eintrag `ma-home-terminal` (ttyd → SSH) neu gegenüber Doku, hört nur auf 127.0.0.1:17681 | live bestätigt |

| Web-Dateirechte (Update 2026-10-09) | `/opt/ma-home/web` root:ma-web 750, Dateien 640; ma-web liest alles; Portal `/` 404 → 200, Assets und `/api/me` 200, ohne Schlüssel 401 | **live bestätigt** (Ausgabe Andrew + Gegenprüfung stat/curl durch Claude). Ersetzt die Hypothese "Web-Dateien unlesbar" oben. Browser-Login noch offen |

## Diagnosebericht 2026-10-09 ~18:19 Europe/Berlin (root-Diagnose, andrew per sudo; bereinigt)

Alle Punkte: Quelle Bericht `~/ma-diag-20261009T161819Z/report.txt`, Belegstatus **live bestätigt**, sofern nicht "Hypothese".

| Bereich | Befund |
|---|---|
| Webdateien | index.html/app.js/style.css auf Server **byte-identisch** mit Installer-Kopie (sha256 app.js d617b4c4…, index 15597436…, style 51d4ed5b…); lokale Kopie `server-snapshot/web-from-installer/` = Serverstand |
| Container | blocky, ntfy, caddy, couchdb, authelia, filebrowser, homeassistant laufen seit 5 Tagen; RAM zusammen ca. 0,8 GiB; HA 545 MiB / 768 MiB Limit |
| Filebrowser | Container "healthy", aber `127.0.0.1:18081` antwortet nicht (`Empty reply`/`Connection reset`); Caddy-Log: 6× 502 auf `/files/` → Funktion "Dateien" im Dashboard defekt. Ursache offen (Logs/Konfig nötig) |
| Home Assistant | HA-Log 2026-10-09 05:22: "request from a reverse proxy was received from 127.0.0.1, but your HTTP integration is not set-up for reverse proxies" → Proxy-Anfragen werden von HA abgelehnt. Belegte Ursache für nicht funktionierende HA-Einbettung ist das *wahrscheinlich*, Laufzeittest offen (Hypothese). HA sendet zusätzlich `X-Frame-Options: SAMEORIGIN`; Caddy entfernt das und setzt `frame-ancestors` für ma-server.duckdns.org (Konfig geprüft) |
| Terminal/ntfy | Upstreams 17681 und 12586 antworten 200 direkt am Server |
| Authelia | Regeln: default deny; Hauptdomain und ha: two_factor; ntfy, sync: one_factor. Anmeldung vom PC erreicht 2FA-Schritt ("requires 2FA, cannot be redirected yet") |
| Caddy | Portal-Route setzt CSP mit `frame-src` für ha/ntfy; `/files` und `/terminal` laufen hinter forward_auth; Zugriffe ohne Anmeldung ergeben 401 (viele Scanner-Anfragen, alle abgewiesen) |
| Blocky | Log 15:06 UTC: DoT-Upstreams 9.9.9.9:853 / 149.112.112.112:853 schlugen fehl (ISP/Netz, Hypothese); Namensauflösung funktionierte in meinen Tests |
| Drucker/Scanner | host.json kennt Scanner `airscan:w1:Samsung C48x`; `scanimage -L` findet aktuell nichts; `printer_ready=False`, keine CUPS-Queue; Gerät zuletzt nicht erreichbar → Hardware/Netz-Blockade |
| Backup | kein `backup.json`, kein Status; externes Ziel fehlt (Blockade, Entscheidung Andrew) |
| UFW | aktiv, default deny; 80/443/8080/8443 offen (IPv4+IPv6), SSH nur LAN, DNS nur LAN |
| sudo | `sudo-rs` 0.2.13: Ticket je Terminal; `/etc/sudoers.d/zz-ma-claude` (timestamp_timeout=480) gesetzt; tmux-Freischaltung im ersten Versuch an falschem Passwort gescheitert (Log 16:18:43) |

## Stand nach Reparaturen 2026-10-09 ~18:40 Europe/Berlin (live bestätigt, Details im CHANGELOG)
- Web-Dateirechte, Filebrowser (`/files`), HA-Proxy-Einstellung und Dokumentvorschau repariert; Portal-API serverseitig vollständig getestet.
- Weiterhin **offen / nicht getestet**: Browser-Ablauf (Login mit 2FA, Navigation, iframes), PC-Client-DNS-Test, Handy-Ansicht, Druck (Drucker nicht erreichbar), Scan, Backup (kein externes Ziel).
